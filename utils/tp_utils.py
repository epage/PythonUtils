#!/usr/bin/env python

import logging

import dbus
import telepathy

import util.go_utils as gobject_utils
import misc


_moduleLogger = logging.getLogger(__name__)
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class WasMissedCall(object):

	def __init__(self, bus, conn, chan, on_success, on_error):
		self.__on_success = on_success
		self.__on_error = on_error

		self._requested = None
		self._didMembersChange = False
		self._didClose = False
		self._didReport = False

		self._onTimeout = gobject_utils.Timeout(self._on_timeout)
		self._onTimeout.start(seconds=60)

		chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].connect_to_signal(
			"MembersChanged",
			self._on_members_changed,
		)

		chan[telepathy.interfaces.CHANNEL].connect_to_signal(
			"Closed",
			self._on_closed,
		)

		chan[DBUS_PROPERTIES].GetAll(
			telepathy.interfaces.CHANNEL_INTERFACE,
			reply_handler = self._on_got_all,
			error_handler = self._on_error,
		)

	def cancel(self):
		self._report_error("by request")

	def _report_missed_if_ready(self):
		if self._didReport:
			pass
		elif self._requested is not None and (self._didMembersChange or self._didClose):
			if self._requested:
				self._report_error("wrong direction")
			elif self._didClose:
				self._report_success()
			else:
				self._report_error("members added")
		else:
			if self._didClose:
				self._report_error("closed too early")

	def _report_success(self):
		assert not self._didReport, "Double reporting a missed call"
		self._didReport = True
		self._onTimeout.cancel()
		self.__on_success(self)

	def _report_error(self, reason):
		assert not self._didReport, "Double reporting a missed call"
		self._didReport = True
		self._onTimeout.cancel()
		self.__on_error(self, reason)

	@misc.log_exception(_moduleLogger)
	def _on_got_all(self, properties):
		self._requested = properties["Requested"]
		self._report_missed_if_ready()

	@misc.log_exception(_moduleLogger)
	def _on_members_changed(self, message, added, removed, lp, rp, actor, reason):
		if added:
			self._didMembersChange = True
			self._report_missed_if_ready()

	@misc.log_exception(_moduleLogger)
	def _on_closed(self):
		self._didClose = True
		self._report_missed_if_ready()

	@misc.log_exception(_moduleLogger)
	def _on_error(self, *args):
		self._report_error(args)

	@misc.log_exception(_moduleLogger)
	def _on_timeout(self):
		self._report_error("timeout")
		return False


class NewChannelSignaller(object):

	def __init__(self, on_new_channel):
		self._sessionBus = dbus.SessionBus()
		self._on_user_new_channel = on_new_channel

	def start(self):
		self._sessionBus.add_signal_receiver(
			self._on_new_channel,
			"NewChannel",
			"org.freedesktop.Telepathy.Connection",
			None,
			None
		)

	def stop(self):
		self._sessionBus.remove_signal_receiver(
			self._on_new_channel,
			"NewChannel",
			"org.freedesktop.Telepathy.Connection",
			None,
			None
		)

	@misc.log_exception(_moduleLogger)
	def _on_new_channel(
		self, channelObjectPath, channelType, handleType, handle, supressHandler
	):
		connObjectPath = channel_path_to_conn_path(channelObjectPath)
		serviceName = path_to_service_name(channelObjectPath)
		try:
			self._on_user_new_channel(
				self._sessionBus, serviceName, connObjectPath, channelObjectPath, channelType
			)
		except Exception:
			_moduleLogger.exception("Blocking exception from being passed up")


class EnableSystemContactIntegration(object):

	ACCOUNT_MGR_NAME = "org.freedesktop.Telepathy.AccountManager"
	ACCOUNT_MGR_PATH = "/org/freedesktop/Telepathy/AccountManager"
	ACCOUNT_MGR_IFACE_QUERY = "com.nokia.AccountManager.Interface.Query"
	ACCOUNT_IFACE_COMPAT = "com.nokia.Account.Interface.Compat"
	ACCOUNT_IFACE_COMPAT_PROFILE = "com.nokia.Account.Interface.Compat.Profile"
	DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'

	def __init__(self, profileName):
		self._bus = dbus.SessionBus()
		self._profileName = profileName

	def start(self):
		self._accountManager = self._bus.get_object(
			self.ACCOUNT_MGR_NAME,
			self.ACCOUNT_MGR_PATH,
		)
		self._accountManagerQuery = dbus.Interface(
			self._accountManager,
			dbus_interface=self.ACCOUNT_MGR_IFACE_QUERY,
		)

		self._accountManagerQuery.FindAccounts(
			{
				self.ACCOUNT_IFACE_COMPAT_PROFILE: self._profileName,
			},
			reply_handler = self._on_found_accounts_reply,
			error_handler = self._on_error,
		)

	@misc.log_exception(_moduleLogger)
	def _on_found_accounts_reply(self, accountObjectPaths):
		for accountObjectPath in accountObjectPaths:
			print accountObjectPath
			account = self._bus.get_object(
				self.ACCOUNT_MGR_NAME,
				accountObjectPath,
			)
			accountProperties = dbus.Interface(
				account,
				self.DBUS_PROPERTIES,
			)
			accountProperties.Set(
				self.ACCOUNT_IFACE_COMPAT,
				"SecondaryVCardFields",
				["TEL"],
				reply_handler = self._on_field_set,
				error_handler = self._on_error,
			)

	@misc.log_exception(_moduleLogger)
	def _on_field_set(self):
		_moduleLogger.info("SecondaryVCardFields Set")

	@misc.log_exception(_moduleLogger)
	def _on_error(self, error):
		_moduleLogger.error("%r" % (error, ))


def channel_path_to_conn_path(channelObjectPath):
	"""
	>>> channel_path_to_conn_path("/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME/Channel1")
	'/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME'
	"""
	return channelObjectPath.rsplit("/", 1)[0]


def path_to_service_name(path):
	"""
	>>> path_to_service_name("/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME/Channel1")
	'org.freedesktop.Telepathy.ConnectionManager.theonering.gv.USERNAME'
	"""
	return ".".join(path[1:].split("/")[0:7])


def cm_from_path(path):
	"""
	>>> cm_from_path("/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME/Channel1")
	'theonering'
	"""
	return path[1:].split("/")[4]
