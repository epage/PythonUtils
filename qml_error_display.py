#!/usr/bin/env python
# -*- coding: UTF8 -*-

from __future__ import with_statement

import os
import logging

import util.qt_compat as qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module("QtGui")
QtDeclarative = qt_compat.import_module("QtDeclarative")

from util import qore_utils
from util import io as io_utils


_moduleLogger = logging.getLogger(__name__)


def run(args):
	logFormat = '(%(relativeCreated)5d) %(levelname)-5s %(threadName)s.%(name)s.%(funcName)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=logFormat)

	errorLog = qore_utils.QErrorLog()
	errorLoghandler = io_utils.ErrorLogHandler(errorLog, level=logging.INFO)

	root = logging.getLogger()
	root.addHandler(errorLoghandler)
	_moduleLogger.debug("OS: %s", os.uname()[0])
	_moduleLogger.debug("Kernel: %s (%s) for %s", *os.uname()[2:])
	_moduleLogger.debug("Hostname: %s", os.uname()[1])

	_moduleLogger.error("Logging with notification bars!")

	app = QtGui.QApplication(args)

	view = QtDeclarative.QDeclarativeView()
	view.setResizeMode(QtDeclarative.QDeclarativeView.SizeRootObjectToView)
	view.setWindowTitle(os.path.basename(__file__))

	engine = view.engine()

	context = view.rootContext()
	context.setContextProperty("errorLog", errorLog)

	topLevelQMLFile = os.path.join(os.path.dirname(__file__), "data", os.path.basename(__file__).replace(".py", ".qml"))
	view.setSource(topLevelQMLFile)

	view.show()
	return app.exec_()


if __name__ == "__main__":
	import sys

	val = run(sys.argv)
	sys.exit(val)
