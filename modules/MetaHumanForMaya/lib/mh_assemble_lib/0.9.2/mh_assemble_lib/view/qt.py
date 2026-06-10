QT_LIB: str = ""

try:
    from qtpy import QtCore, QtWidgets

    QT_LIB = "qtpy"
except ImportError:
    try:
        from PySide6 import QtCore, QtWidgets

        QT_LIB = "PySide6"
    except ImportError:
        from PySide2 import QtCore, QtWidgets

        QT_LIB = "PySide2"

qt_core = QtCore
qt_widgets = QtWidgets
