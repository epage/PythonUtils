#!/usr/bin/env python

"""
Showcases:
* qt_compat
* comncurrent's async functions which builds on go_utils / qore_utils task pool
* qui_util's error log
* logging slot exceptions
* qui_util's QSignalingMainWindow which exposes some additional signals
"""

from __future__ import with_statement
from __future__ import division

import time
import logging

from utils import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module("QtGui")
from utils import qore_utils
from utils import qui_utils
from utils import concurrent
from utils import misc


_moduleLogger = logging.getLogger(__name__)


class BusyWait(object):

	def __init__(self):
		# Specifically make this variable thread unsafe
		self._value = 0

	def wait(self, t):
		self._value = t
		while self._value < (t+10):
			self._value += 1
			print self._value
			time.sleep(0.1)


class Window(object):

	def __init__(self):
		self._errorLog = qui_utils.QErrorLog()
		self._errorDisplay = qui_utils.ErrorDisplay(self._errorLog)
		self._taskPool = qore_utils.FutureThread()
		self._taskPool.start()
		self._busyWait = BusyWait()

		exceptionButton = QtGui.QPushButton("Throw")
		exceptionButton.clicked.connect(self._on_exception)

		backgroundButton = QtGui.QPushButton("Background Task")
		backgroundButton.clicked.connect(self._on_background)

		self._layout = QtGui.QBoxLayout(QtGui.QBoxLayout.LeftToRight)
		self._layout.addWidget(exceptionButton)
		self._layout.addWidget(backgroundButton)
		self._layout.setContentsMargins(0, 0, 0, 0)

		self._superLayout = QtGui.QVBoxLayout()
		self._superLayout.addWidget(self._errorDisplay.toplevel)
		self._superLayout.addLayout(self._layout)
		self._superLayout.setContentsMargins(0, 0, 0, 0)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self._superLayout)
		centralWidget.setContentsMargins(0, 0, 0, 0)

		self._qwindow = qui_utils.QSignalingMainWindow()
		self._qwindow.shown.connect(self._on_shown)
		self._qwindow.hidden.connect(self._on_hidden)
		self._qwindow.closed.connect(self._on_closed)
		self._qwindow.destroyed.connect(self._on_destroyed)
		self._qwindow.setCentralWidget(centralWidget)
		qui_utils.set_stackable(self._qwindow, True)

	def show(self):
		self._qwindow.show()

	def destroy(self):
		self._taskPool.stop()
		self._qwindow.destroy()

	@misc.log_exception(_moduleLogger)
	def _on_background(self, *args):
		print "background"
		# Works perfectly well with a GObject task pool
		agt = concurrent.AsyncGeneratorTask(self._taskPool, self._call_into_background)
		agt.start(10)

	def _call_into_background(self, t):
		with qui_utils.notify_error(self._errorLog):
			with qui_utils.notify_busy(self._errorLog, "Counting..."):
				print "Start count"
				yield self._busyWait.wait, (t, ), {}
				print "Count done"

	@misc.log_exception(_moduleLogger)
	def _on_exception(self, *args):
		with qui_utils.notify_error(self._errorLog):
			l = [1, 2, 3]
			print l["a"]

	@misc.log_exception(_moduleLogger)
	def _on_shown(self):
		self._errorLog.push_message("shown")
		print "shown"

	@misc.log_exception(_moduleLogger)
	def _on_hidden(self):
		self._errorLog.push_message("hidden")
		print "hidden"

	@misc.log_exception(_moduleLogger)
	def _on_closed(self):
		self._errorLog.push_message("closed")
		print "closed"

	@misc.log_exception(_moduleLogger)
	def _on_destroyed(self):
		self._errorLog.push_message("destroyed")
		print "destroyed"


def run():
	logFormat = '(%(relativeCreated)5d) %(levelname)-5s %(threadName)s.%(name)s.%(funcName)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=logFormat)

	app = QtGui.QApplication([])

	win = Window()
	win.show()

	ret = app.exec_()

	win.destroy()

	return ret


if __name__ == "__main__":
	import sys

	val = run()
	sys.exit(val)
