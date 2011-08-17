#!/usr/bin/env python

"""
Simple example of using signals/slots to send messages across threads
"""

from __future__ import with_statement
from __future__ import division

import logging
import time

from utils import qt_compat
QtCore = qt_compat.QtCore
from utils import qore_utils
from utils import misc


_moduleLogger = logging.getLogger(__name__)


class Producer(QtCore.QObject):

	data = qt_compat.Signal(int)
	done = qt_compat.Signal()

	def __init__(self):
		QtCore.QObject.__init__(self)

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def process(self):
		print "Starting producer"
		for i in xrange(10):
			self.data.emit(i)
			time.sleep(0.1)
		self.done.emit()


class Consumer(QtCore.QObject):

	def __init__(self):
		QtCore.QObject.__init__(self)

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def process(self):
		print "Starting consumer"

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def print_done(self):
		print "Done"

	@qt_compat.Slot(int)
	@misc.log_exception(_moduleLogger)
	def print_data(self, i):
		print i


def run_producer_consumer():
	app = QtCore.QCoreApplication([])

	producerThread = qore_utils.QThread44()
	producer = Producer()
	producer.moveToThread(producerThread)
	producerThread.started.connect(producer.process)

	consumerThread = qore_utils.QThread44()
	consumer = Consumer()
	consumer.moveToThread(consumerThread)
	consumerThread.started.connect(consumer.process)

	producer.data.connect(consumer.print_data)
	producer.done.connect(consumer.print_done)

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def producer_done():
		print "Shutting down"
		producerThread.quit()
		consumerThread.quit()
		producerThread.wait()
		consumerThread.wait()
		print "Done"
	producer.done.connect(producer_done)

	count = [0]

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def thread_done():
		print "Thread done"
		count[0] += 1
		if count[0] == 2:
			print "Quitting"
			app.exit(0)
		print "Done"
	producerThread.finished.connect(thread_done)
	consumerThread.finished.connect(thread_done)

	producerThread.start()
	consumerThread.start()
	print "Status %s" % app.exec_()


if __name__ == "__main__":
	run_producer_consumer()
