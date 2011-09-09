#!/usr/bin/env python


import os
import logging

try:
	from xdg import BaseDirectory as _BaseDirectory
	BaseDirectory = _BaseDirectory
except ImportError:
	BaseDirectory = None


_moduleLogger = logging.getLogger(__name__)


_libc = None


def set_process_name(name):
	try: # change process name for killall
		global _libc
		if _libc is None:
			import ctypes
			_libc = ctypes.CDLL('libc.so.6')
		_libc.prctl(15, name, 0, 0, 0)
	except Exception, e:
		_moduleLogger.warning('Unable to set processName: %s" % e')


def _get_xdg_path(resourceType):
	if BaseDirectory is not None:
		if resourceType == "data":
			base = BaseDirectory.xdg_data_home
			if base == "/usr/share/mime":
				# Ugly hack because somehow Maemo 4.1 seems to be set to this
				base = None
		elif resourceType == "config":
			base = BaseDirectory.xdg_config_home
		elif resourceType == "cache":
			base = BaseDirectory.xdg_cache_home
		else:
			raise RuntimeError("Unknown type: "+resourceType)
	else:
		base = None

	return base


def get_resource_path(resourceType, resource, name = None):
	base = _get_xdg_path(resourceType)
	if base is not None:
		dirPath = os.path.join(base, resource)
	else:
		base = os.path.join(os.path.expanduser("~"), ".%s" % resource)
		dirPath = base
	if name is not None:
		dirPath = os.path.join(dirPath, name)
	return dirPath


def get_new_resource(resourceType, resource, name):
	dirPath = get_resource_path(resourceType, resource)
	filePath = os.path.join(dirPath, name)
	if not os.path.exists(dirPath):
		# Looking before I leap to not mask errors
		os.makedirs(dirPath)

	return filePath


def get_existing_resource(resourceType, resource, name):
	base = _get_xdg_path(resourceType)

	if base is not None:
		finalPath = os.path.join(base, name)
		if os.path.exists(finalPath):
			return finalPath

	altBase = os.path.join(os.path.expanduser("~"), ".%s" % resource)
	finalPath = os.path.join(altBase, name)
	if os.path.exists(finalPath):
		return finalPath
	else:
		raise RuntimeError("Resource not found: %r" % ((resourceType, resource, name), ))
