#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import logging

import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module("QtGui")

import qui_utils
import misc as misc_utils
import linux as linux_utils


_moduleLogger = logging.getLogger(__name__)


class ApplicationWrapper(object):

	DEFAULT_ORIENTATION = "Default"
	AUTO_ORIENTATION = "Auto"
	LANDSCAPE_ORIENTATION = "Landscape"
	PORTRAIT_ORIENTATION = "Portrait"

	def __init__(self, qapp, constants):
		self._constants = constants
		self._qapp = qapp
		self._clipboard = QtGui.QApplication.clipboard()

		self._errorLog = qui_utils.QErrorLog()
		self._mainWindow = None

		self._fullscreenAction = QtGui.QAction(None)
		self._fullscreenAction.setText("Fullscreen")
		self._fullscreenAction.setCheckable(True)
		self._fullscreenAction.setShortcut(QtGui.QKeySequence("CTRL+Enter"))
		self._fullscreenAction.toggled.connect(self._on_toggle_fullscreen)

		self._orientation = self.DEFAULT_ORIENTATION
		self._orientationAction = QtGui.QAction(None)
		self._orientationAction.setText("Next Orientation")
		self._orientationAction.setCheckable(True)
		self._orientationAction.setShortcut(QtGui.QKeySequence("CTRL+o"))
		self._orientationAction.triggered.connect(self._on_next_orientation)

		self._logAction = QtGui.QAction(None)
		self._logAction.setText("Log")
		self._logAction.setShortcut(QtGui.QKeySequence("CTRL+l"))
		self._logAction.triggered.connect(self._on_log)

		self._quitAction = QtGui.QAction(None)
		self._quitAction.setText("Quit")
		self._quitAction.setShortcut(QtGui.QKeySequence("CTRL+q"))
		self._quitAction.triggered.connect(self._on_quit)

		self._aboutAction = QtGui.QAction(None)
		self._aboutAction.setText("About")
		self._aboutAction.triggered.connect(self._on_about)

		self._qapp.lastWindowClosed.connect(self._on_app_quit)
		self._mainWindow = self._new_main_window()
		self._mainWindow.window.destroyed.connect(self._on_child_close)

		self.load_settings()

		self._mainWindow.show()
		self._idleDelay = QtCore.QTimer()
		self._idleDelay.setSingleShot(True)
		self._idleDelay.setInterval(0)
		self._idleDelay.timeout.connect(self._on_delayed_start)
		self._idleDelay.start()

	def load_settings(self):
		raise NotImplementedError("Booh")

	def save_settings(self):
		raise NotImplementedError("Booh")

	def _new_main_window(self):
		raise NotImplementedError("Booh")

	@property
	def qapp(self):
		return self._qapp

	@property
	def constants(self):
		return self._constants

	@property
	def errorLog(self):
		return self._errorLog

	@property
	def fullscreenAction(self):
		return self._fullscreenAction

	@property
	def orientationAction(self):
		return self._orientationAction

	@property
	def orientation(self):
		return self._orientation

	@property
	def logAction(self):
		return self._logAction

	@property
	def aboutAction(self):
		return self._aboutAction

	@property
	def quitAction(self):
		return self._quitAction

	def set_orientation(self, orientation):
		self._orientation = orientation
		self._mainWindow.update_orientation(self._orientation)

	@classmethod
	def _next_orientation(cls, current):
		return {
			cls.DEFAULT_ORIENTATION: cls.AUTO_ORIENTATION,
			cls.AUTO_ORIENTATION: cls.LANDSCAPE_ORIENTATION,
			cls.LANDSCAPE_ORIENTATION: cls.PORTRAIT_ORIENTATION,
			cls.PORTRAIT_ORIENTATION: cls.DEFAULT_ORIENTATION,
		}[current]

	def _close_windows(self):
		if self._mainWindow is not None:
			self.save_settings()
			self._mainWindow.window.destroyed.disconnect(self._on_child_close)
			self._mainWindow.close()
			self._mainWindow = None

	@misc_utils.log_exception(_moduleLogger)
	def _on_delayed_start(self):
		self._mainWindow.start()

	@misc_utils.log_exception(_moduleLogger)
	def _on_app_quit(self, checked = False):
		if self._mainWindow is not None:
			self.save_settings()
			self._mainWindow.destroy()

	@misc_utils.log_exception(_moduleLogger)
	def _on_child_close(self, obj = None):
		if self._mainWindow is not None:
			self.save_settings()
			self._mainWindow = None

	@misc_utils.log_exception(_moduleLogger)
	def _on_toggle_fullscreen(self, checked = False):
		with qui_utils.notify_error(self._errorLog):
			self._mainWindow.set_fullscreen(checked)

	@misc_utils.log_exception(_moduleLogger)
	def _on_next_orientation(self, checked = False):
		with qui_utils.notify_error(self._errorLog):
			self.set_orientation(self._next_orientation(self._orientation))

	@misc_utils.log_exception(_moduleLogger)
	def _on_about(self, checked = True):
		raise NotImplementedError("Booh")

	@misc_utils.log_exception(_moduleLogger)
	def _on_log(self, checked = False):
		with qui_utils.notify_error(self._errorLog):
			logPath = linux_utils.get_resource_path(
				"cache", self._constants.__app_name__, "%s.log" % self._constants.__app_name__
			)
			with open(logPath, "r") as f:
				logLines = f.xreadlines()
				log = "".join(logLines)
				self._clipboard.setText(log)

	@misc_utils.log_exception(_moduleLogger)
	def _on_quit(self, checked = False):
		with qui_utils.notify_error(self._errorLog):
			self._close_windows()


class WindowWrapper(object):

	def __init__(self, parent, app):
		self._app = app

		self._errorDisplay = qui_utils.ErrorDisplay(self._app.errorLog)

		self._layout = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
		self._layout.setContentsMargins(0, 0, 0, 0)

		self._superLayout = QtGui.QVBoxLayout()
		self._superLayout.addWidget(self._errorDisplay.toplevel)
		self._superLayout.setContentsMargins(0, 0, 0, 0)
		self._superLayout.addLayout(self._layout)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._superLayout)
		centralWidget.setContentsMargins(0, 0, 0, 0)

		self._window = qui_utils.QSignalingMainWindow(parent)
		self._window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		qui_utils.set_stackable(self._window, True)
		self._window.setCentralWidget(centralWidget)

		self._closeWindowAction = QtGui.QAction(None)
		self._closeWindowAction.setText("Close")
		self._closeWindowAction.setShortcut(QtGui.QKeySequence("CTRL+w"))
		self._closeWindowAction.triggered.connect(self._on_close_window)

		self._window.addAction(self._closeWindowAction)
		self._window.addAction(self._app.quitAction)
		self._window.addAction(self._app.fullscreenAction)
		self._window.addAction(self._app.orientationAction)
		self._window.addAction(self._app.logAction)

	@property
	def window(self):
		return self._window

	@property
	def windowOrientation(self):
		geom = self._window.size()
		if geom.width() <= geom.height():
			return QtCore.Qt.Vertical
		else:
			return QtCore.Qt.Horizontal

	@property
	def idealWindowOrientation(self):
		if self._app.orientation ==  self._app.AUTO_ORIENTATION:
			windowOrientation = self.windowOrientation
		elif self._app.orientation ==  self._app.DEFAULT_ORIENTATION:
			windowOrientation = qui_utils.screen_orientation()
		elif self._app.orientation ==  self._app.LANDSCAPE_ORIENTATION:
			windowOrientation = QtCore.Qt.Horizontal
		elif self._app.orientation ==  self._app.PORTRAIT_ORIENTATION:
			windowOrientation = QtCore.Qt.Vertical
		else:
			raise RuntimeError("Bad! No %r for you" % self._app.orientation)
		return windowOrientation

	def walk_children(self):
		return ()

	def start(self):
		pass

	def close(self):
		for child in self.walk_children():
			child.window.destroyed.disconnect(self._on_child_close)
			child.close()
		self._window.close()

	def destroy(self):
		pass

	def show(self):
		self._window.show()
		for child in self.walk_children():
			child.show()
		self.set_fullscreen(self._app.fullscreenAction.isChecked())

	def hide(self):
		for child in self.walk_children():
			child.hide()
		self._window.hide()

	def set_fullscreen(self, isFullscreen):
		if self._window.isVisible():
			if isFullscreen:
				self._window.showFullScreen()
			else:
				self._window.showNormal()
		for child in self.walk_children():
			child.set_fullscreen(isFullscreen)

	def update_orientation(self, orientation):
		if orientation == self._app.DEFAULT_ORIENTATION:
			qui_utils.set_autorient(self.window, False)
			qui_utils.set_window_orientation(self.window, None)
		elif orientation == self._app.AUTO_ORIENTATION:
			qui_utils.set_autorient(self.window, True)
			qui_utils.set_window_orientation(self.window, None)
		elif orientation == self._app.LANDSCAPE_ORIENTATION:
			qui_utils.set_autorient(self.window, False)
			qui_utils.set_window_orientation(self.window, QtCore.Qt.Horizontal)
		elif orientation == self._app.PORTRAIT_ORIENTATION:
			qui_utils.set_autorient(self.window, False)
			qui_utils.set_window_orientation(self.window, QtCore.Qt.Vertical)
		else:
			raise RuntimeError("Unknown orientation: %r" % orientation)
		for child in self.walk_children():
			child.update_orientation(orientation)

	@misc_utils.log_exception(_moduleLogger)
	def _on_child_close(self, obj = None):
		raise NotImplementedError("Booh")

	@misc_utils.log_exception(_moduleLogger)
	def _on_close_window(self, checked = True):
		with qui_utils.notify_error(self._errorLog):
			self.close()


class AutoFreezeWindowFeature(object):

	def __init__(self, app, window):
		self._app = app
		self._window = window
		self._app.qapp.focusChanged.connect(self._on_focus_changed)
		if self._app.qapp.focusWidget() is not None:
			self._window.setUpdatesEnabled(True)
		else:
			self._window.setUpdatesEnabled(False)

	def close(self):
		self._app.qapp.focusChanged.disconnect(self._on_focus_changed)
		self._window.setUpdatesEnabled(True)

	@misc_utils.log_exception(_moduleLogger)
	def _on_focus_changed(self, oldWindow, newWindow):
		with qui_utils.notify_error(self._app.errorLog):
			if oldWindow is None and newWindow is not None:
				self._window.setUpdatesEnabled(True)
			elif oldWindow is not None and newWindow is None:
				self._window.setUpdatesEnabled(False)
