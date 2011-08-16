#!/usr/bin/env python

from __future__ import with_statement

import contextlib
import logging

import qt_compat
QtCore = qt_compat.QtCore

import misc


_moduleLogger = logging.getLogger(__name__)


class QThread44(QtCore.QThread):
	"""
	This is to imitate QThread in Qt 4.4+ for when running on older version
	See http://labs.trolltech.com/blogs/2010/06/17/youre-doing-it-wrong
	(On Lucid I have Qt 4.7 and this is still an issue)
	"""

	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)

	def run(self):
		self.exec_()


class _WorkerThread(QtCore.QObject):

	_taskComplete  = qt_compat.Signal(object)

	def __init__(self, futureThread):
		QtCore.QObject.__init__(self)
		self._futureThread = futureThread
		self._futureThread._addTask.connect(self._on_task_added)
		self._taskComplete.connect(self._futureThread._on_task_complete)

	@qt_compat.Slot(object)
	def _on_task_added(self, task):
		self.__on_task_added(task)

	@misc.log_exception(_moduleLogger)
	def __on_task_added(self, task):
		if not self._futureThread._isRunning:
			_moduleLogger.error("Dropping task")

		func, args, kwds, on_success, on_error = task

		try:
			result = func(*args, **kwds)
			isError = False
		except Exception, e:
			_moduleLogger.error("Error, passing it back to the main thread")
			result = e
			isError = True

		taskResult = on_success, on_error, isError, result
		self._taskComplete.emit(taskResult)


class FutureThread(QtCore.QObject):

	_addTask = qt_compat.Signal(object)

	def __init__(self):
		QtCore.QObject.__init__(self)
		self._thread = QThread44()
		self._isRunning = False
		self._worker = _WorkerThread(self)
		self._worker.moveToThread(self._thread)

	def start(self):
		self._thread.start()
		self._isRunning = True

	def stop(self):
		self._isRunning = False
		self._thread.quit()

	def add_task(self, func, args, kwds, on_success, on_error):
		assert self._isRunning, "Task queue not started"
		task = func, args, kwds, on_success, on_error
		self._addTask.emit(task)

	@qt_compat.Slot(object)
	def _on_task_complete(self, taskResult):
		self.__on_task_complete(taskResult)

	@misc.log_exception(_moduleLogger)
	def __on_task_complete(self, taskResult):
		on_success, on_error, isError, result = taskResult
		if not self._isRunning:
			if isError:
				_moduleLogger.error("Masking: %s" % (result, ))
			isError = True
			result = StopIteration("Cancelling all callbacks")
		callback = on_success if not isError else on_error
		try:
			callback(result)
		except Exception:
			_moduleLogger.exception("Callback errored")


def create_single_column_list_model(columnName, **kwargs):
	"""
	>>> class Single(object): pass
	>>> SingleListModel = create_single_column_list_model("s")
	>>> slm = SingleListModel([Single(), Single(), Single()])
	"""

	class SingleColumnListModel(QtCore.QAbstractListModel):

		def __init__(self, l = None):
			QtCore.QAbstractListModel.__init__(self)
			self._list = l if l is not None else []
			self.setRoleNames({0: columnName})

		def __len__(self):
			return len(self._list)

		def __getitem__(self, key):
			return self._list[key]

		def __setitem__(self, key, value):
			with scoped_model_reset(self):
				self._list[key] = value

		def __delitem__(self, key):
			with scoped_model_reset(self):
				del self._list[key]

		def __iter__(self):
			return iter(self._list)

		def __repr__(self):
			return '<%s (%s)>' % (
				self.__class__.__name__,
				columnName,
			)

		def rowCount(self, parent=QtCore.QModelIndex()):
			return len(self._list)

		def data(self, index, role):
			if index.isValid() and role == 0:
				return self._list[index.row()]
			return None

	if "name" in kwargs:
		SingleColumnListModel.__name__ = kwargs["name"]

	return SingleColumnListModel


def create_tupled_list_model(*columnNames, **kwargs):
	"""
	>>> class Column0(object): pass
	>>> class Column1(object): pass
	>>> class Column2(object): pass
	>>> MultiColumnedListModel = create_tupled_list_model("c0", "c1", "c2")
	>>> mclm = MultiColumnedListModel([(Column0(), Column1(), Column2())])
	"""

	class TupledListModel(QtCore.QAbstractListModel):

		def __init__(self, l = None):
			QtCore.QAbstractListModel.__init__(self)
			self._list = l if l is not None else []
			self.setRoleNames(dict(enumerate(columnNames)))

		def __len__(self):
			return len(self._list)

		def __getitem__(self, key):
			return self._list[key]

		def __setitem__(self, key, value):
			with scoped_model_reset(self):
				self._list[key] = value

		def __delitem__(self, key):
			with scoped_model_reset(self):
				del self._list[key]

		def __iter__(self):
			return iter(self._list)

		def __repr__(self):
			return '<%s (%s)>' % (
				self.__class__.__name__,
				', '.join(columnNames),
			)

		def rowCount(self, parent=QtCore.QModelIndex()):
			return len(self._list)

		def data(self, index, role):
			if index.isValid() and 0 <= role and role < len(columnNames):
				return self._list[index.row()][role]
			return None

	if "name" in kwargs:
		TupledListModel.__name__ = kwargs["name"]

	return TupledListModel


class FileSystemModel(QtCore.QAbstractListModel):
	"""
	Wrapper around QtGui.QFileSystemModel
	"""

	FILEINFOS = [
		"fileName",
		"isDir",
		"filePath",
		"completeSuffix",
		"baseName",
	]

	EXTINFOS = [
		"type",
	]

	ALLINFOS = FILEINFOS + EXTINFOS

	def __init__(self, model, path):
		QtCore.QAbstractListModel.__init__(self)
		self._path = path

		self._model = model
		self._rootIndex = self._model.index(self._path)

		self._child = None
		self.setRoleNames(dict(enumerate(self.ALLINFOS)))
		self._model.directoryLoaded.connect(self._on_directory_loaded)

	childChanged = qt_compat.Signal(QtCore.QObject)

	def _child(self):
		assert self._child is not None
		return self._child

	child = qt_compat.Property(QtCore.QObject, _child, notify=childChanged)

	backendChanged = qt_compat.Signal()

	def _parent(self):
		finfo = self._model.fileInfo(self._rootIndex)
		return finfo.fileName()

	parent = qt_compat.Property(str, _parent, notify=backendChanged)

	@qt_compat.Slot(str)
	def browse_to(self, path):
		if self._child is None:
			self._child = FileSystemModel(self._model, path)
		else:
			self._child.switch_to(path)
		self.childChanged.emit()
		return self._child

	@qt_compat.Slot(str)
	def switch_to(self, path):
		with scoped_model_reset(self):
			self._path = path
			self._rootIndex = self._model.index(self._path)
		self.backendChanged.emit()

	def __len__(self):
		return self._model.rowCount(self._rootIndex)

	def __getitem__(self, key):
		return self._model.index(key, 0, self._rootIndex)

	def __iter__(self):
		return (self[i] for i in xrange(len(self)))

	def rowCount(self, parent=QtCore.QModelIndex()):
		return len(self)

	def data(self, index, role):
		if index.isValid() and 0 <= role and role < len(self.ALLINFOS):
			internalIndex = self._translate_index(index)
			info = self._model.fileInfo(internalIndex)
			if role < len(self.FILEINFOS):
				field = self.FILEINFOS[role]
				value = getattr(info, field)()
			else:
				role -= len(self.FILEINFOS)
				field = self.EXTINFOS[role]
				if field == "type":
					return self._model.type(internalIndex)
				else:
					raise NotImplementedError("Out of range that was already checked")
			return value
		return None

	def _on_directory_loaded(self, path):
		if self._path == path:
			self.backendChanged.emit()
			self.reset()

	def _translate_index(self, externalIndex):
		internalIndex = self._model.index(externalIndex.row(), 0, self._rootIndex)
		return internalIndex


@contextlib.contextmanager
def scoped_model_reset(model):
	model.beginResetModel()
	try:
		yield
	finally:
		model.endResetModel()


def create_qobject(*classDef, **kwargs):
	"""
	>>> Car = create_qobject(
	...     ('model', str),
	...     ('brand', str),
	...     ('year', int),
	...     ('inStock', bool),
	...     name='Car'
	... )
	>>> print Car
	<class '__main__.AutoQObject'>
	>>>  
	>>> c = Car(model='Fiesta', brand='Ford', year=1337)
	>>> print c.model, c.brand, c.year, c.inStock
	Fiesta Ford 1337 False
	>>> print c
	<Car (model='Fiesta', brand='Ford', year=1337, inStock=False)>
	>>>  
	>>> c.inStock = True
	>>>  
	>>> print c.model, c.brand, c.year, c.inStock
	Fiesta Ford 1337 True
	>>> print c
	<Car (model='Fiesta', brand='Ford', year=1337, inStock=True)>
	"""

	class AutoQObject(QtCore.QObject):

		def __init__(self, **initKwargs):
			QtCore.QObject.__init__(self)
			for key, val in classDef:
				setattr(self, '_'+key, initKwargs.get(key, val()))

		def __repr__(self):
			values = (
				'%s=%r' % (key, getattr(self, '_'+key))
				for key, value in classDef
			)
			return '<%s (%s)>' % (
				kwargs.get('name', self.__class__.__name__),
				', '.join(values),
			)

		for key, value in classDef:
			nfy = locals()['_nfy_'+key] = qt_compat.Signal()

			def _get(key):
				def f(self):
					return self.__dict__['_'+key]
				return f

			def _set(key):
				def f(self, value):
					setattr(self, '_'+key, value)
					getattr(self, '_nfy_'+key).emit()
				return f

			setter = locals()['_set_'+key] = _set(key)
			getter = locals()['_get_'+key] = _get(key)

			locals()[key] = qt_compat.Property(value, getter, setter, notify=nfy)
		del nfy, _get, _set, getter, setter

	return AutoQObject


class QObjectProxy(object):
	"""
	Proxy for accessing properties and slots as attributes

	This class acts as a proxy for the object for which it is
	created, and makes property access more Pythonic while
	still allowing access to slots (as member functions).

	Attribute names starting with '_' are not proxied.
	"""

	def __init__(self, rootObject):
		self._rootObject = rootObject
		m = self._rootObject.metaObject()
		self._properties = [
			m.property(i).name()
			for i in xrange(m.propertyCount())
		]

	def __getattr__(self, key):
		value = self._rootObject.property(key)

		# No such property, so assume we call a slot
		if value is None and key not in self._properties:
			return getattr(self._rootObject, key)

		return value

	def __setattr__(self, key, value):
		if key.startswith('_'):
			object.__setattr__(self, key, value)
		else:
			self._rootObject.setProperty(key, value)


if __name__ == "__main__":
	import doctest
	print doctest.testmod()
