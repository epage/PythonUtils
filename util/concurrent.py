#!/usr/bin/env python

from __future__ import with_statement

import os
import errno
import time
import functools
import contextlib
import logging

import misc


_moduleLogger = logging.getLogger(__name__)


class AsyncTaskQueue(object):

	def __init__(self, taskPool):
		self._asyncs = []
		self._taskPool = taskPool

	def add_async(self, func):
		self.flush()
		a = AsyncGeneratorTask(self._taskPool, func)
		self._asyncs.append(a)
		return a

	def flush(self):
		self._asyncs = [a for a in self._asyncs if not a.isDone]


class AsyncGeneratorTask(object):

	def __init__(self, pool, func):
		self._pool = pool
		self._func = func
		self._run = None
		self._isDone = False

	@property
	def isDone(self):
		return self._isDone

	def start(self, *args, **kwds):
		assert self._run is None, "Task already started"
		self._run = self._func(*args, **kwds)
		trampoline, args, kwds = self._run.send(None) # priming the function
		self._pool.add_task(
			trampoline,
			args,
			kwds,
			self.on_success,
			self.on_error,
		)

	@misc.log_exception(_moduleLogger)
	def on_success(self, result):
		_moduleLogger.debug("Processing success for: %r", self._func)
		try:
			trampoline, args, kwds = self._run.send(result)
		except StopIteration, e:
			self._isDone = True
		else:
			self._pool.add_task(
				trampoline,
				args,
				kwds,
				self.on_success,
				self.on_error,
			)

	@misc.log_exception(_moduleLogger)
	def on_error(self, error):
		_moduleLogger.debug("Processing error for: %r", self._func)
		try:
			trampoline, args, kwds = self._run.throw(error)
		except StopIteration, e:
			self._isDone = True
		else:
			self._pool.add_task(
				trampoline,
				args,
				kwds,
				self.on_success,
				self.on_error,
			)

	def __repr__(self):
		return "<async %s at 0x%x>" % (self._func.__name__, id(self))

	def __hash__(self):
		return hash(self._func)

	def __eq__(self, other):
		return self._func == other._func

	def __ne__(self, other):
		return self._func != other._func


def synchronized(lock):
	"""
	Synchronization decorator.

	>>> import misc
	>>> misc.validate_decorator(synchronized(object()))
	"""

	def wrap(f):

		@functools.wraps(f)
		def newFunction(*args, **kw):
			lock.acquire()
			try:
				return f(*args, **kw)
			finally:
				lock.release()
		return newFunction
	return wrap


@contextlib.contextmanager
def qlock(queue, gblock = True, gtimeout = None, pblock = True, ptimeout = None):
	"""
	Locking with a queue, good for when you want to lock an item passed around

	>>> import Queue
	>>> item = 5
	>>> lock = Queue.Queue()
	>>> lock.put(item)
	>>> with qlock(lock) as i:
	... 	print i
	5
	"""
	item = queue.get(gblock, gtimeout)
	try:
		yield item
	finally:
		queue.put(item, pblock, ptimeout)


@contextlib.contextmanager
def flock(path, timeout=-1):
	WAIT_FOREVER = -1
	DELAY = 0.1
	timeSpent = 0

	acquired = False

	while timeSpent <= timeout or timeout == WAIT_FOREVER:
		try:
			fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
			acquired = True
			break
		except OSError, e:
			if e.errno != errno.EEXIST:
				raise
		time.sleep(DELAY)
		timeSpent += DELAY

	assert acquired, "Failed to grab file-lock %s within timeout %d" % (path, timeout)

	try:
		yield fd
	finally:
		os.unlink(path)
