#!/usr/bin/env python

"""
Uses for generators
* Pull pipelining (iterators)
* Push pipelining (coroutines)
* State machines (coroutines)
* "Cooperative multitasking" (coroutines)
* Algorithm -> Object transform for cohesiveness (for example context managers) (coroutines)

Design considerations
* When should a stage pass on exceptions or have it thrown within it?
* When should a stage pass on GeneratorExits?
* Is there a way to either turn a push generator into a iterator or to use
	comprehensions syntax for push generators (I doubt it)
* When should the stage try and send data in both directions
* Since pull generators (generators), push generators (coroutines), subroutines, and coroutines are all coroutines, maybe we should rename the push generators to not confuse them, like signals/slots? and then refer to two-way generators as coroutines
** If so, make s* and co* implementation of functions
"""

import threading
import Queue
import pickle
import functools
import itertools
import xml.sax
import xml.parsers.expat


def autostart(func):
	"""
	>>> @autostart
	... def grep_sink(pattern):
	... 	print "Looking for %s" % pattern
	... 	while True:
	... 		line = yield
	... 		if pattern in line:
	... 			print line,
	>>> g = grep_sink("python")
	Looking for python
	>>> g.send("Yeah but no but yeah but no")
	>>> g.send("A series of tubes")
	>>> g.send("python generators rock!")
	python generators rock!
	>>> g.close()
	"""

	@functools.wraps(func)
	def start(*args, **kwargs):
		cr = func(*args, **kwargs)
		cr.next()
		return cr

	return start


@autostart
def printer_sink(format = "%s"):
	"""
	>>> pr = printer_sink("%r")
	>>> pr.send("Hello")
	'Hello'
	>>> pr.send("5")
	'5'
	>>> pr.send(5)
	5
	>>> p = printer_sink()
	>>> p.send("Hello")
	Hello
	>>> p.send("World")
	World
	>>> # p.throw(RuntimeError, "Goodbye")
	>>> # p.send("Meh")
	>>> # p.close()
	"""
	while True:
		item = yield
		print format % (item, )


@autostart
def null_sink():
	"""
	Good for uses like with cochain to pick up any slack
	"""
	while True:
		item = yield


def itr_source(itr, target):
	"""
	>>> itr_source(xrange(2), printer_sink())
	0
	1
	"""
	for item in itr:
		target.send(item)


@autostart
def cofilter(predicate, target):
	"""
	>>> p = printer_sink()
	>>> cf = cofilter(None, p)
	>>> cf.send("")
	>>> cf.send("Hello")
	Hello
	>>> cf.send([])
	>>> cf.send([1, 2])
	[1, 2]
	>>> cf.send(False)
	>>> cf.send(True)
	True
	>>> cf.send(0)
	>>> cf.send(1)
	1
	>>> # cf.throw(RuntimeError, "Goodbye")
	>>> # cf.send(False)
	>>> # cf.send(True)
	>>> # cf.close()
	"""
	if predicate is None:
		predicate = bool

	while True:
		try:
			item = yield
			if predicate(item):
				target.send(item)
		except StandardError, e:
			target.throw(e.__class__, e.message)


@autostart
def comap(function, target):
	"""
	>>> p = printer_sink()
	>>> cm = comap(lambda x: x+1, p)
	>>> cm.send(0)
	1
	>>> cm.send(1.0)
	2.0
	>>> cm.send(-2)
	-1
	>>> # cm.throw(RuntimeError, "Goodbye")
	>>> # cm.send(0)
	>>> # cm.send(1.0)
	>>> # cm.close()
	"""
	while True:
		try:
			item = yield
			mappedItem = function(item)
			target.send(mappedItem)
		except StandardError, e:
			target.throw(e.__class__, e.message)


def func_sink(function):
	return comap(function, null_sink())


def expand_positional(function):

	@functools.wraps(function)
	def expander(item):
		return function(*item)

	return expander


@autostart
def append_sink(l):
	"""
	>>> l = []
	>>> apps = append_sink(l)
	>>> apps.send(1)
	>>> apps.send(2)
	>>> apps.send(3)
	>>> print l
	[1, 2, 3]
	"""
	while True:
		item = yield
		l.append(item)


@autostart
def last_n_sink(l, n = 1):
	"""
	>>> l = []
	>>> lns = last_n_sink(l)
	>>> lns.send(1)
	>>> lns.send(2)
	>>> lns.send(3)
	>>> print l
	[3]
	"""
	del l[:]
	while True:
		item = yield
		extraCount = len(l) - n + 1
		if 0 < extraCount:
			del l[0:extraCount]
		l.append(item)


@autostart
def coreduce(target, function, initializer = None):
	"""
	>>> reduceResult = []
	>>> lns = last_n_sink(reduceResult)
	>>> cr = coreduce(lns, lambda x, y: x + y, 0)
	>>> cr.send(1)
	>>> cr.send(2)
	>>> cr.send(3)
	>>> print reduceResult
	[6]
	>>> cr = coreduce(lns, lambda x, y: x + y)
	>>> cr.send(1)
	>>> cr.send(2)
	>>> cr.send(3)
	>>> print reduceResult
	[6]
	"""
	isFirst = True
	cumulativeRef = initializer
	while True:
		item = yield
		if isFirst and initializer is None:
			cumulativeRef = item
		else:
			cumulativeRef = function(cumulativeRef, item)
		target.send(cumulativeRef)
		isFirst = False


@autostart
def cotee(targets):
	"""
	Takes a sequence of coroutines and sends the received items to all of them

	>>> ct = cotee((printer_sink("1 %s"), printer_sink("2 %s")))
	>>> ct.send("Hello")
	1 Hello
	2 Hello
	>>> ct.send("World")
	1 World
	2 World
	>>> # ct.throw(RuntimeError, "Goodbye")
	>>> # ct.send("Meh")
	>>> # ct.close()
	"""
	while True:
		try:
			item = yield
			for target in targets:
				target.send(item)
		except StandardError, e:
			for target in targets:
				target.throw(e.__class__, e.message)


class CoTee(object):
	"""
	>>> ct = CoTee()
	>>> ct.register_sink(printer_sink("1 %s"))
	>>> ct.register_sink(printer_sink("2 %s"))
	>>> ct.stage.send("Hello")
	1 Hello
	2 Hello
	>>> ct.stage.send("World")
	1 World
	2 World
	>>> ct.register_sink(printer_sink("3 %s"))
	>>> ct.stage.send("Foo")
	1 Foo
	2 Foo
	3 Foo
	>>> # ct.stage.throw(RuntimeError, "Goodbye")
	>>> # ct.stage.send("Meh")
	>>> # ct.stage.close()
	"""

	def __init__(self):
		self.stage = self._stage()
		self._targets = []

	def register_sink(self, sink):
		self._targets.append(sink)

	def unregister_sink(self, sink):
		self._targets.remove(sink)

	def restart(self):
		self.stage = self._stage()

	@autostart
	def _stage(self):
		while True:
			try:
				item = yield
				for target in self._targets:
					target.send(item)
			except StandardError, e:
				for target in self._targets:
					target.throw(e.__class__, e.message)


def _flush_queue(queue):
	while not queue.empty():
		yield queue.get()


@autostart
def cocount(target, start = 0):
	"""
	>>> cc = cocount(printer_sink("%s"))
	>>> cc.send("a")
	0
	>>> cc.send(None)
	1
	>>> cc.send([])
	2
	>>> cc.send(0)
	3
	"""
	for i in itertools.count(start):
		item = yield
		target.send(i)


@autostart
def coenumerate(target, start = 0):
	"""
	>>> ce = coenumerate(printer_sink("%r"))
	>>> ce.send("a")
	(0, 'a')
	>>> ce.send(None)
	(1, None)
	>>> ce.send([])
	(2, [])
	>>> ce.send(0)
	(3, 0)
	"""
	for i in itertools.count(start):
		item = yield
		decoratedItem = i, item
		target.send(decoratedItem)


@autostart
def corepeat(target, elem):
	"""
	>>> cr = corepeat(printer_sink("%s"), "Hello World")
	>>> cr.send("a")
	Hello World
	>>> cr.send(None)
	Hello World
	>>> cr.send([])
	Hello World
	>>> cr.send(0)
	Hello World
	"""
	while True:
		item = yield
		target.send(elem)


@autostart
def cointercept(target, elems):
	"""
	>>> cr = cointercept(printer_sink("%s"), [1, 2, 3, 4])
	>>> cr.send("a")
	1
	>>> cr.send(None)
	2
	>>> cr.send([])
	3
	>>> cr.send(0)
	4
	>>> cr.send("Bye")
	Traceback (most recent call last):
	  File "/usr/lib/python2.5/doctest.py", line 1228, in __run
	    compileflags, 1) in test.globs
	  File "<doctest __main__.cointercept[5]>", line 1, in <module>
	    cr.send("Bye")
	StopIteration
	"""
	item = yield
	for elem in elems:
		target.send(elem)
		item = yield


@autostart
def codropwhile(target, pred):
	"""
	>>> cdw = codropwhile(printer_sink("%s"), lambda x: x)
	>>> cdw.send([0, 1, 2])
	>>> cdw.send(1)
	>>> cdw.send(True)
	>>> cdw.send(False)
	>>> cdw.send([0, 1, 2])
	[0, 1, 2]
	>>> cdw.send(1)
	1
	>>> cdw.send(True)
	True
	"""
	while True:
		item = yield
		if not pred(item):
			break

	while True:
		item = yield
		target.send(item)


@autostart
def cotakewhile(target, pred):
	"""
	>>> ctw = cotakewhile(printer_sink("%s"), lambda x: x)
	>>> ctw.send([0, 1, 2])
	[0, 1, 2]
	>>> ctw.send(1)
	1
	>>> ctw.send(True)
	True
	>>> ctw.send(False)
	>>> ctw.send([0, 1, 2])
	>>> ctw.send(1)
	>>> ctw.send(True)
	"""
	while True:
		item = yield
		if not pred(item):
			break
		target.send(item)

	while True:
		item = yield


@autostart
def coslice(target, lower, upper):
	"""
	>>> cs = coslice(printer_sink("%r"), 3, 5)
	>>> cs.send("0")
	>>> cs.send("1")
	>>> cs.send("2")
	>>> cs.send("3")
	'3'
	>>> cs.send("4")
	'4'
	>>> cs.send("5")
	>>> cs.send("6")
	"""
	for i in xrange(lower):
		item = yield
	for i in xrange(upper - lower):
		item = yield
		target.send(item)
	while True:
		item = yield


@autostart
def cochain(targets):
	"""
	>>> cr = cointercept(printer_sink("good %s"), [1, 2, 3, 4])
	>>> cc = cochain([cr, printer_sink("end %s")])
	>>> cc.send("a")
	good 1
	>>> cc.send(None)
	good 2
	>>> cc.send([])
	good 3
	>>> cc.send(0)
	good 4
	>>> cc.send("Bye")
	end Bye
	"""
	behind = []
	for target in targets:
		try:
			while behind:
				item = behind.pop()
				target.send(item)
			while True:
				item = yield
				target.send(item)
		except StopIteration:
			behind.append(item)


@autostart
def queue_sink(queue):
	"""
	>>> q = Queue.Queue()
	>>> qs = queue_sink(q)
	>>> qs.send("Hello")
	>>> qs.send("World")
	>>> qs.throw(RuntimeError, "Goodbye")
	>>> qs.send("Meh")
	>>> qs.close()
	>>> print [i for i in _flush_queue(q)]
	[(None, 'Hello'), (None, 'World'), (<type 'exceptions.RuntimeError'>, 'Goodbye'), (None, 'Meh'), (<type 'exceptions.GeneratorExit'>, None)]
	"""
	while True:
		try:
			item = yield
			queue.put((None, item))
		except StandardError, e:
			queue.put((e.__class__, e.message))
		except GeneratorExit:
			queue.put((GeneratorExit, None))
			raise


def decode_item(item, target):
	if item[0] is None:
		target.send(item[1])
		return False
	elif item[0] is GeneratorExit:
		target.close()
		return True
	else:
		target.throw(item[0], item[1])
		return False


def queue_source(queue, target):
	"""
	>>> q = Queue.Queue()
	>>> for i in [
	... 	(None, 'Hello'),
	... 	(None, 'World'),
	... 	(GeneratorExit, None),
	... 	]:
	... 	q.put(i)
	>>> qs = queue_source(q, printer_sink())
	Hello
	World
	"""
	isDone = False
	while not isDone:
		item = queue.get()
		isDone = decode_item(item, target)


def threaded_stage(target, thread_factory = threading.Thread):
	messages = Queue.Queue()

	run_source = functools.partial(queue_source, messages, target)
	thread_factory(target=run_source).start()

	# Sink running in current thread
	return functools.partial(queue_sink, messages)


@autostart
def pickle_sink(f):
	while True:
		try:
			item = yield
			pickle.dump((None, item), f)
		except StandardError, e:
			pickle.dump((e.__class__, e.message), f)
		except GeneratorExit:
			pickle.dump((GeneratorExit, ), f)
			raise
		except StopIteration:
			f.close()
			return


def pickle_source(f, target):
	try:
		isDone = False
		while not isDone:
			item = pickle.load(f)
			isDone = decode_item(item, target)
	except EOFError:
		target.close()


class EventHandler(object, xml.sax.ContentHandler):

	START = "start"
	TEXT = "text"
	END = "end"

	def __init__(self, target):
		object.__init__(self)
		xml.sax.ContentHandler.__init__(self)
		self._target = target

	def startElement(self, name, attrs):
		self._target.send((self.START, (name, attrs._attrs)))

	def characters(self, text):
		self._target.send((self.TEXT, text))

	def endElement(self, name):
		self._target.send((self.END, name))


def expat_parse(f, target):
	parser = xml.parsers.expat.ParserCreate()
	parser.buffer_size = 65536
	parser.buffer_text = True
	parser.returns_unicode = False
	parser.StartElementHandler = lambda name, attrs: target.send(('start', (name, attrs)))
	parser.EndElementHandler = lambda name: target.send(('end', name))
	parser.CharacterDataHandler = lambda data: target.send(('text', data))
	parser.ParseFile(f)


if __name__ == "__main__":
	import doctest
	doctest.testmod()
