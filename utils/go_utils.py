#!/usr/bin/env python

from __future__ import with_statement

import time
import functools
import threading
import Queue
import logging

import gobject

import algorithms
import misc


_moduleLogger = logging.getLogger(__name__)


def make_idler(func):
	"""
	Decorator that makes a generator-function into a function that will continue execution on next call
	"""
	a = []

	@functools.wraps(func)
	def decorated_func(*args, **kwds):
		if not a:
			a.append(func(*args, **kwds))
		try:
			a[0].next()
			return True
		except StopIteration:
			del a[:]
			return False

	return decorated_func


def async(func):
	"""
	Make a function mainloop friendly. the function will be called at the
	next mainloop idle state.

	>>> import misc
	>>> misc.validate_decorator(async)
	"""

	@functools.wraps(func)
	def new_function(*args, **kwargs):

		def async_function():
			func(*args, **kwargs)
			return False

		gobject.idle_add(async_function)

	return new_function


class Async(object):

	def __init__(self, func, once = True):
		self.__func = func
		self.__idleId = None
		self.__once = once

	def start(self):
		assert self.__idleId is None
		if self.__once:
			self.__idleId = gobject.idle_add(self._on_once)
		else:
			self.__idleId = gobject.idle_add(self.__func)

	def is_running(self):
		return self.__idleId is not None

	def cancel(self):
		if self.__idleId is not None:
			gobject.source_remove(self.__idleId)
			self.__idleId = None

	def __call__(self):
		return self.start()

	@misc.log_exception(_moduleLogger)
	def _on_once(self):
		self.cancel()
		try:
			self.__func()
		except Exception:
			pass
		return False


class Timeout(object):

	def __init__(self, func, once = True):
		self.__func = func
		self.__timeoutId = None
		self.__once = once

	def start(self, **kwds):
		assert self.__timeoutId is None

		callback = self._on_once if self.__once else self.__func

		assert len(kwds) == 1
		timeoutInSeconds = kwds["seconds"]
		assert 0 <= timeoutInSeconds

		if timeoutInSeconds == 0:
			self.__timeoutId = gobject.idle_add(callback)
		else:
			self.__timeoutId = timeout_add_seconds(timeoutInSeconds, callback)

	def is_running(self):
		return self.__timeoutId is not None

	def cancel(self):
		if self.__timeoutId is not None:
			gobject.source_remove(self.__timeoutId)
			self.__timeoutId = None

	def __call__(self, **kwds):
		return self.start(**kwds)

	@misc.log_exception(_moduleLogger)
	def _on_once(self):
		self.cancel()
		try:
			self.__func()
		except Exception:
			pass
		return False


_QUEUE_EMPTY = object()


class FutureThread(object):

	def __init__(self):
		self.__workQueue = Queue.Queue()
		self.__thread = threading.Thread(
			name = type(self).__name__,
			target = self.__consume_queue,
		)
		self.__isRunning = True

	def start(self):
		self.__thread.start()

	def stop(self):
		self.__isRunning = False
		for _ in algorithms.itr_available(self.__workQueue):
			pass # eat up queue to cut down dumb work
		self.__workQueue.put(_QUEUE_EMPTY)

	def clear_tasks(self):
		for _ in algorithms.itr_available(self.__workQueue):
			pass # eat up queue to cut down dumb work

	def add_task(self, func, args, kwds, on_success, on_error):
		task = func, args, kwds, on_success, on_error
		self.__workQueue.put(task)

	@misc.log_exception(_moduleLogger)
	def __trampoline_callback(self, on_success, on_error, isError, result):
		if not self.__isRunning:
			if isError:
				_moduleLogger.error("Masking: %s" % (result, ))
			isError = True
			result = StopIteration("Cancelling all callbacks")
		callback = on_success if not isError else on_error
		try:
			callback(result)
		except Exception:
			_moduleLogger.exception("Callback errored")
		return False

	@misc.log_exception(_moduleLogger)
	def __consume_queue(self):
		while True:
			task = self.__workQueue.get()
			if task is _QUEUE_EMPTY:
				break
			func, args, kwds, on_success, on_error = task

			try:
				result = func(*args, **kwds)
				isError = False
			except Exception, e:
				_moduleLogger.error("Error, passing it back to the main thread")
				result = e
				isError = True
			self.__workQueue.task_done()

			gobject.idle_add(self.__trampoline_callback, on_success, on_error, isError, result)
		_moduleLogger.debug("Shutting down worker thread")


class AutoSignal(object):

	def __init__(self, toplevel):
		self.__disconnectPool = []
		toplevel.connect("destroy", self.__on_destroy)

	def connect_auto(self, widget, *args):
		id = widget.connect(*args)
		self.__disconnectPool.append((widget, id))

	@misc.log_exception(_moduleLogger)
	def __on_destroy(self, widget):
		_moduleLogger.info("Destroy: %r (%s to clean up)" % (self, len(self.__disconnectPool)))
		for widget, id in self.__disconnectPool:
			widget.disconnect(id)
		del self.__disconnectPool[:]


def throttled(minDelay, queue):
	"""
	Throttle the calls to a function by queueing all the calls that happen
	before the minimum delay

	>>> import misc
	>>> import Queue
	>>> misc.validate_decorator(throttled(0, Queue.Queue()))
	"""

	def actual_decorator(func):

		lastCallTime = [None]

		def process_queue():
			if 0 < len(queue):
				func, args, kwargs = queue.pop(0)
				lastCallTime[0] = time.time() * 1000
				func(*args, **kwargs)
			return False

		@functools.wraps(func)
		def new_function(*args, **kwargs):
			now = time.time() * 1000
			if (
				lastCallTime[0] is None or
				(now - lastCallTime >= minDelay)
			):
				lastCallTime[0] = now
				func(*args, **kwargs)
			else:
				queue.append((func, args, kwargs))
				lastCallDelta = now - lastCallTime[0]
				processQueueTimeout = int(minDelay * len(queue) - lastCallDelta)
				gobject.timeout_add(processQueueTimeout, process_queue)

		return new_function

	return actual_decorator


def _old_timeout_add_seconds(timeout, callback):
	return gobject.timeout_add(timeout * 1000, callback)


def _timeout_add_seconds(timeout, callback):
	return gobject.timeout_add_seconds(timeout, callback)


try:
	gobject.timeout_add_seconds
	timeout_add_seconds = _timeout_add_seconds
except AttributeError:
	timeout_add_seconds = _old_timeout_add_seconds
