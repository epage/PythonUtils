#!/usr/bin/env python

"""
Open Issues
	@bug not all of a message is shown
	@bug Buttons are too small
"""


import gobject
import gtk
import dbus


class _NullHildonModule(object):
	pass


try:
	import hildon as _hildon
	hildon  = _hildon # Dumb but gets around pyflakiness
except (ImportError, OSError):
	hildon = _NullHildonModule


IS_HILDON_SUPPORTED = hildon is not _NullHildonModule


class _NullHildonProgram(object):

	def add_window(self, window):
		pass


def _hildon_get_app_class():
	return hildon.Program


def _null_get_app_class():
	return _NullHildonProgram


try:
	hildon.Program
	get_app_class = _hildon_get_app_class
except AttributeError:
	get_app_class = _null_get_app_class


def _hildon_set_application_name(name):
	gtk.set_application_name(name)


def _null_set_application_name(name):
	pass


try:
	gtk.set_application_name
	set_application_name = _hildon_set_application_name
except AttributeError:
	set_application_name = _null_set_application_name


def _fremantle_hildonize_window(app, window):
	oldWindow = window
	newWindow = hildon.StackableWindow()
	if oldWindow.get_child() is not None:
		oldWindow.get_child().reparent(newWindow)
	app.add_window(newWindow)
	return newWindow


def _hildon_hildonize_window(app, window):
	oldWindow = window
	newWindow = hildon.Window()
	if oldWindow.get_child() is not None:
		oldWindow.get_child().reparent(newWindow)
	app.add_window(newWindow)
	return newWindow


def _null_hildonize_window(app, window):
	return window


try:
	hildon.StackableWindow
	hildonize_window = _fremantle_hildonize_window
except AttributeError:
	try:
		hildon.Window
		hildonize_window = _hildon_hildonize_window
	except AttributeError:
		hildonize_window = _null_hildonize_window


def _fremantle_hildonize_menu(window, gtkMenu):
	appMenu = hildon.AppMenu()
	window.set_app_menu(appMenu)
	gtkMenu.get_parent().remove(gtkMenu)
	return appMenu


def _hildon_hildonize_menu(window, gtkMenu):
	hildonMenu = gtk.Menu()
	for child in gtkMenu.get_children():
		child.reparent(hildonMenu)
	window.set_menu(hildonMenu)
	gtkMenu.destroy()
	return hildonMenu


def _null_hildonize_menu(window, gtkMenu):
	return gtkMenu


try:
	hildon.AppMenu
	GTK_MENU_USED = False
	IS_FREMANTLE_SUPPORTED = True
	hildonize_menu = _fremantle_hildonize_menu
except AttributeError:
	GTK_MENU_USED = True
	IS_FREMANTLE_SUPPORTED = False
	if IS_HILDON_SUPPORTED:
		hildonize_menu = _hildon_hildonize_menu
	else:
		hildonize_menu = _null_hildonize_menu


def _hildon_set_button_auto_selectable(button):
	button.set_theme_size(hildon.HILDON_SIZE_AUTO_HEIGHT)


def _null_set_button_auto_selectable(button):
	pass


try:
	hildon.HILDON_SIZE_AUTO_HEIGHT
	gtk.Button.set_theme_size
	set_button_auto_selectable = _hildon_set_button_auto_selectable
except AttributeError:
	set_button_auto_selectable = _null_set_button_auto_selectable


def _hildon_set_button_finger_selectable(button):
	button.set_theme_size(hildon.HILDON_SIZE_FINGER_HEIGHT)


def _null_set_button_finger_selectable(button):
	pass


try:
	hildon.HILDON_SIZE_FINGER_HEIGHT
	gtk.Button.set_theme_size
	set_button_finger_selectable = _hildon_set_button_finger_selectable
except AttributeError:
	set_button_finger_selectable = _null_set_button_finger_selectable


def _hildon_set_button_thumb_selectable(button):
	button.set_theme_size(hildon.HILDON_SIZE_THUMB_HEIGHT)


def _null_set_button_thumb_selectable(button):
	pass


try:
	hildon.HILDON_SIZE_THUMB_HEIGHT
	gtk.Button.set_theme_size
	set_button_thumb_selectable = _hildon_set_button_thumb_selectable
except AttributeError:
	set_button_thumb_selectable = _null_set_button_thumb_selectable


def _hildon_set_cell_thumb_selectable(renderer):
	renderer.set_property("scale", 1.5)


def _null_set_cell_thumb_selectable(renderer):
	pass


if IS_HILDON_SUPPORTED:
	set_cell_thumb_selectable = _hildon_set_cell_thumb_selectable
else:
	set_cell_thumb_selectable = _null_set_cell_thumb_selectable


def _hildon_set_pix_cell_thumb_selectable(renderer):
	renderer.set_property("stock-size", 48)


def _null_set_pix_cell_thumb_selectable(renderer):
	pass


if IS_HILDON_SUPPORTED:
	set_pix_cell_thumb_selectable = _hildon_set_pix_cell_thumb_selectable
else:
	set_pix_cell_thumb_selectable = _null_set_pix_cell_thumb_selectable


def _fremantle_show_information_banner(parent, message):
	hildon.hildon_banner_show_information(parent, "", message)


def _hildon_show_information_banner(parent, message):
	hildon.hildon_banner_show_information(parent, None, message)


def _null_show_information_banner(parent, message):
	pass


if IS_FREMANTLE_SUPPORTED:
	show_information_banner = _fremantle_show_information_banner
else:
	try:
		hildon.hildon_banner_show_information
		show_information_banner = _hildon_show_information_banner
	except AttributeError:
		show_information_banner = _null_show_information_banner


def _fremantle_show_busy_banner_start(parent, message):
	hildon.hildon_gtk_window_set_progress_indicator(parent, True)
	return parent


def _fremantle_show_busy_banner_end(banner):
	hildon.hildon_gtk_window_set_progress_indicator(banner, False)


def _hildon_show_busy_banner_start(parent, message):
	return hildon.hildon_banner_show_animation(parent, None, message)


def _hildon_show_busy_banner_end(banner):
	banner.destroy()


def _null_show_busy_banner_start(parent, message):
	return None


def _null_show_busy_banner_end(banner):
	assert banner is None


try:
	hildon.hildon_gtk_window_set_progress_indicator
	show_busy_banner_start = _fremantle_show_busy_banner_start
	show_busy_banner_end = _fremantle_show_busy_banner_end
except AttributeError:
	try:
		hildon.hildon_banner_show_animation
		show_busy_banner_start = _hildon_show_busy_banner_start
		show_busy_banner_end = _hildon_show_busy_banner_end
	except AttributeError:
		show_busy_banner_start = _null_show_busy_banner_start
		show_busy_banner_end = _null_show_busy_banner_end


def _hildon_hildonize_text_entry(textEntry):
	textEntry.set_property('hildon-input-mode', 7)


def _null_hildonize_text_entry(textEntry):
	pass


if IS_HILDON_SUPPORTED:
	hildonize_text_entry = _hildon_hildonize_text_entry
else:
	hildonize_text_entry = _null_hildonize_text_entry


def _hildon_window_to_portrait(window):
	# gtk documentation is unclear whether this does a "=" or a "|="
	flags = hildon.PORTRAIT_MODE_SUPPORT | hildon.PORTRAIT_MODE_REQUEST
	hildon.hildon_gtk_window_set_portrait_flags(window, flags)


def _hildon_window_to_landscape(window):
	# gtk documentation is unclear whether this does a "=" or a "&= ~"
	flags = hildon.PORTRAIT_MODE_SUPPORT
	hildon.hildon_gtk_window_set_portrait_flags(window, flags)


def _null_window_to_portrait(window):
	pass


def _null_window_to_landscape(window):
	pass


try:
	hildon.PORTRAIT_MODE_SUPPORT
	hildon.PORTRAIT_MODE_REQUEST
	hildon.hildon_gtk_window_set_portrait_flags

	window_to_portrait = _hildon_window_to_portrait
	window_to_landscape = _hildon_window_to_landscape
except AttributeError:
	window_to_portrait = _null_window_to_portrait
	window_to_landscape = _null_window_to_landscape


def get_device_orientation():
	bus = dbus.SystemBus()
	try:
		rawMceRequest = bus.get_object("com.nokia.mce", "/com/nokia/mce/request")
		mceRequest = dbus.Interface(rawMceRequest, dbus_interface="com.nokia.mce.request")
		orientation, standState, faceState, xAxis, yAxis, zAxis = mceRequest.get_device_orientation()
	except dbus.exception.DBusException:
		# catching for documentation purposes that when a system doesn't
		# support this, this is what to expect
		raise

	if orientation == "":
		return gtk.ORIENTATION_HORIZONTAL
	elif orientation == "":
		return gtk.ORIENTATION_VERTICAL
	else:
		raise RuntimeError("Unknown orientation: %s" % orientation)


def _hildon_hildonize_password_entry(textEntry):
	textEntry.set_property('hildon-input-mode', 7 | (1 << 29))


def _null_hildonize_password_entry(textEntry):
	pass


if IS_HILDON_SUPPORTED:
	hildonize_password_entry = _hildon_hildonize_password_entry
else:
	hildonize_password_entry = _null_hildonize_password_entry


def _hildon_hildonize_combo_entry(comboEntry):
	comboEntry.set_property('hildon-input-mode', 1 << 4)


def _null_hildonize_combo_entry(textEntry):
	pass


if IS_HILDON_SUPPORTED:
	hildonize_combo_entry = _hildon_hildonize_combo_entry
else:
	hildonize_combo_entry = _null_hildonize_combo_entry


def _null_create_seekbar():
	adjustment = gtk.Adjustment(0, 0, 101, 1, 5, 1)
	seek = gtk.HScale(adjustment)
	seek.set_draw_value(False)
	return seek


def _fremantle_create_seekbar():
	seek = hildon.Seekbar()
	seek.set_range(0.0, 100)
	seek.set_draw_value(False)
	seek.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
	return seek


try:
	hildon.Seekbar
	create_seekbar = _fremantle_create_seekbar
except AttributeError:
	create_seekbar = _null_create_seekbar


def _fremantle_hildonize_scrollwindow(scrolledWindow):
	pannableWindow = hildon.PannableArea()

	child = scrolledWindow.get_child()
	scrolledWindow.remove(child)
	pannableWindow.add(child)

	parent = scrolledWindow.get_parent()
	if parent is not None:
		parent.remove(scrolledWindow)
		parent.add(pannableWindow)

	return pannableWindow


def _hildon_hildonize_scrollwindow(scrolledWindow):
	hildon.hildon_helper_set_thumb_scrollbar(scrolledWindow, True)
	return scrolledWindow


def _null_hildonize_scrollwindow(scrolledWindow):
	return scrolledWindow


try:
	hildon.PannableArea
	hildonize_scrollwindow = _fremantle_hildonize_scrollwindow
	hildonize_scrollwindow_with_viewport = _hildon_hildonize_scrollwindow
except AttributeError:
	try:
		hildon.hildon_helper_set_thumb_scrollbar
		hildonize_scrollwindow = _hildon_hildonize_scrollwindow
		hildonize_scrollwindow_with_viewport = _hildon_hildonize_scrollwindow
	except AttributeError:
		hildonize_scrollwindow = _null_hildonize_scrollwindow
		hildonize_scrollwindow_with_viewport = _null_hildonize_scrollwindow


def _hildon_request_number(parent, title, range, default):
	spinner = hildon.NumberEditor(*range)
	spinner.set_value(default)

	dialog = gtk.Dialog(
		title,
		parent,
		gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
		(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
	)
	dialog.set_default_response(gtk.RESPONSE_CANCEL)
	dialog.get_child().add(spinner)

	try:
		dialog.show_all()
		response = dialog.run()

		if response == gtk.RESPONSE_OK:
			return spinner.get_value()
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
	finally:
		dialog.hide()
		dialog.destroy()


def _null_request_number(parent, title, range, default):
	adjustment = gtk.Adjustment(default, range[0], range[1], 1, 5, 0)
	spinner = gtk.SpinButton(adjustment, 0, 0)
	spinner.set_wrap(False)

	dialog = gtk.Dialog(
		title,
		parent,
		gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
		(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
	)
	dialog.set_default_response(gtk.RESPONSE_CANCEL)
	dialog.get_child().add(spinner)

	try:
		dialog.show_all()
		response = dialog.run()

		if response == gtk.RESPONSE_OK:
			return spinner.get_value_as_int()
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
	finally:
		dialog.hide()
		dialog.destroy()


try:
	hildon.NumberEditor # TODO deprecated in fremantle
	request_number = _hildon_request_number
except AttributeError:
	request_number = _null_request_number


def _hildon_touch_selector(parent, title, items, defaultIndex):
	model = gtk.ListStore(gobject.TYPE_STRING)
	for item in items:
		model.append((item, ))

	selector = hildon.TouchSelector()
	selector.append_text_column(model, True)
	selector.set_column_selection_mode(hildon.TOUCH_SELECTOR_SELECTION_MODE_SINGLE)
	selector.set_active(0, defaultIndex)

	dialog = hildon.PickerDialog(parent)
	dialog.set_selector(selector)

	try:
		dialog.show_all()
		response = dialog.run()

		if response == gtk.RESPONSE_OK:
			return selector.get_active(0)
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
	finally:
		dialog.hide()
		dialog.destroy()


def _on_null_touch_selector_activated(treeView, path, column, dialog, pathData):
	dialog.response(gtk.RESPONSE_OK)
	pathData[0] = path


def _null_touch_selector(parent, title, items, defaultIndex = -1):
	parentSize = parent.get_size()

	model = gtk.ListStore(gobject.TYPE_STRING)
	for item in items:
		model.append((item, ))

	cell = gtk.CellRendererText()
	set_cell_thumb_selectable(cell)
	column = gtk.TreeViewColumn(title)
	column.pack_start(cell, expand=True)
	column.add_attribute(cell, "text", 0)

	treeView = gtk.TreeView()
	treeView.set_model(model)
	treeView.append_column(column)
	selection = treeView.get_selection()
	selection.set_mode(gtk.SELECTION_SINGLE)
	if 0 < defaultIndex:
		selection.select_path((defaultIndex, ))

	scrolledWin = gtk.ScrolledWindow()
	scrolledWin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
	scrolledWin.add(treeView)

	dialog = gtk.Dialog(
		title,
		parent,
		gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
		(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
	)
	dialog.set_default_response(gtk.RESPONSE_CANCEL)
	dialog.get_child().add(scrolledWin)
	dialog.resize(parentSize[0], max(parentSize[1]-100, 100))

	scrolledWin = hildonize_scrollwindow(scrolledWin)
	pathData = [None]
	treeView.connect("row-activated", _on_null_touch_selector_activated, dialog, pathData)

	try:
		dialog.show_all()
		response = dialog.run()

		if response == gtk.RESPONSE_OK:
			if pathData[0] is None:
				raise RuntimeError("No selection made")
			return pathData[0][0]
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
	finally:
		dialog.hide()
		dialog.destroy()


try:
	hildon.PickerDialog
	hildon.TouchSelector
	touch_selector = _hildon_touch_selector
except AttributeError:
	touch_selector = _null_touch_selector


def _hildon_touch_selector_entry(parent, title, items, defaultItem):
	# Got a segfault when using append_text_column with TouchSelectorEntry, so using this way
	try:
		selector = hildon.TouchSelectorEntry(text=True)
	except TypeError:
		selector = hildon.hildon_touch_selector_entry_new_text()
	defaultIndex = -1
	for i, item in enumerate(items):
		selector.append_text(item)
		if item == defaultItem:
			defaultIndex = i

	dialog = hildon.PickerDialog(parent)
	dialog.set_selector(selector)

	if 0 < defaultIndex:
		selector.set_active(0, defaultIndex)
	else:
		selector.get_entry().set_text(defaultItem)

	try:
		dialog.show_all()
		response = dialog.run()
	finally:
		dialog.hide()

	if response == gtk.RESPONSE_OK:
		return selector.get_entry().get_text()
	elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
		raise RuntimeError("User cancelled request")
	else:
		raise RuntimeError("Unrecognized response %r", response)


def _on_null_touch_selector_entry_entry_changed(entry, result, selection, defaultIndex):
	custom = entry.get_text().strip()
	if custom:
		result[0] = custom
		selection.unselect_all()
	else:
		result[0] = None
		selection.select_path((defaultIndex, ))


def _on_null_touch_selector_entry_entry_activated(customEntry, dialog, result):
	dialog.response(gtk.RESPONSE_OK)
	result[0] = customEntry.get_text()


def _on_null_touch_selector_entry_tree_activated(treeView, path, column, dialog, result):
	dialog.response(gtk.RESPONSE_OK)
	model = treeView.get_model()
	itr = model.get_iter(path)
	if itr is not None:
		result[0] = model.get_value(itr, 0)


def _null_touch_selector_entry(parent, title, items, defaultItem):
	parentSize = parent.get_size()

	model = gtk.ListStore(gobject.TYPE_STRING)
	defaultIndex = -1
	for i, item in enumerate(items):
		model.append((item, ))
		if item == defaultItem:
			defaultIndex = i

	cell = gtk.CellRendererText()
	set_cell_thumb_selectable(cell)
	column = gtk.TreeViewColumn(title)
	column.pack_start(cell, expand=True)
	column.add_attribute(cell, "text", 0)

	treeView = gtk.TreeView()
	treeView.set_model(model)
	treeView.append_column(column)
	selection = treeView.get_selection()
	selection.set_mode(gtk.SELECTION_SINGLE)

	scrolledWin = gtk.ScrolledWindow()
	scrolledWin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
	scrolledWin.add(treeView)

	customEntry = gtk.Entry()

	layout = gtk.VBox()
	layout.pack_start(customEntry, expand=False)
	layout.pack_start(scrolledWin)

	dialog = gtk.Dialog(
		title,
		parent,
		gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
		(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
	)
	dialog.set_default_response(gtk.RESPONSE_CANCEL)
	dialog.get_child().add(layout)
	dialog.resize(parentSize[0], max(parentSize[1]-100, 100))

	scrolledWin = hildonize_scrollwindow(scrolledWin)

	result = [None]
	if 0 < defaultIndex:
		selection.select_path((defaultIndex, ))
		result[0] = defaultItem
	else:
		customEntry.set_text(defaultItem)

	customEntry.connect("activate", _on_null_touch_selector_entry_entry_activated, dialog, result)
	customEntry.connect("changed", _on_null_touch_selector_entry_entry_changed, result, selection, defaultIndex)
	treeView.connect("row-activated", _on_null_touch_selector_entry_tree_activated, dialog, result)

	try:
		dialog.show_all()
		response = dialog.run()

		if response == gtk.RESPONSE_OK:
			_, itr = selection.get_selected()
			if itr is not None:
				return model.get_value(itr, 0)
			else:
				enteredText = customEntry.get_text().strip()
				if enteredText:
					return enteredText
				elif result[0] is not None:
					return result[0]
				else:
					raise RuntimeError("No selection made")
		elif response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
			raise RuntimeError("User cancelled request")
		else:
			raise RuntimeError("Unrecognized response %r", response)
	finally:
		dialog.hide()
		dialog.destroy()


try:
	hildon.PickerDialog
	hildon.TouchSelectorEntry
	touch_selector_entry = _hildon_touch_selector_entry
except AttributeError:
	touch_selector_entry = _null_touch_selector_entry


if __name__ == "__main__":
	app = get_app_class()()

	label = gtk.Label("Hello World from a Label!")

	win = gtk.Window()
	win.add(label)
	win = hildonize_window(app, win)
	if False and IS_FREMANTLE_SUPPORTED:
		appMenu = hildon.AppMenu()
		for i in xrange(5):
			b = gtk.Button(str(i))
			appMenu.append(b)
		win.set_app_menu(appMenu)
		win.show_all()
		appMenu.show_all()
		gtk.main()
	elif False:
		print touch_selector(win, "Test", ["A", "B", "C", "D"], 2)
	elif False:
		print touch_selector_entry(win, "Test", ["A", "B", "C", "D"], "C")
		print touch_selector_entry(win, "Test", ["A", "B", "C", "D"], "Blah")
	elif False:
		import pprint
		name, value = "", ""
		goodLocals = [
			(name, value) for (name, value) in locals().iteritems()
			if not name.startswith("_")
		]
		pprint.pprint(goodLocals)
	elif False:
		import time
		show_information_banner(win, "Hello World")
		time.sleep(5)
	elif False:
		import time
		banner = show_busy_banner_start(win, "Hello World")
		time.sleep(5)
		show_busy_banner_end(banner)
