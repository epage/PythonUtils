#!/usr/bin/env python

import math
import logging

import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module("QtGui")

import misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


_TWOPI = 2 * math.pi


def _radius_at(center, pos):
	delta = pos - center
	xDelta = delta.x()
	yDelta = delta.y()

	radius = math.sqrt(xDelta ** 2 + yDelta ** 2)
	return radius


def _angle_at(center, pos):
	delta = pos - center
	xDelta = delta.x()
	yDelta = delta.y()

	radius = math.sqrt(xDelta ** 2 + yDelta ** 2)
	angle = math.acos(xDelta / radius)
	if 0 <= yDelta:
		angle = _TWOPI - angle

	return angle


class QActionPieItem(object):

	def __init__(self, action, weight = 1):
		self._action = action
		self._weight = weight

	def action(self):
		return self._action

	def setWeight(self, weight):
		self._weight = weight

	def weight(self):
		return self._weight

	def setEnabled(self, enabled = True):
		self._action.setEnabled(enabled)

	def isEnabled(self):
		return self._action.isEnabled()


class PieFiling(object):

	INNER_RADIUS_DEFAULT = 64
	OUTER_RADIUS_DEFAULT = 192

	SELECTION_CENTER = -1
	SELECTION_NONE = -2

	NULL_CENTER = QActionPieItem(QtGui.QAction(None))

	def __init__(self):
		self._innerRadius = self.INNER_RADIUS_DEFAULT
		self._outerRadius = self.OUTER_RADIUS_DEFAULT
		self._children = []
		self._center = self.NULL_CENTER

		self._cacheIndexToAngle = {}
		self._cacheTotalWeight = 0

	def insertItem(self, item, index = -1):
		self._children.insert(index, item)
		self._invalidate_cache()

	def removeItemAt(self, index):
		item = self._children.pop(index)
		self._invalidate_cache()

	def set_center(self, item):
		if item is None:
			item = self.NULL_CENTER
		self._center = item

	def center(self):
		return self._center

	def clear(self):
		del self._children[:]
		self._center = self.NULL_CENTER
		self._invalidate_cache()

	def itemAt(self, index):
		return self._children[index]

	def indexAt(self, center, point):
		return self._angle_to_index(_angle_at(center, point))

	def innerRadius(self):
		return self._innerRadius

	def setInnerRadius(self, radius):
		self._innerRadius = radius

	def outerRadius(self):
		return self._outerRadius

	def setOuterRadius(self, radius):
		self._outerRadius = radius

	def __iter__(self):
		return iter(self._children)

	def __len__(self):
		return len(self._children)

	def __getitem__(self, index):
		return self._children[index]

	def _invalidate_cache(self):
		self._cacheIndexToAngle.clear()
		self._cacheTotalWeight = sum(child.weight() for child in self._children)
		if self._cacheTotalWeight == 0:
			self._cacheTotalWeight = 1

	def _index_to_angle(self, index, isShifted):
		key = index, isShifted
		if key in self._cacheIndexToAngle:
			return self._cacheIndexToAngle[key]
		index = index % len(self._children)

		baseAngle = _TWOPI / self._cacheTotalWeight

		angle = math.pi / 2
		if isShifted:
			if self._children:
				angle -= (self._children[0].weight() * baseAngle) / 2
			else:
				angle -= baseAngle / 2
		while angle < 0:
			angle += _TWOPI

		for i, child in enumerate(self._children):
			if index < i:
				break
			angle += child.weight() * baseAngle
		while _TWOPI < angle:
			angle -= _TWOPI

		self._cacheIndexToAngle[key] = angle
		return angle

	def _angle_to_index(self, angle):
		numChildren = len(self._children)
		if numChildren == 0:
			return self.SELECTION_CENTER

		baseAngle = _TWOPI / self._cacheTotalWeight

		iterAngle = math.pi / 2 - (self.itemAt(0).weight() * baseAngle) / 2
		while iterAngle < 0:
			iterAngle += _TWOPI

		oldIterAngle = iterAngle
		for index, child in enumerate(self._children):
			iterAngle += child.weight() * baseAngle
			if oldIterAngle < angle and angle <= iterAngle:
				return index - 1 if index != 0 else numChildren - 1
			elif oldIterAngle < (angle + _TWOPI) and (angle + _TWOPI <= iterAngle):
				return index - 1 if index != 0 else numChildren - 1
			oldIterAngle = iterAngle


class PieArtist(object):

	ICON_SIZE_DEFAULT = 48

	SHAPE_CIRCLE = "circle"
	SHAPE_SQUARE = "square"
	DEFAULT_SHAPE = SHAPE_SQUARE

	BACKGROUND_FILL = "fill"
	BACKGROUND_NOFILL = "no fill"

	def __init__(self, filing, background = BACKGROUND_FILL):
		self._filing = filing

		self._cachedOuterRadius = self._filing.outerRadius()
		self._cachedInnerRadius = self._filing.innerRadius()
		canvasSize = self._cachedOuterRadius * 2 + 1
		self._canvas = QtGui.QPixmap(canvasSize, canvasSize)
		self._mask = None
		self._backgroundState = background
		self.palette = None

	def pieSize(self):
		diameter = self._filing.outerRadius() * 2 + 1
		return QtCore.QSize(diameter, diameter)

	def centerSize(self):
		painter = QtGui.QPainter(self._canvas)
		text = self._filing.center().action().text()
		fontMetrics = painter.fontMetrics()
		if text:
			textBoundingRect = fontMetrics.boundingRect(text)
		else:
			textBoundingRect = QtCore.QRect()
		textWidth = textBoundingRect.width()
		textHeight = textBoundingRect.height()

		return QtCore.QSize(
			textWidth + self.ICON_SIZE_DEFAULT,
			max(textHeight, self.ICON_SIZE_DEFAULT),
		)

	def show(self, palette):
		self.palette = palette

		if (
			self._cachedOuterRadius != self._filing.outerRadius() or
			self._cachedInnerRadius != self._filing.innerRadius()
		):
			self._cachedOuterRadius = self._filing.outerRadius()
			self._cachedInnerRadius = self._filing.innerRadius()
			self._canvas = self._canvas.scaled(self.pieSize())

		if self._mask is None:
			self._mask = QtGui.QBitmap(self._canvas.size())
			self._mask.fill(QtCore.Qt.color0)
			self._generate_mask(self._mask)
			self._canvas.setMask(self._mask)
		return self._mask

	def hide(self):
		self.palette = None

	def paint(self, selectionIndex):
		painter = QtGui.QPainter(self._canvas)
		painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

		self.paintPainter(selectionIndex, painter)

		return self._canvas

	def paintPainter(self, selectionIndex, painter):
		adjustmentRect = painter.viewport().adjusted(0, 0, -1, -1)

		numChildren = len(self._filing)
		if numChildren == 0:
			self._paint_center_background(painter, adjustmentRect, selectionIndex)
			self._paint_center_foreground(painter, adjustmentRect, selectionIndex)
			return self._canvas
		else:
			for i in xrange(len(self._filing)):
				self._paint_slice_background(painter, adjustmentRect, i, selectionIndex)

		self._paint_center_background(painter, adjustmentRect, selectionIndex)
		self._paint_center_foreground(painter, adjustmentRect, selectionIndex)

		for i in xrange(len(self._filing)):
			self._paint_slice_foreground(painter, adjustmentRect, i, selectionIndex)

	def _generate_mask(self, mask):
		"""
		Specifies on the mask the shape of the pie menu
		"""
		painter = QtGui.QPainter(mask)
		painter.setPen(QtCore.Qt.color1)
		painter.setBrush(QtCore.Qt.color1)
		if self.DEFAULT_SHAPE == self.SHAPE_SQUARE:
			painter.drawRect(mask.rect())
		elif self.DEFAULT_SHAPE == self.SHAPE_CIRCLE:
			painter.drawEllipse(mask.rect().adjusted(0, 0, -1, -1))
		else:
			raise NotImplementedError(self.DEFAULT_SHAPE)

	def _paint_slice_background(self, painter, adjustmentRect, i, selectionIndex):
		if self.DEFAULT_SHAPE == self.SHAPE_SQUARE:
			currentWidth = adjustmentRect.width()
			newWidth = math.sqrt(2) * currentWidth
			dx = (newWidth - currentWidth) / 2
			adjustmentRect = adjustmentRect.adjusted(-dx, -dx, dx, dx)
		elif self.DEFAULT_SHAPE == self.SHAPE_CIRCLE:
			pass
		else:
			raise NotImplementedError(self.DEFAULT_SHAPE)

		if self._backgroundState == self.BACKGROUND_NOFILL:
			painter.setBrush(QtGui.QBrush(QtCore.Qt.transparent))
			painter.setPen(self.palette.highlight().color())
		else:
			if i == selectionIndex and self._filing[i].isEnabled():
				painter.setBrush(self.palette.highlight())
				painter.setPen(self.palette.highlight().color())
			else:
				painter.setBrush(self.palette.window())
				painter.setPen(self.palette.window().color())

		a = self._filing._index_to_angle(i, True)
		b = self._filing._index_to_angle(i + 1, True)
		if b < a:
			b += _TWOPI
		size = b - a
		if size < 0:
			size += _TWOPI

		startAngleInDeg = (a * 360 * 16) / _TWOPI
		sizeInDeg = (size * 360 * 16) / _TWOPI
		painter.drawPie(adjustmentRect, int(startAngleInDeg), int(sizeInDeg))

	def _paint_slice_foreground(self, painter, adjustmentRect, i, selectionIndex):
		child = self._filing[i]

		a = self._filing._index_to_angle(i, True)
		b = self._filing._index_to_angle(i + 1, True)
		if b < a:
			b += _TWOPI
		middleAngle = (a + b) / 2
		averageRadius = (self._cachedInnerRadius + self._cachedOuterRadius) / 2

		sliceX = averageRadius * math.cos(middleAngle)
		sliceY = - averageRadius * math.sin(middleAngle)

		piePos = adjustmentRect.center()
		pieX = piePos.x()
		pieY = piePos.y()
		self._paint_label(
			painter, child.action(), i == selectionIndex, pieX+sliceX, pieY+sliceY
		)

	def _paint_label(self, painter, action, isSelected, x, y):
		text = action.text()
		fontMetrics = painter.fontMetrics()
		if text:
			textBoundingRect = fontMetrics.boundingRect(text)
		else:
			textBoundingRect = QtCore.QRect()
		textWidth = textBoundingRect.width()
		textHeight = textBoundingRect.height()

		icon = action.icon().pixmap(
			QtCore.QSize(self.ICON_SIZE_DEFAULT, self.ICON_SIZE_DEFAULT),
			QtGui.QIcon.Normal,
			QtGui.QIcon.On,
		)
		iconWidth = icon.width()
		iconHeight = icon.width()
		averageWidth = (iconWidth + textWidth)/2
		if not icon.isNull():
			iconRect = QtCore.QRect(
				x - averageWidth,
				y - iconHeight/2,
				iconWidth,
				iconHeight,
			)

			painter.drawPixmap(iconRect, icon)

		if text:
			if isSelected:
				if action.isEnabled():
					pen = self.palette.highlightedText()
					brush = self.palette.highlight()
				else:
					pen = self.palette.mid()
					brush = self.palette.window()
			else:
				if action.isEnabled():
					pen = self.palette.windowText()
				else:
					pen = self.palette.mid()
				brush = self.palette.window()

			leftX = x - averageWidth + iconWidth
			topY = y + textHeight/2
			painter.setPen(pen.color())
			painter.setBrush(brush)
			painter.drawText(leftX, topY, text)

	def _paint_center_background(self, painter, adjustmentRect, selectionIndex):
		if self._backgroundState == self.BACKGROUND_NOFILL:
			return
		if len(self._filing) == 0:
			if self._backgroundState == self.BACKGROUND_NOFILL:
				painter.setBrush(QtGui.QBrush(QtCore.Qt.transparent))
			else:
				if selectionIndex == PieFiling.SELECTION_CENTER and self._filing.center().isEnabled():
					painter.setBrush(self.palette.highlight())
				else:
					painter.setBrush(self.palette.window())
			painter.setPen(self.palette.mid().color())

			painter.drawRect(adjustmentRect)
		else:
			dark = self.palette.mid().color()
			light = self.palette.light().color()
			if self._backgroundState == self.BACKGROUND_NOFILL:
				background = QtGui.QBrush(QtCore.Qt.transparent)
			else:
				if selectionIndex == PieFiling.SELECTION_CENTER and self._filing.center().isEnabled():
					background = self.palette.highlight().color()
				else:
					background = self.palette.window().color()

			innerRadius = self._cachedInnerRadius
			adjustmentCenterPos = adjustmentRect.center()
			innerRect = QtCore.QRect(
				adjustmentCenterPos.x() - innerRadius,
				adjustmentCenterPos.y() - innerRadius,
				innerRadius * 2 + 1,
				innerRadius * 2 + 1,
			)

			painter.setPen(QtCore.Qt.NoPen)
			painter.setBrush(background)
			painter.drawPie(innerRect, 0, 360 * 16)

			if self.DEFAULT_SHAPE == self.SHAPE_SQUARE:
				pass
			elif self.DEFAULT_SHAPE == self.SHAPE_CIRCLE:
				painter.setPen(QtGui.QPen(dark, 1))
				painter.setBrush(QtCore.Qt.NoBrush)
				painter.drawEllipse(adjustmentRect)
			else:
				raise NotImplementedError(self.DEFAULT_SHAPE)

	def _paint_center_foreground(self, painter, adjustmentRect, selectionIndex):
		centerPos = adjustmentRect.center()
		pieX = centerPos.x()
		pieY = centerPos.y()

		x = pieX
		y = pieY

		self._paint_label(
			painter,
			self._filing.center().action(),
			selectionIndex == PieFiling.SELECTION_CENTER,
			x, y
		)


class QPieDisplay(QtGui.QWidget):

	def __init__(self, filing, parent = None, flags = QtCore.Qt.Window):
		QtGui.QWidget.__init__(self, parent, flags)
		self._filing = filing
		self._artist = PieArtist(self._filing)
		self._selectionIndex = PieFiling.SELECTION_NONE

	def popup(self, pos):
		self._update_selection(pos)
		self.show()

	def sizeHint(self):
		return self._artist.pieSize()

	@misc_utils.log_exception(_moduleLogger)
	def showEvent(self, showEvent):
		mask = self._artist.show(self.palette())
		self.setMask(mask)

		QtGui.QWidget.showEvent(self, showEvent)

	@misc_utils.log_exception(_moduleLogger)
	def hideEvent(self, hideEvent):
		self._artist.hide()
		self._selectionIndex = PieFiling.SELECTION_NONE
		QtGui.QWidget.hideEvent(self, hideEvent)

	@misc_utils.log_exception(_moduleLogger)
	def paintEvent(self, paintEvent):
		canvas = self._artist.paint(self._selectionIndex)
		offset = (self.size() - canvas.size()) / 2

		screen = QtGui.QPainter(self)
		screen.drawPixmap(QtCore.QPoint(offset.width(), offset.height()), canvas)

		QtGui.QWidget.paintEvent(self, paintEvent)

	def selectAt(self, index):
		oldIndex = self._selectionIndex
		self._selectionIndex = index
		if self.isVisible():
			self.update()


class QPieButton(QtGui.QWidget):

	activated = qt_compat.Signal(int)
	highlighted = qt_compat.Signal(int)
	canceled = qt_compat.Signal()
	aboutToShow = qt_compat.Signal()
	aboutToHide = qt_compat.Signal()

	BUTTON_RADIUS = 24
	DELAY = 250

	def __init__(self, buttonSlice, parent = None, buttonSlices = None):
		# @bug Artifacts on Maemo 5 due to window 3D effects, find way to disable them for just these?
		# @bug The pie's are being pushed back on screen on Maemo, leading to coordinate issues
		QtGui.QWidget.__init__(self, parent)
		self._cachedCenterPosition = self.rect().center()

		self._filing = PieFiling()
		self._display = QPieDisplay(self._filing, None, QtCore.Qt.SplashScreen)
		self._selectionIndex = PieFiling.SELECTION_NONE

		self._buttonFiling = PieFiling()
		self._buttonFiling.set_center(buttonSlice)
		if buttonSlices is not None:
			for slice in buttonSlices:
				self._buttonFiling.insertItem(slice)
		self._buttonFiling.setOuterRadius(self.BUTTON_RADIUS)
		self._buttonArtist = PieArtist(self._buttonFiling, PieArtist.BACKGROUND_NOFILL)
		self._poppedUp = False
		self._pressed = False

		self._delayPopupTimer = QtCore.QTimer()
		self._delayPopupTimer.setInterval(self.DELAY)
		self._delayPopupTimer.setSingleShot(True)
		self._delayPopupTimer.timeout.connect(self._on_delayed_popup)
		self._popupLocation = None

		self._mousePosition = None
		self.setFocusPolicy(QtCore.Qt.StrongFocus)
		self.setSizePolicy(
			QtGui.QSizePolicy(
				QtGui.QSizePolicy.MinimumExpanding,
				QtGui.QSizePolicy.MinimumExpanding,
			)
		)

	def insertItem(self, item, index = -1):
		self._filing.insertItem(item, index)

	def removeItemAt(self, index):
		self._filing.removeItemAt(index)

	def set_center(self, item):
		self._filing.set_center(item)

	def set_button(self, item):
		self.update()

	def clear(self):
		self._filing.clear()

	def itemAt(self, index):
		return self._filing.itemAt(index)

	def indexAt(self, point):
		return self._filing.indexAt(self._cachedCenterPosition, point)

	def innerRadius(self):
		return self._filing.innerRadius()

	def setInnerRadius(self, radius):
		self._filing.setInnerRadius(radius)

	def outerRadius(self):
		return self._filing.outerRadius()

	def setOuterRadius(self, radius):
		self._filing.setOuterRadius(radius)

	def buttonRadius(self):
		return self._buttonFiling.outerRadius()

	def setButtonRadius(self, radius):
		self._buttonFiling.setOuterRadius(radius)
		self._buttonFiling.setInnerRadius(radius / 2)
		self._buttonArtist.show(self.palette())

	def minimumSizeHint(self):
		return self._buttonArtist.centerSize()

	@misc_utils.log_exception(_moduleLogger)
	def mousePressEvent(self, mouseEvent):
		lastSelection = self._selectionIndex

		lastMousePos = mouseEvent.pos()
		self._mousePosition = lastMousePos
		self._update_selection(self._cachedCenterPosition)

		self.highlighted.emit(self._selectionIndex)

		self._display.selectAt(self._selectionIndex)
		self._pressed = True
		self.update()
		self._popupLocation = mouseEvent.globalPos()
		self._delayPopupTimer.start()

	@misc_utils.log_exception(_moduleLogger)
	def _on_delayed_popup(self):
		assert self._popupLocation is not None, "Widget location abuse"
		self._popup_child(self._popupLocation)

	@misc_utils.log_exception(_moduleLogger)
	def mouseMoveEvent(self, mouseEvent):
		lastSelection = self._selectionIndex

		lastMousePos = mouseEvent.pos()
		if self._mousePosition is None:
			# Absolute
			self._update_selection(lastMousePos)
		else:
			# Relative
			self._update_selection(
				self._cachedCenterPosition + (lastMousePos - self._mousePosition),
				ignoreOuter = True,
			)

		if lastSelection != self._selectionIndex:
			self.highlighted.emit(self._selectionIndex)
			self._display.selectAt(self._selectionIndex)

		if self._selectionIndex != PieFiling.SELECTION_CENTER and self._delayPopupTimer.isActive():
			self._on_delayed_popup()

	@misc_utils.log_exception(_moduleLogger)
	def mouseReleaseEvent(self, mouseEvent):
		self._delayPopupTimer.stop()
		self._popupLocation = None

		lastSelection = self._selectionIndex

		lastMousePos = mouseEvent.pos()
		if self._mousePosition is None:
			# Absolute
			self._update_selection(lastMousePos)
		else:
			# Relative
			self._update_selection(
				self._cachedCenterPosition + (lastMousePos - self._mousePosition),
				ignoreOuter = True,
			)
		self._mousePosition = None

		self._activate_at(self._selectionIndex)
		self._pressed = False
		self.update()
		self._hide_child()

	@misc_utils.log_exception(_moduleLogger)
	def keyPressEvent(self, keyEvent):
		if keyEvent.key() in [QtCore.Qt.Key_Right, QtCore.Qt.Key_Down, QtCore.Qt.Key_Tab]:
			self._popup_child(QtGui.QCursor.pos())
			if self._selectionIndex != len(self._filing) - 1:
				nextSelection = self._selectionIndex + 1
			else:
				nextSelection = 0
			self._select_at(nextSelection)
			self._display.selectAt(self._selectionIndex)
		elif keyEvent.key() in [QtCore.Qt.Key_Left, QtCore.Qt.Key_Up, QtCore.Qt.Key_Backtab]:
			self._popup_child(QtGui.QCursor.pos())
			if 0 < self._selectionIndex:
				nextSelection = self._selectionIndex - 1
			else:
				nextSelection = len(self._filing) - 1
			self._select_at(nextSelection)
			self._display.selectAt(self._selectionIndex)
		elif keyEvent.key() in [QtCore.Qt.Key_Space]:
			self._popup_child(QtGui.QCursor.pos())
			self._select_at(PieFiling.SELECTION_CENTER)
			self._display.selectAt(self._selectionIndex)
		elif keyEvent.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Space]:
			self._delayPopupTimer.stop()
			self._popupLocation = None
			self._activate_at(self._selectionIndex)
			self._hide_child()
		elif keyEvent.key() in [QtCore.Qt.Key_Escape, QtCore.Qt.Key_Backspace]:
			self._delayPopupTimer.stop()
			self._popupLocation = None
			self._activate_at(PieFiling.SELECTION_NONE)
			self._hide_child()
		else:
			QtGui.QWidget.keyPressEvent(self, keyEvent)

	@misc_utils.log_exception(_moduleLogger)
	def resizeEvent(self, resizeEvent):
		self.setButtonRadius(min(resizeEvent.size().width(), resizeEvent.size().height()) / 2 - 1)
		QtGui.QWidget.resizeEvent(self, resizeEvent)

	@misc_utils.log_exception(_moduleLogger)
	def showEvent(self, showEvent):
		self._buttonArtist.show(self.palette())
		self._cachedCenterPosition = self.rect().center()

		QtGui.QWidget.showEvent(self, showEvent)

	@misc_utils.log_exception(_moduleLogger)
	def hideEvent(self, hideEvent):
		self._display.hide()
		self._select_at(PieFiling.SELECTION_NONE)
		QtGui.QWidget.hideEvent(self, hideEvent)

	@misc_utils.log_exception(_moduleLogger)
	def paintEvent(self, paintEvent):
		self.setButtonRadius(min(self.rect().width(), self.rect().height()) / 2 - 1)
		if self._poppedUp:
			selectionIndex = PieFiling.SELECTION_CENTER
		else:
			selectionIndex = PieFiling.SELECTION_NONE

		screen = QtGui.QStylePainter(self)
		screen.setRenderHint(QtGui.QPainter.Antialiasing, True)
		option = QtGui.QStyleOptionButton()
		option.initFrom(self)
		option.state = QtGui.QStyle.State_Sunken if self._pressed else QtGui.QStyle.State_Raised

		screen.drawControl(QtGui.QStyle.CE_PushButton, option)
		self._buttonArtist.paintPainter(selectionIndex, screen)

		QtGui.QWidget.paintEvent(self, paintEvent)

	def __iter__(self):
		return iter(self._filing)

	def __len__(self):
		return len(self._filing)

	def _popup_child(self, position):
		self._poppedUp = True
		self.aboutToShow.emit()

		self._delayPopupTimer.stop()
		self._popupLocation = None

		position = position - QtCore.QPoint(self._filing.outerRadius(), self._filing.outerRadius())
		self._display.move(position)
		self._display.show()

		self.update()

	def _hide_child(self):
		self._poppedUp = False
		self.aboutToHide.emit()
		self._display.hide()
		self.update()

	def _select_at(self, index):
		self._selectionIndex = index

	def _update_selection(self, lastMousePos, ignoreOuter = False):
		radius = _radius_at(self._cachedCenterPosition, lastMousePos)
		if radius < self._filing.innerRadius():
			self._select_at(PieFiling.SELECTION_CENTER)
		elif radius <= self._filing.outerRadius() or ignoreOuter:
			self._select_at(self.indexAt(lastMousePos))
		else:
			self._select_at(PieFiling.SELECTION_NONE)

	def _activate_at(self, index):
		if index == PieFiling.SELECTION_NONE:
			self.canceled.emit()
			return
		elif index == PieFiling.SELECTION_CENTER:
			child = self._filing.center()
		else:
			child = self.itemAt(index)

		if child.action().isEnabled():
			child.action().trigger()
			self.activated.emit(index)
		else:
			self.canceled.emit()


class QPieMenu(QtGui.QWidget):

	activated = qt_compat.Signal(int)
	highlighted = qt_compat.Signal(int)
	canceled = qt_compat.Signal()
	aboutToShow = qt_compat.Signal()
	aboutToHide = qt_compat.Signal()

	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self._cachedCenterPosition = self.rect().center()

		self._filing = PieFiling()
		self._artist = PieArtist(self._filing)
		self._selectionIndex = PieFiling.SELECTION_NONE

		self._mousePosition = ()
		self.setFocusPolicy(QtCore.Qt.StrongFocus)

	def popup(self, pos):
		self._update_selection(pos)
		self.show()

	def insertItem(self, item, index = -1):
		self._filing.insertItem(item, index)
		self.update()

	def removeItemAt(self, index):
		self._filing.removeItemAt(index)
		self.update()

	def set_center(self, item):
		self._filing.set_center(item)
		self.update()

	def clear(self):
		self._filing.clear()
		self.update()

	def itemAt(self, index):
		return self._filing.itemAt(index)

	def indexAt(self, point):
		return self._filing.indexAt(self._cachedCenterPosition, point)

	def innerRadius(self):
		return self._filing.innerRadius()

	def setInnerRadius(self, radius):
		self._filing.setInnerRadius(radius)
		self.update()

	def outerRadius(self):
		return self._filing.outerRadius()

	def setOuterRadius(self, radius):
		self._filing.setOuterRadius(radius)
		self.update()

	def sizeHint(self):
		return self._artist.pieSize()

	@misc_utils.log_exception(_moduleLogger)
	def mousePressEvent(self, mouseEvent):
		lastSelection = self._selectionIndex

		lastMousePos = mouseEvent.pos()
		self._update_selection(lastMousePos)
		self._mousePosition = lastMousePos

		if lastSelection != self._selectionIndex:
			self.highlighted.emit(self._selectionIndex)
			self.update()

	@misc_utils.log_exception(_moduleLogger)
	def mouseMoveEvent(self, mouseEvent):
		lastSelection = self._selectionIndex

		lastMousePos = mouseEvent.pos()
		self._update_selection(lastMousePos)

		if lastSelection != self._selectionIndex:
			self.highlighted.emit(self._selectionIndex)
			self.update()

	@misc_utils.log_exception(_moduleLogger)
	def mouseReleaseEvent(self, mouseEvent):
		lastSelection = self._selectionIndex

		lastMousePos = mouseEvent.pos()
		self._update_selection(lastMousePos)
		self._mousePosition = ()

		self._activate_at(self._selectionIndex)
		self.update()

	@misc_utils.log_exception(_moduleLogger)
	def keyPressEvent(self, keyEvent):
		if keyEvent.key() in [QtCore.Qt.Key_Right, QtCore.Qt.Key_Down, QtCore.Qt.Key_Tab]:
			if self._selectionIndex != len(self._filing) - 1:
				nextSelection = self._selectionIndex + 1
			else:
				nextSelection = 0
			self._select_at(nextSelection)
			self.update()
		elif keyEvent.key() in [QtCore.Qt.Key_Left, QtCore.Qt.Key_Up, QtCore.Qt.Key_Backtab]:
			if 0 < self._selectionIndex:
				nextSelection = self._selectionIndex - 1
			else:
				nextSelection = len(self._filing) - 1
			self._select_at(nextSelection)
			self.update()
		elif keyEvent.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Space]:
			self._activate_at(self._selectionIndex)
		elif keyEvent.key() in [QtCore.Qt.Key_Escape, QtCore.Qt.Key_Backspace]:
			self._activate_at(PieFiling.SELECTION_NONE)
		else:
			QtGui.QWidget.keyPressEvent(self, keyEvent)

	@misc_utils.log_exception(_moduleLogger)
	def showEvent(self, showEvent):
		self.aboutToShow.emit()
		self._cachedCenterPosition = self.rect().center()

		mask = self._artist.show(self.palette())
		self.setMask(mask)

		lastMousePos = self.mapFromGlobal(QtGui.QCursor.pos())
		self._update_selection(lastMousePos)

		QtGui.QWidget.showEvent(self, showEvent)

	@misc_utils.log_exception(_moduleLogger)
	def hideEvent(self, hideEvent):
		self._artist.hide()
		self._selectionIndex = PieFiling.SELECTION_NONE
		QtGui.QWidget.hideEvent(self, hideEvent)

	@misc_utils.log_exception(_moduleLogger)
	def paintEvent(self, paintEvent):
		canvas = self._artist.paint(self._selectionIndex)

		screen = QtGui.QPainter(self)
		screen.drawPixmap(QtCore.QPoint(0, 0), canvas)

		QtGui.QWidget.paintEvent(self, paintEvent)

	def __iter__(self):
		return iter(self._filing)

	def __len__(self):
		return len(self._filing)

	def _select_at(self, index):
		self._selectionIndex = index

	def _update_selection(self, lastMousePos):
		radius = _radius_at(self._cachedCenterPosition, lastMousePos)
		if radius < self._filing.innerRadius():
			self._selectionIndex = PieFiling.SELECTION_CENTER
		elif radius <= self._filing.outerRadius():
			self._select_at(self.indexAt(lastMousePos))
		else:
			self._selectionIndex = PieFiling.SELECTION_NONE

	def _activate_at(self, index):
		if index == PieFiling.SELECTION_NONE:
			self.canceled.emit()
			self.aboutToHide.emit()
			self.hide()
			return
		elif index == PieFiling.SELECTION_CENTER:
			child = self._filing.center()
		else:
			child = self.itemAt(index)

		if child.isEnabled():
			child.action().trigger()
			self.activated.emit(index)
		else:
			self.canceled.emit()
		self.aboutToHide.emit()
		self.hide()


def init_pies():
	PieFiling.NULL_CENTER.setEnabled(False)


def _print(msg):
	print msg


def _on_about_to_hide(app):
	app.exit()


if __name__ == "__main__":
	app = QtGui.QApplication([])
	init_pies()

	if False:
		pie = QPieMenu()
		pie.show()

	if False:
		singleAction = QtGui.QAction(None)
		singleAction.setText("Boo")
		singleItem = QActionPieItem(singleAction)
		spie = QPieMenu()
		spie.insertItem(singleItem)
		spie.show()

	if False:
		oneAction = QtGui.QAction(None)
		oneAction.setText("Chew")
		oneItem = QActionPieItem(oneAction)
		twoAction = QtGui.QAction(None)
		twoAction.setText("Foo")
		twoItem = QActionPieItem(twoAction)
		iconTextAction = QtGui.QAction(None)
		iconTextAction.setText("Icon")
		iconTextAction.setIcon(QtGui.QIcon.fromTheme("gtk-close"))
		iconTextItem = QActionPieItem(iconTextAction)
		mpie = QPieMenu()
		mpie.insertItem(oneItem)
		mpie.insertItem(twoItem)
		mpie.insertItem(oneItem)
		mpie.insertItem(iconTextItem)
		mpie.show()

	if True:
		oneAction = QtGui.QAction(None)
		oneAction.setText("Chew")
		oneAction.triggered.connect(lambda: _print("Chew"))
		oneItem = QActionPieItem(oneAction)
		twoAction = QtGui.QAction(None)
		twoAction.setText("Foo")
		twoAction.triggered.connect(lambda: _print("Foo"))
		twoItem = QActionPieItem(twoAction)
		iconAction = QtGui.QAction(None)
		iconAction.setIcon(QtGui.QIcon.fromTheme("gtk-open"))
		iconAction.triggered.connect(lambda: _print("Icon"))
		iconItem = QActionPieItem(iconAction)
		iconTextAction = QtGui.QAction(None)
		iconTextAction.setText("Icon")
		iconTextAction.setIcon(QtGui.QIcon.fromTheme("gtk-close"))
		iconTextAction.triggered.connect(lambda: _print("Icon and text"))
		iconTextItem = QActionPieItem(iconTextAction)
		mpie = QPieMenu()
		mpie.set_center(iconItem)
		mpie.insertItem(oneItem)
		mpie.insertItem(twoItem)
		mpie.insertItem(oneItem)
		mpie.insertItem(iconTextItem)
		mpie.show()
		mpie.aboutToHide.connect(lambda: _on_about_to_hide(app))
		mpie.canceled.connect(lambda: _print("Canceled"))

	if False:
		oneAction = QtGui.QAction(None)
		oneAction.setText("Chew")
		oneAction.triggered.connect(lambda: _print("Chew"))
		oneItem = QActionPieItem(oneAction)
		twoAction = QtGui.QAction(None)
		twoAction.setText("Foo")
		twoAction.triggered.connect(lambda: _print("Foo"))
		twoItem = QActionPieItem(twoAction)
		iconAction = QtGui.QAction(None)
		iconAction.setIcon(QtGui.QIcon.fromTheme("gtk-open"))
		iconAction.triggered.connect(lambda: _print("Icon"))
		iconItem = QActionPieItem(iconAction)
		iconTextAction = QtGui.QAction(None)
		iconTextAction.setText("Icon")
		iconTextAction.setIcon(QtGui.QIcon.fromTheme("gtk-close"))
		iconTextAction.triggered.connect(lambda: _print("Icon and text"))
		iconTextItem = QActionPieItem(iconTextAction)
		pieFiling = PieFiling()
		pieFiling.set_center(iconItem)
		pieFiling.insertItem(oneItem)
		pieFiling.insertItem(twoItem)
		pieFiling.insertItem(oneItem)
		pieFiling.insertItem(iconTextItem)
		mpie = QPieDisplay(pieFiling)
		mpie.show()

	if False:
		oneAction = QtGui.QAction(None)
		oneAction.setText("Chew")
		oneAction.triggered.connect(lambda: _print("Chew"))
		oneItem = QActionPieItem(oneAction)
		twoAction = QtGui.QAction(None)
		twoAction.setText("Foo")
		twoAction.triggered.connect(lambda: _print("Foo"))
		twoItem = QActionPieItem(twoAction)
		iconAction = QtGui.QAction(None)
		iconAction.setIcon(QtGui.QIcon.fromTheme("gtk-open"))
		iconAction.triggered.connect(lambda: _print("Icon"))
		iconItem = QActionPieItem(iconAction)
		iconTextAction = QtGui.QAction(None)
		iconTextAction.setText("Icon")
		iconTextAction.setIcon(QtGui.QIcon.fromTheme("gtk-close"))
		iconTextAction.triggered.connect(lambda: _print("Icon and text"))
		iconTextItem = QActionPieItem(iconTextAction)
		mpie = QPieButton(iconItem)
		mpie.set_center(iconItem)
		mpie.insertItem(oneItem)
		mpie.insertItem(twoItem)
		mpie.insertItem(oneItem)
		mpie.insertItem(iconTextItem)
		mpie.show()
		mpie.aboutToHide.connect(lambda: _on_about_to_hide(app))
		mpie.canceled.connect(lambda: _print("Canceled"))

	app.exec_()
