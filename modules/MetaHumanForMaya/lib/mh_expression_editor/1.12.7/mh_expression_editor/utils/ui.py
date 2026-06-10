# Copyright Epic Games, Inc. All Rights Reserved.

import sys
import contextlib

from qtpy import QtGui, QtCore, QtWidgets

from .general import resource


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        yield app
    else:
        yield app
    app.exec_()


def _get_icon(filename):
    file = resource("icon", filename)
    icon = QtGui.QIcon(file)
    return icon


def set_icon(widget, filename):
    icon = _get_icon(filename)
    widget.setIcon(icon)
    if hasattr(widget, "setIconSize"):
        widget.setIconSize(QtCore.QSize(23, 23))
    elif hasattr(widget, "setFixedSize"):
        widget.setFixedSize(QtCore.QSize(23, 23))


def get_main_qt_window(name=None):
    main_window = None
    widgets = QtWidgets.QApplication.topLevelWidgets()

    # first try to find a qwidget by provided name
    widget = next(iter([w for w in widgets if w.objectName() == name]), None)
    if widget and isinstance(widget, QtWidgets.QMainWindow):
        main_window = widget

    # try to find maya main window in case we are running code there
    if not main_window:
        main_window = next(iter([w for w in widgets if w.objectName() == "MayaWindow"]), None)

    # fallback to just finding first toplevel QMainWindow object
    if not main_window:
        for widget in widgets:
            if isinstance(widget, QtWidgets.QMainWindow):
                main_window = widget
                break

    return main_window


def keyboard_modifiers():
    modifier = QtWidgets.QApplication.keyboardModifiers()
    mod = []
    if modifier == QtCore.Qt.ControlModifier:
        mod.append("CTRL")
    if modifier == QtCore.Qt.ShiftModifier:
        mod.append("SHIFT")
    if modifier == QtCore.Qt.AltModifier:
        mod.append("ALT")

    return mod
