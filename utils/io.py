#!/usr/bin/env python


from __future__ import with_statement

import os
import pickle
import contextlib
import itertools
import codecs
from xml.sax import saxutils
import csv
try:
	import cStringIO as StringIO
except ImportError:
	import StringIO


@contextlib.contextmanager
def change_directory(directory):
	previousDirectory = os.getcwd()
	os.chdir(directory)
	currentDirectory = os.getcwd()

	try:
		yield previousDirectory, currentDirectory
	finally:
		os.chdir(previousDirectory)


@contextlib.contextmanager
def pickled(filename):
	"""
	Here is an example usage:
	with pickled("foo.db") as p:
		p("users", list).append(["srid", "passwd", 23])
	"""

	if os.path.isfile(filename):
		data = pickle.load(open(filename))
	else:
		data = {}

	def getter(item, factory):
		if item in data:
			return data[item]
		else:
			data[item] = factory()
			return data[item]

	yield getter

	pickle.dump(data, open(filename, "w"))


@contextlib.contextmanager
def redirect(object_, attr, value):
	"""
	>>> import sys
	... with redirect(sys, 'stdout', open('stdout', 'w')):
	... 	print "hello"
	...
	>>> print "we're back"
	we're back
	"""
	orig = getattr(object_, attr)
	setattr(object_, attr, value)
	try:
		yield
	finally:
		setattr(object_, attr, orig)


def pathsplit(path):
	"""
	>>> pathsplit("/a/b/c")
	['', 'a', 'b', 'c']
	>>> pathsplit("./plugins/builtins.ini")
	['.', 'plugins', 'builtins.ini']
	"""
	pathParts = path.split(os.path.sep)
	return pathParts


def commonpath(l1, l2, common=None):
	"""
	>>> commonpath(pathsplit('/a/b/c/d'), pathsplit('/a/b/c1/d1'))
	(['', 'a', 'b'], ['c', 'd'], ['c1', 'd1'])
	>>> commonpath(pathsplit("./plugins/"), pathsplit("./plugins/builtins.ini"))
	(['.', 'plugins'], [''], ['builtins.ini'])
	>>> commonpath(pathsplit("./plugins/builtins"), pathsplit("./plugins"))
	(['.', 'plugins'], ['builtins'], [])
	"""
	if common is None:
		common = []

	if l1 == l2:
		return l1, [], []

	for i, (leftDir, rightDir) in enumerate(zip(l1, l2)):
		if leftDir != rightDir:
			return l1[0:i], l1[i:], l2[i:]
	else:
		if leftDir == rightDir:
			i += 1
		return l1[0:i], l1[i:], l2[i:]


def relpath(p1, p2):
	"""
	>>> relpath('/', '/')
	'./'
	>>> relpath('/a/b/c/d', '/')
	'../../../../'
	>>> relpath('/a/b/c/d', '/a/b/c1/d1')
	'../../c1/d1'
	>>> relpath('/a/b/c/d', '/a/b/c1/d1/')
	'../../c1/d1'
	>>> relpath("./plugins/builtins", "./plugins")
	'../'
	>>> relpath("./plugins/", "./plugins/builtins.ini")
	'builtins.ini'
	"""
	sourcePath = os.path.normpath(p1)
	destPath = os.path.normpath(p2)

	(common, sourceOnly, destOnly) = commonpath(pathsplit(sourcePath), pathsplit(destPath))
	if len(sourceOnly) or len(destOnly):
		relParts = itertools.chain(
			(('..' + os.sep) * len(sourceOnly), ),
			destOnly,
		)
		return os.path.join(*relParts)
	else:
		return "."+os.sep


class UTF8Recoder(object):
	"""
	Iterator that reads an encoded stream and reencodes the input to UTF-8
	"""
	def __init__(self, f, encoding):
		self.reader = codecs.getreader(encoding)(f)

	def __iter__(self):
		return self

	def next(self):
		return self.reader.next().encode("utf-8")


class UnicodeReader(object):
	"""
	A CSV reader which will iterate over lines in the CSV file "f",
	which is encoded in the given encoding.
	"""

	def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
		f = UTF8Recoder(f, encoding)
		self.reader = csv.reader(f, dialect=dialect, **kwds)

	def next(self):
		row = self.reader.next()
		return [unicode(s, "utf-8") for s in row]

	def __iter__(self):
		return self

class UnicodeWriter(object):
	"""
	A CSV writer which will write rows to CSV file "f",
	which is encoded in the given encoding.
	"""

	def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
		# Redirect output to a queue
		self.queue = StringIO.StringIO()
		self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
		self.stream = f
		self.encoder = codecs.getincrementalencoder(encoding)()

	def writerow(self, row):
		self.writer.writerow([s.encode("utf-8") for s in row])
		# Fetch UTF-8 output from the queue ...
		data = self.queue.getvalue()
		data = data.decode("utf-8")
		# ... and reencode it into the target encoding
		data = self.encoder.encode(data)
		# write to the target stream
		self.stream.write(data)
		# empty queue
		self.queue.truncate(0)

	def writerows(self, rows):
		for row in rows:
			self.writerow(row)


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
	# csv.py doesn't do Unicode; encode temporarily as UTF-8:
	csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
							dialect=dialect, **kwargs)
	for row in csv_reader:
		# decode UTF-8 back to Unicode, cell by cell:
		yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
	for line in unicode_csv_data:
		yield line.encode('utf-8')


_UNESCAPE_ENTITIES = {
 "&quot;": '"',
 "&nbsp;": " ",
 "&#39;": "'",
}


_ESCAPE_ENTITIES = dict((v, k) for (v, k) in zip(_UNESCAPE_ENTITIES.itervalues(), _UNESCAPE_ENTITIES.iterkeys()))
del _ESCAPE_ENTITIES[" "]


def unescape(text):
	plain = saxutils.unescape(text, _UNESCAPE_ENTITIES)
	return plain


def escape(text):
	fancy = saxutils.escape(text, _ESCAPE_ENTITIES)
	return fancy
