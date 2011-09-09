import sys
import contextlib
import datetime
import logging

import qt_compat
QtCore = qt_compat.QtCore
QtGui = qt_compat.import_module("QtGui")
import qore_utils

import misc


_moduleLogger = logging.getLogger(__name__)


class ErrorDisplay(object):

	_SENTINEL_ICON = QtGui.QIcon()

	def __init__(self, errorLog):
		self._errorLog = errorLog
		self._errorLog.messagePushed.connect(self._on_message_pushed)
		self._errorLog.messagePopped.connect(self._on_message_popped)

		self._icons = None
		self._severityLabel = QtGui.QLabel()
		self._severityLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

		self._message = QtGui.QLabel()
		self._message.setText("Boo")
		self._message.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
		self._message.setWordWrap(True)

		self._closeLabel = None

		self._controlLayout = QtGui.QHBoxLayout()
		self._controlLayout.addWidget(self._severityLabel, 1, QtCore.Qt.AlignCenter)
		self._controlLayout.addWidget(self._message, 1000)

		self._widget = QtGui.QWidget()
		self._widget.setLayout(self._controlLayout)
		self._widget.hide()

	@property
	def toplevel(self):
		return self._widget

	def _show_error(self):
		if self._icons is None:
			self._icons = {
				qore_utils.QErrorMessage.LEVEL_BUSY:
					get_theme_icon(
						#("process-working", "view-refresh", "general_refresh", "gtk-refresh")
						("view-refresh", "general_refresh", "gtk-refresh", )
					).pixmap(32, 32),
				qore_utils.QErrorMessage.LEVEL_WARNING:
					get_theme_icon(
						("dialog-warning", )
					).pixmap(32, 32),
				qore_utils.QErrorMessage.LEVEL_INFO:
					get_theme_icon(
						("dialog-information", "general_notes", "gtk-info")
					).pixmap(32, 32),
				qore_utils.QErrorMessage.LEVEL_ERROR:
					get_theme_icon(
						("dialog-error", "app_install_error", "gtk-dialog-error")
					).pixmap(32, 32),
			}
		if self._closeLabel is None:
			closeIcon = get_theme_icon(("window-close", "general_close", "gtk-close"), self._SENTINEL_ICON)
			if closeIcon is not self._SENTINEL_ICON:
				self._closeLabel = QtGui.QPushButton(closeIcon, "")
			else:
				self._closeLabel = QtGui.QPushButton("X")
			self._closeLabel.clicked.connect(self._on_close)
			self._controlLayout.addWidget(self._closeLabel, 1, QtCore.Qt.AlignCenter)
		error = self._errorLog.peek_message()
		self._message.setText(error.message)
		self._severityLabel.setPixmap(self._icons[error.level])
		self._widget.show()

	@qt_compat.Slot()
	@qt_compat.Slot(bool)
	@misc.log_exception(_moduleLogger)
	def _on_close(self, checked = False):
		self._errorLog.pop()

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def _on_message_pushed(self):
		self._show_error()

	@qt_compat.Slot()
	@misc.log_exception(_moduleLogger)
	def _on_message_popped(self):
		if len(self._errorLog) == 0:
			self._message.setText("")
			self._widget.hide()
		else:
			self._show_error()


class QHtmlDelegate(QtGui.QStyledItemDelegate):

	UNDEFINED_SIZE = -1

	def __init__(self, *args, **kwd):
		QtGui.QStyledItemDelegate.__init__(*((self, ) + args), **kwd)
		self._width = self.UNDEFINED_SIZE

	def paint(self, painter, option, index):
		newOption = QtGui.QStyleOptionViewItemV4(option)
		self.initStyleOption(newOption, index)
		if newOption.widget is not None:
			style = newOption.widget.style()
		else:
			style = QtGui.QApplication.style()

		doc = QtGui.QTextDocument()
		doc.setHtml(newOption.text)
		doc.setTextWidth(newOption.rect.width())

		newOption.text = ""
		style.drawControl(QtGui.QStyle.CE_ItemViewItem, newOption, painter)

		ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
		if newOption.state & QtGui.QStyle.State_Selected:
			ctx.palette.setColor(
				QtGui.QPalette.Text,
				newOption.palette.color(
					QtGui.QPalette.Active,
					QtGui.QPalette.HighlightedText
				)
			)
		else:
			ctx.palette.setColor(
				QtGui.QPalette.Text,
				newOption.palette.color(
					QtGui.QPalette.Active,
					QtGui.QPalette.Text
				)
			)

		textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, newOption)
		painter.save()
		painter.translate(textRect.topLeft())
		painter.setClipRect(textRect.translated(-textRect.topLeft()))
		doc.documentLayout().draw(painter, ctx)
		painter.restore()

	def setWidth(self, width, model):
		if self._width == width:
			return
		self._width = width
		for c in xrange(model.rowCount()):
			cItem = model.item(c, 0)
			for r in xrange(model.rowCount()):
				rItem = cItem.child(r, 0)
				rIndex = model.indexFromItem(rItem)
				self.sizeHintChanged.emit(rIndex)
				return

	def sizeHint(self, option, index):
		newOption = QtGui.QStyleOptionViewItemV4(option)
		self.initStyleOption(newOption, index)

		doc = QtGui.QTextDocument()
		doc.setHtml(newOption.text)
		if self._width != self.UNDEFINED_SIZE:
			width = self._width
		else:
			width = newOption.rect.width()
		doc.setTextWidth(width)
		size = QtCore.QSize(doc.idealWidth(), doc.size().height())
		return size


class QSignalingMainWindow(QtGui.QMainWindow):

	closed = qt_compat.Signal()
	hidden = qt_compat.Signal()
	shown = qt_compat.Signal()
	resized = qt_compat.Signal()

	def __init__(self, *args, **kwd):
		QtGui.QMainWindow.__init__(*((self, )+args), **kwd)

	def closeEvent(self, event):
		val = QtGui.QMainWindow.closeEvent(self, event)
		self.closed.emit()
		return val

	def hideEvent(self, event):
		val = QtGui.QMainWindow.hideEvent(self, event)
		self.hidden.emit()
		return val

	def showEvent(self, event):
		val = QtGui.QMainWindow.showEvent(self, event)
		self.shown.emit()
		return val

	def resizeEvent(self, event):
		val = QtGui.QMainWindow.resizeEvent(self, event)
		self.resized.emit()
		return val

def set_current_index(selector, itemText, default = 0):
	for i in xrange(selector.count()):
		if selector.itemText(i) == itemText:
			selector.setCurrentIndex(i)
			break
	else:
		itemText.setCurrentIndex(default)


def _null_set_stackable(window, isStackable):
	pass


def _maemo_set_stackable(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow, isStackable)


try:
	QtCore.Qt.WA_Maemo5StackedWindow
	set_stackable = _maemo_set_stackable
except AttributeError:
	set_stackable = _null_set_stackable


def _null_set_autorient(window, doAutoOrient):
	pass


def _maemo_set_autorient(window, doAutoOrient):
	window.setAttribute(QtCore.Qt.WA_Maemo5AutoOrientation, doAutoOrient)


try:
	QtCore.Qt.WA_Maemo5AutoOrientation
	set_autorient = _maemo_set_autorient
except AttributeError:
	set_autorient = _null_set_autorient


def screen_orientation():
	geom = QtGui.QApplication.desktop().screenGeometry()
	if geom.width() <= geom.height():
		return QtCore.Qt.Vertical
	else:
		return QtCore.Qt.Horizontal


def _null_set_window_orientation(window, orientation):
	pass


def _maemo_set_window_orientation(window, orientation):
	if orientation == QtCore.Qt.Vertical:
		window.setAttribute(QtCore.Qt.WA_Maemo5LandscapeOrientation, False)
		window.setAttribute(QtCore.Qt.WA_Maemo5PortraitOrientation, True)
	elif orientation == QtCore.Qt.Horizontal:
		window.setAttribute(QtCore.Qt.WA_Maemo5LandscapeOrientation, True)
		window.setAttribute(QtCore.Qt.WA_Maemo5PortraitOrientation, False)
	elif orientation is None:
		window.setAttribute(QtCore.Qt.WA_Maemo5LandscapeOrientation, False)
		window.setAttribute(QtCore.Qt.WA_Maemo5PortraitOrientation, False)
	else:
		raise RuntimeError("Unknown orientation: %r" % orientation)


try:
	QtCore.Qt.WA_Maemo5LandscapeOrientation
	QtCore.Qt.WA_Maemo5PortraitOrientation
	set_window_orientation = _maemo_set_window_orientation
except AttributeError:
	set_window_orientation = _null_set_window_orientation


def _null_show_progress_indicator(window, isStackable):
	pass


def _maemo_show_progress_indicator(window, isStackable):
	window.setAttribute(QtCore.Qt.WA_Maemo5ShowProgressIndicator, isStackable)


try:
	QtCore.Qt.WA_Maemo5ShowProgressIndicator
	show_progress_indicator = _maemo_show_progress_indicator
except AttributeError:
	show_progress_indicator = _null_show_progress_indicator


def _null_mark_numbers_preferred(widget):
	pass


def _newqt_mark_numbers_preferred(widget):
	widget.setInputMethodHints(QtCore.Qt.ImhPreferNumbers)


try:
	QtCore.Qt.ImhPreferNumbers
	mark_numbers_preferred = _newqt_mark_numbers_preferred
except AttributeError:
	mark_numbers_preferred = _null_mark_numbers_preferred


def _null_get_theme_icon(iconNames, fallback = None):
	icon = fallback if fallback is not None else QtGui.QIcon()
	return icon


def _newqt_get_theme_icon(iconNames, fallback = None):
	for iconName in iconNames:
		if QtGui.QIcon.hasThemeIcon(iconName):
			icon = QtGui.QIcon.fromTheme(iconName)
			break
	else:
		icon = fallback if fallback is not None else QtGui.QIcon()
	return icon


try:
	QtGui.QIcon.fromTheme
	get_theme_icon = _newqt_get_theme_icon
except AttributeError:
	get_theme_icon = _null_get_theme_icon

