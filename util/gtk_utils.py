#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import contextlib
import logging

import gtk


_moduleLogger = logging.getLogger(__name__)


@contextlib.contextmanager
def gtk_lock():
	gtk.gdk.threads_enter()
	try:
		yield
	finally:
		gtk.gdk.threads_leave()


def find_parent_window(widget):
	while True:
		parent = widget.get_parent()
		if isinstance(parent, gtk.Window):
			return parent
		widget = parent


if __name__ == "__main__":
	pass

