Python utilities
======================

PySide/PyQt
	qt_compat.py - Centralize the differences between PySide and PyQt
	qore_utils.py - Qt helpers that only depend on QtCore, including threading, models, QObject tools
	qui_utils.py - Qt helpers that depend on QtGui, including standardized error reporting mechanism, HTML Delegate, a QMainWindow that provides more signals Qt-Maemo5 graceful degredation
	qml_utils.py - I am still learning QML so these are still being defined
	qtpie.py - QWidget-based pie menus (See QWidget version of ejpi for an example)
	qtpieboard.py - QtPie keyboard (See QWidget version of ejpi for an example)
	qwrappers.py - Default implementation of objects owning QApplication and QMainWindow objects
PyGTK / Hildon Development:
	go_utils.py - Threading, API version compat, etc
	gtk_utils.py
	hildonize.py - Gracefully fallback when Hildon features are unavailable
	tp_utils - Telepathy tools
Other
	linux.py - XDG Helpers

Everything else is misc tools that fill in gaps for Python.  I don't really end up using them except for misc.log_exception I place around every single slot so to ease debugging users' applications.

Usage
======================
Copy what files you need into your tool

As you can tell by my skeleton project (https://github.com/epage/MaemoPythonSkeleton) I copy the whole folder to make it easier to diff between projects to make sure everything is up to date.

Why no installer?  These are subject to change and I don't want to break people

The LICENSE is LGPL v2.1 but I am willing to negotiate on that.
