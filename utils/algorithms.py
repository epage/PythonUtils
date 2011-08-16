#!/usr/bin/env python

"""
@note Source http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66448
"""

import itertools
import functools
import datetime
import types
import array
import random


def ordered_itr(collection):
	"""
	>>> [v for v in ordered_itr({"a": 1, "b": 2})]
	[('a', 1), ('b', 2)]
	>>> [v for v in ordered_itr([3, 1, 10, -20])]
	[-20, 1, 3, 10]
	"""
	if isinstance(collection, types.DictType):
		keys = list(collection.iterkeys())
		keys.sort()
		for key in keys:
			yield key, collection[key]
	else:
		values = list(collection)
		values.sort()
		for value in values:
			yield value


def itercat(*iterators):
	"""
	Concatenate several iterators into one.

	>>> [v for v in itercat([1, 2, 3], [4, 1, 3])]
	[1, 2, 3, 4, 1, 3]
	"""
	for i in iterators:
		for x in i:
			yield x


def product(*args, **kwds):
	# product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
	# product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
	pools = map(tuple, args) * kwds.get('repeat', 1)
	result = [[]]
	for pool in pools:
		result = [x+[y] for x in result for y in pool]
	for prod in result:
		yield tuple(prod)


def iterwhile(func, iterator):
	"""
	Iterate for as long as func(value) returns true.
	>>> through = lambda b: b
	>>> [v for v in iterwhile(through, [True, True, False])]
	[True, True]
	"""
	iterator = iter(iterator)
	while 1:
		next = iterator.next()
		if not func(next):
			raise StopIteration
		yield next


def iterfirst(iterator, count=1):
	"""
	Iterate through 'count' first values.

	>>> [v for v in iterfirst([1, 2, 3, 4, 5], 3)]
	[1, 2, 3]
	"""
	iterator = iter(iterator)
	for i in xrange(count):
		yield iterator.next()


def iterstep(iterator, n):
	"""
	Iterate every nth value.

	>>> [v for v in iterstep([1, 2, 3, 4, 5], 1)]
	[1, 2, 3, 4, 5]
	>>> [v for v in iterstep([1, 2, 3, 4, 5], 2)]
	[1, 3, 5]
	>>> [v for v in iterstep([1, 2, 3, 4, 5], 3)]
	[1, 4]
	"""
	iterator = iter(iterator)
	while True:
		yield iterator.next()
		# skip n-1 values
		for dummy in xrange(n-1):
			iterator.next()


def itergroup(iterator, count, padValue = None):
	"""
	Iterate in groups of 'count' values. If there
	aren't enough values, the last result is padded with
	None.

	>>> for val in itergroup([1, 2, 3, 4, 5, 6], 3):
	... 	print tuple(val)
	(1, 2, 3)
	(4, 5, 6)
	>>> for val in itergroup([1, 2, 3, 4, 5, 6], 3):
	... 	print list(val)
	[1, 2, 3]
	[4, 5, 6]
	>>> for val in itergroup([1, 2, 3, 4, 5, 6, 7], 3):
	... 	print tuple(val)
	(1, 2, 3)
	(4, 5, 6)
	(7, None, None)
	>>> for val in itergroup("123456", 3):
	... 	print tuple(val)
	('1', '2', '3')
	('4', '5', '6')
	>>> for val in itergroup("123456", 3):
	... 	print repr("".join(val))
	'123'
	'456'
	"""
	paddedIterator = itertools.chain(iterator, itertools.repeat(padValue, count-1))
	nIterators = (paddedIterator, ) * count
	return itertools.izip(*nIterators)


def xzip(*iterators):
	"""Iterative version of builtin 'zip'."""
	iterators = itertools.imap(iter, iterators)
	while 1:
		yield tuple([x.next() for x in iterators])


def xmap(func, *iterators):
	"""Iterative version of builtin 'map'."""
	iterators = itertools.imap(iter, iterators)
	values_left = [1]

	def values():
		# Emulate map behaviour, i.e. shorter
		# sequences are padded with None when
		# they run out of values.
		values_left[0] = 0
		for i in range(len(iterators)):
			iterator = iterators[i]
			if iterator is None:
				yield None
			else:
				try:
					yield iterator.next()
					values_left[0] = 1
				except StopIteration:
					iterators[i] = None
					yield None
	while 1:
		args = tuple(values())
		if not values_left[0]:
			raise StopIteration
		yield func(*args)


def xfilter(func, iterator):
	"""Iterative version of builtin 'filter'."""
	iterator = iter(iterator)
	while 1:
		next = iterator.next()
		if func(next):
			yield next


def xreduce(func, iterator, default=None):
	"""Iterative version of builtin 'reduce'."""
	iterator = iter(iterator)
	try:
		prev = iterator.next()
	except StopIteration:
		return default
	single = 1
	for next in iterator:
		single = 0
		prev = func(prev, next)
	if single:
		return func(prev, default)
	return prev


def daterange(begin, end, delta = datetime.timedelta(1)):
	"""
	Form a range of dates and iterate over them.

	Arguments:
	begin -- a date (or datetime) object; the beginning of the range.
	end   -- a date (or datetime) object; the end of the range.
	delta -- (optional) a datetime.timedelta object; how much to step each iteration.
			Default step is 1 day.

	Usage:
	"""
	if not isinstance(delta, datetime.timedelta):
		delta = datetime.timedelta(delta)

	ZERO = datetime.timedelta(0)

	if begin < end:
		if delta <= ZERO:
			raise StopIteration
		test = end.__gt__
	else:
		if delta >= ZERO:
			raise StopIteration
		test = end.__lt__

	while test(begin):
		yield begin
		begin += delta


class LazyList(object):
	"""
	A Sequence whose values are computed lazily by an iterator.

	Module for the creation and use of iterator-based lazy lists.
	this module defines a class LazyList which can be used to represent sequences
	of values generated lazily. One can also create recursively defined lazy lists
	that generate their values based on ones previously generated.

	Backport to python 2.5 by Michael Pust
	"""

	__author__ = 'Dan Spitz'

	def __init__(self, iterable):
		self._exhausted = False
		self._iterator = iter(iterable)
		self._data = []

	def __len__(self):
		"""Get the length of a LazyList's computed data."""
		return len(self._data)

	def __getitem__(self, i):
		"""Get an item from a LazyList.
		i should be a positive integer or a slice object."""
		if isinstance(i, int):
			#index has not yet been yielded by iterator (or iterator exhausted
			#before reaching that index)
			if i >= len(self):
				self.exhaust(i)
			elif i < 0:
				raise ValueError('cannot index LazyList with negative number')
			return self._data[i]

		#LazyList slices are iterators over a portion of the list.
		elif isinstance(i, slice):
			start, stop, step = i.start, i.stop, i.step
			if any(x is not None and x < 0 for x in (start, stop, step)):
				raise ValueError('cannot index or step through a LazyList with'
								'a negative number')
			#set start and step to their integer defaults if they are None.
			if start is None:
				start = 0
			if step is None:
				step = 1

			def LazyListIterator():
				count = start
				predicate = (
					(lambda: True)
					if stop is None
					else (lambda: count < stop)
				)
				while predicate():
					try:
						yield self[count]
					#slices can go out of actual index range without raising an
					#error
					except IndexError:
						break
					count += step
			return LazyListIterator()

		raise TypeError('i must be an integer or slice')

	def __iter__(self):
		"""return an iterator over each value in the sequence,
		whether it has been computed yet or not."""
		return self[:]

	def computed(self):
		"""Return an iterator over the values in a LazyList that have
		already been computed."""
		return self[:len(self)]

	def exhaust(self, index = None):
		"""Exhaust the iterator generating this LazyList's values.
		if index is None, this will exhaust the iterator completely.
		Otherwise, it will iterate over the iterator until either the list
		has a value for index or the iterator is exhausted.
		"""
		if self._exhausted:
			return
		if index is None:
			ind_range = itertools.count(len(self))
		else:
			ind_range = range(len(self), index + 1)

		for ind in ind_range:
			try:
				self._data.append(self._iterator.next())
			except StopIteration: #iterator is fully exhausted
				self._exhausted = True
				break


class RecursiveLazyList(LazyList):

	def __init__(self, prod, *args, **kwds):
		super(RecursiveLazyList, self).__init__(prod(self, *args, **kwds))


class RecursiveLazyListFactory:

	def __init__(self, producer):
		self._gen = producer

	def __call__(self, *a, **kw):
		return RecursiveLazyList(self._gen, *a, **kw)


def lazylist(gen):
	"""
	Decorator for creating a RecursiveLazyList subclass.
	This should decorate a generator function taking the LazyList object as its
	first argument which yields the contents of the list in order.

	>>> #fibonnacci sequence in a lazy list.
	>>> @lazylist
	... def fibgen(lst):
	... 	yield 0
	... 	yield 1
	... 	for a, b in itertools.izip(lst, lst[1:]):
	... 		yield a + b
	...
	>>> #now fibs can be indexed or iterated over as if it were an infinitely long list containing the fibonnaci sequence
	>>> fibs = fibgen()
	>>>
	>>> #prime numbers in a lazy list.
	>>> @lazylist
	... def primegen(lst):
	... 	yield 2
	... 	for candidate in itertools.count(3): #start at next number after 2
	... 		#if candidate is not divisible by any smaller prime numbers,
	... 		#it is a prime.
	... 		if all(candidate % p for p in lst.computed()):
	... 			yield candidate
	...
	>>> #same for primes- treat it like an infinitely long list containing all prime numbers.
	>>> primes = primegen()
	>>> print fibs[0], fibs[1], fibs[2], primes[0], primes[1], primes[2]
	0 1 1 2 3 5
	>>> print list(fibs[:10]), list(primes[:10])
	[0, 1, 1, 2, 3, 5, 8, 13, 21, 34] [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
	"""
	return RecursiveLazyListFactory(gen)


def map_func(f):
	"""
	>>> import misc
	>>> misc.validate_decorator(map_func)
	"""

	@functools.wraps(f)
	def wrapper(*args):
		result = itertools.imap(f, args)
		return result
	return wrapper


def reduce_func(function):
	"""
	>>> import misc
	>>> misc.validate_decorator(reduce_func(lambda x: x))
	"""

	def decorator(f):

		@functools.wraps(f)
		def wrapper(*args):
			result = reduce(function, f(args))
			return result
		return wrapper
	return decorator


def any_(iterable):
	"""
	@note Python Version <2.5

	>>> any_([True, True])
	True
	>>> any_([True, False])
	True
	>>> any_([False, False])
	False
	"""

	for element in iterable:
		if element:
			return True
	return False


def all_(iterable):
	"""
	@note Python Version <2.5

	>>> all_([True, True])
	True
	>>> all_([True, False])
	False
	>>> all_([False, False])
	False
	"""

	for element in iterable:
		if not element:
			return False
	return True


def for_every(pred, seq):
	"""
	for_every takes a one argument predicate function and a sequence.
	@param pred The predicate function should return true or false.
	@returns true if every element in seq returns true for predicate, else returns false.

	>>> for_every (lambda c: c > 5,(6,7,8,9))
	True

	@author Source:http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52907
	"""

	for i in seq:
		if not pred(i):
			return False
	return True


def there_exists(pred, seq):
	"""
	there_exists takes a one argument predicate	function and a sequence.
	@param pred The predicate function should return true or false.
	@returns true if any element in seq returns true for predicate, else returns false.

	>>> there_exists (lambda c: c > 5,(6,7,8,9))
	True

	@author Source:http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52907
	"""

	for i in seq:
		if pred(i):
			return True
	return False


def func_repeat(quantity, func, *args, **kwd):
	"""
	Meant to be in connection with "reduce"
	"""
	for i in xrange(quantity):
		yield func(*args, **kwd)


def function_map(preds, item):
	"""
	Meant to be in connection with "reduce"
	"""
	results = (pred(item) for pred in preds)

	return results


def functional_if(combiner, preds, item):
	"""
	Combines the result of a list of predicates applied to item according to combiner

	@see any, every for example combiners
	"""
	pass_bool = lambda b: b

	bool_results = function_map(preds, item)
	return combiner(pass_bool, bool_results)


def pushback_itr(itr):
	"""
	>>> list(pushback_itr(xrange(5)))
	[0, 1, 2, 3, 4]
	>>>
	>>> first = True
	>>> itr = pushback_itr(xrange(5))
	>>> for i in itr:
	... 	print i
	... 	if first and i == 2:
	... 		first = False
	... 		print itr.send(i)
	0
	1
	2
	None
	2
	3
	4
	>>>
	>>> first = True
	>>> itr = pushback_itr(xrange(5))
	>>> for i in itr:
	... 	print i
	... 	if first and i == 2:
	... 		first = False
	... 		print itr.send(i)
	... 		print itr.send(i)
	0
	1
	2
	None
	None
	2
	2
	3
	4
	>>>
	>>> itr = pushback_itr(xrange(5))
	>>> print itr.next()
	0
	>>> print itr.next()
	1
	>>> print itr.send(10)
	None
	>>> print itr.next()
	10
	>>> print itr.next()
	2
	>>> print itr.send(20)
	None
	>>> print itr.send(30)
	None
	>>> print itr.send(40)
	None
	>>> print itr.next()
	40
	>>> print itr.next()
	30
	>>> print itr.send(50)
	None
	>>> print itr.next()
	50
	>>> print itr.next()
	20
	>>> print itr.next()
	3
	>>> print itr.next()
	4
	"""
	for item in itr:
		maybePushedBack = yield item
		queue = []
		while queue or maybePushedBack is not None:
			if maybePushedBack is not None:
				queue.append(maybePushedBack)
				maybePushedBack = yield None
			else:
				item = queue.pop()
				maybePushedBack = yield item


def itr_available(queue, initiallyBlock = False):
	if initiallyBlock:
		yield queue.get()
	while not queue.empty():
		yield queue.get_nowait()


class BloomFilter(object):
	"""
	http://en.wikipedia.org/wiki/Bloom_filter
	Sources:
	http://code.activestate.com/recipes/577684-bloom-filter/
	http://code.activestate.com/recipes/577686-bloom-filter/

	>>> from random import sample
	>>> from string import ascii_letters
	>>> states = '''Alabama Alaska Arizona Arkansas California Colorado Connecticut
	... Delaware Florida Georgia Hawaii Idaho Illinois Indiana Iowa Kansas
	... Kentucky Louisiana Maine Maryland Massachusetts Michigan Minnesota
	... Mississippi Missouri Montana Nebraska Nevada NewHampshire NewJersey
	... NewMexico NewYork NorthCarolina NorthDakota Ohio Oklahoma Oregon
	... Pennsylvania RhodeIsland SouthCarolina SouthDakota Tennessee Texas Utah
	... Vermont Virginia Washington WestVirginia Wisconsin Wyoming'''.split()
	>>> bf = BloomFilter(num_bits=1000, num_probes=14)
	>>> for state in states:
	... 	bf.add(state)
	>>> numStatesFound = sum(state in bf for state in states)
	>>> numStatesFound, len(states)
	(50, 50)
	>>> trials = 100
	>>> numGarbageFound = sum(''.join(sample(ascii_letters, 5)) in bf for i in range(trials))
	>>> numGarbageFound, trials
	(0, 100)
	"""

	def __init__(self, num_bits, num_probes):
		num_words = (num_bits + 31) // 32
		self._arr = array.array('B', [0]) * num_words
		self._num_probes = num_probes

	def add(self, key):
		for i, mask in self._get_probes(key):
			self._arr[i] |= mask

	def union(self, bfilter):
		if self._match_template(bfilter):
			for i, b in enumerate(bfilter._arr):
				self._arr[i] |= b
		else:
			# Union b/w two unrelated bloom filter raises this
			raise ValueError("Mismatched bloom filters")

	def intersection(self, bfilter):
		if self._match_template(bfilter):
			for i, b in enumerate(bfilter._arr):
				self._arr[i] &= b
		else:
			# Intersection b/w two unrelated bloom filter raises this
			raise ValueError("Mismatched bloom filters")

	def __contains__(self, key):
		return all(self._arr[i] & mask for i, mask in self._get_probes(key))

	def _match_template(self, bfilter):
		return self.num_bits == bfilter.num_bits and self.num_probes == bfilter.num_probes

	def _get_probes(self, key):
		hasher = random.Random(key).randrange
		for _ in range(self._num_probes):
			array_index = hasher(len(self._arr))
			bit_index = hasher(32)
			yield array_index, 1 << bit_index


if __name__ == "__main__":
	import doctest
	print doctest.testmod()
