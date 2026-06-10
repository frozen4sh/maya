# Copyright Epic Games, Inc. All Rights Reserved.

from qtpy import QtCore, QtWidgets


class TabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QTabBar::tab { min-height: 24px;} QTabBar {color: white;}")

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            index = self.tabBar().tabAt(event.pos())
            if index != -1 and index != 0:
                self.tabCloseRequested.emit(index)
            super().mouseReleaseEvent(event)

    def minimumSizeHint(self):
        """Allow the tab bar to shrink as much as needed."""
        minimumSizeHint = super().minimumSizeHint()
        return QtCore.QSize(0, minimumSizeHint.height())

    def sizeHint(self):
        return self.minimumSizeHint()
