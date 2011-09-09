#!/usr/bin/env python

"""
QML Tips:
	Large images:
		QML asynchronous = true; cache = false; [1]
	Insert properties at top of element declarations [1]
	Non-visible items: set opacity to 0 [2]
	Use Loader [1]
	Keep QML files small [1]

[1] http://sf2011.meego.com/program/sessions/performance-tips-and-tricks-qtqml-applications-0
[2] http://doc.qt.nokia.com/4.7/qdeclarativeperformance.html
"""

from __future__ import with_statement
from __future__ import division

import os
import logging

import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module("QtGui")
QtDeclarative = qt_compat.import_module("QtDeclarative")


_moduleLogger = logging.getLogger(__name__)


class DeclarativeView(QtDeclarative.QDeclarativeView):

	def __init__(self):
		QtDeclarative.QDeclarativeView.__init__(self)

	closing = qt_compat.Signal()

	def closeEvent(self, event):
		self.closing.emit()
		event.ignore()


def disable_default_window_painting(view):
	"""
	See http://doc.qt.nokia.com/4.7-snapshot/qdeclarativeperformance.html
	"""
	view.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
	view.setAttribute(QtCore.Qt.WA_NoSystemBackground)
	view.viewport().setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
	view.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)


class SystemThemeIconProvider(QtDeclarative.QDeclarativeImageProvider):

	IMAGE_TYPE = QtDeclarative.QDeclarativeImageProvider.ImageType.Pixmap

	def __init__(self):
		QtDeclarative.QDeclarativeImageProvider.__init__(self, self.IMAGE_TYPE)

	def requestPixmap(self, id, size, requestedSize):
		icon = QtGui.QIcon.fromTheme(id)
		pixmap = icon.pixmap(requestedSize)
		return pixmap


class LocalImageProvider(QtDeclarative.QDeclarativeImageProvider):

	IMAGE_TYPE = QtDeclarative.QDeclarativeImageProvider.ImageType.Image

	def __init__(self, path):
		QtDeclarative.QDeclarativeImageProvider.__init__(self, self.IMAGE_TYPE)
		self._path = path

	def requestImage(self, id, size, requestedSize):
		image = QtGui.QImage(os.path.join(self._path, id))
		return image


if __name__ == "__main__":
	pass

