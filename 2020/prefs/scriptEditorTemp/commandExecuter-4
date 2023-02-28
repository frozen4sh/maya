from maya import OpenMayaUI as omui

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2 import __version__
from shiboken2 import wrapInstance

mayaMainWindowPtr = omui.MQtUtil.mainWindow()
mayaMainWindow= wrapInstance(long(mayaMainWindowPtr), QWidget)

# WORKS: Widget is fine
hello = QLabel("Hello, World", parent=mayaMainWindow)
hello.setObjectName('MyLabel')
hello.setWindowFlags(Qt.Window) # Make this widget a standalone window even though it is parented
hello.show()
hello = None # the "hello" widget is parented, so it will not be destroyed.

# BROKEN: Widget is destroyed
hello = QLabel("Hello, World", parent=None)
hello.setObjectName('MyLabel')
hello.show()
hello = None # the "hello" widget is not parented, so it will be destroyed.
