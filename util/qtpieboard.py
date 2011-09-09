#!/usr/bin/env python


from __future__ import division

import os
import warnings

import qt_compat
QtGui = qt_compat.import_module("QtGui")

import qtpie


class PieKeyboard(object):

	SLICE_CENTER = -1
	SLICE_NORTH = 0
	SLICE_NORTH_WEST = 1
	SLICE_WEST = 2
	SLICE_SOUTH_WEST = 3
	SLICE_SOUTH = 4
	SLICE_SOUTH_EAST = 5
	SLICE_EAST = 6
	SLICE_NORTH_EAST = 7

	MAX_ANGULAR_SLICES = 8

	SLICE_DIRECTIONS = [
		SLICE_CENTER,
		SLICE_NORTH,
		SLICE_NORTH_WEST,
		SLICE_WEST,
		SLICE_SOUTH_WEST,
		SLICE_SOUTH,
		SLICE_SOUTH_EAST,
		SLICE_EAST,
		SLICE_NORTH_EAST,
	]

	SLICE_DIRECTION_NAMES = [
		"CENTER",
		"NORTH",
		"NORTH_WEST",
		"WEST",
		"SOUTH_WEST",
		"SOUTH",
		"SOUTH_EAST",
		"EAST",
		"NORTH_EAST",
	]

	def __init__(self):
		self._layout = QtGui.QGridLayout()
		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._layout)

		self.__cells = {}

	@property
	def toplevel(self):
		return self._widget

	def add_pie(self, row, column, pieButton):
		assert len(pieButton) == 8
		self._layout.addWidget(pieButton, row, column)
		self.__cells[(row, column)] = pieButton

	def get_pie(self, row, column):
		return self.__cells[(row, column)]


class KeyboardModifier(object):

	def __init__(self, name):
		self.name = name
		self.lock = False
		self.once = False

	@property
	def isActive(self):
		return self.lock or self.once

	def on_toggle_lock(self, *args, **kwds):
		self.lock = not self.lock

	def on_toggle_once(self, *args, **kwds):
		self.once = not self.once

	def reset_once(self):
		self.once = False


def parse_keyboard_data(text):
	return eval(text)


def _enumerate_pie_slices(pieData, iconPaths):
	for direction, directionName in zip(
		PieKeyboard.SLICE_DIRECTIONS, PieKeyboard.SLICE_DIRECTION_NAMES
	):
		if directionName in pieData:
			sliceData = pieData[directionName]

			action = QtGui.QAction(None)
			try:
				action.setText(sliceData["text"])
			except KeyError:
				pass
			try:
				relativeIconPath = sliceData["path"]
			except KeyError:
				pass
			else:
				for iconPath in iconPaths:
					absIconPath = os.path.join(iconPath, relativeIconPath)
					if os.path.exists(absIconPath):
						action.setIcon(QtGui.QIcon(absIconPath))
						break
			pieItem = qtpie.QActionPieItem(action)
			actionToken = sliceData["action"]
		else:
			pieItem = qtpie.PieFiling.NULL_CENTER
			actionToken = ""
		yield direction, pieItem, actionToken


def load_keyboard(keyboardName, dataTree, keyboard, keyboardHandler, iconPaths):
	for (row, column), pieData in dataTree.iteritems():
		pieItems = list(_enumerate_pie_slices(pieData, iconPaths))
		assert pieItems[0][0] == PieKeyboard.SLICE_CENTER, pieItems[0]
		_, center, centerAction = pieItems.pop(0)

		pieButton = qtpie.QPieButton(center)
		pieButton.set_center(center)
		keyboardHandler.map_slice_action(center, centerAction)
		for direction, pieItem, action in pieItems:
			pieButton.insertItem(pieItem)
			keyboardHandler.map_slice_action(pieItem, action)
		keyboard.add_pie(row, column, pieButton)


class KeyboardHandler(object):

	def __init__(self, keyhandler):
		self.__keyhandler = keyhandler
		self.__commandHandlers = {}
		self.__modifiers = {}
		self.__sliceActions = {}

		self.register_modifier("Shift")
		self.register_modifier("Super")
		self.register_modifier("Control")
		self.register_modifier("Alt")

	def register_command_handler(self, command, handler):
		# @todo Look into hooking these up directly to the pie actions
		self.__commandHandlers["[%s]" % command] = handler

	def unregister_command_handler(self, command):
		# @todo Look into hooking these up directly to the pie actions
		del self.__commandHandlers["[%s]" % command]

	def register_modifier(self, modifierName):
		mod = KeyboardModifier(modifierName)
		self.register_command_handler(modifierName, mod.on_toggle_lock)
		self.__modifiers["<%s>" % modifierName] = mod

	def unregister_modifier(self, modifierName):
		self.unregister_command_handler(modifierName)
		del self.__modifiers["<%s>" % modifierName]

	def map_slice_action(self, slice, action):
		callback = lambda: self(action)
		slice.action().triggered.connect(callback)
		self.__sliceActions[slice] = (action, callback)

	def __call__(self, action):
		activeModifiers = [
			mod.name
			for mod in self.__modifiers.itervalues()
				if mod.isActive
		]

		needResetOnce = False
		if action.startswith("[") and action.endswith("]"):
			commandName = action[1:-1]
			if action in self.__commandHandlers:
				self.__commandHandlers[action](commandName, activeModifiers)
				needResetOnce = True
			else:
				warnings.warn("Unknown command: [%s]" % commandName)
		elif action.startswith("<") and action.endswith(">"):
			modName = action[1:-1]
			for mod in self.__modifiers.itervalues():
				if mod.name == modName:
					mod.on_toggle_once()
					break
			else:
				warnings.warn("Unknown modifier: <%s>" % modName)
		else:
			self.__keyhandler(action, activeModifiers)
			needResetOnce = True

		if needResetOnce:
			for mod in self.__modifiers.itervalues():
				mod.reset_once()
