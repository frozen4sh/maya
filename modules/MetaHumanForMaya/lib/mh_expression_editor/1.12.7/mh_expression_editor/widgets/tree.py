# Copyright Epic Games, Inc. All Rights Reserved.

from qtpy import QtCore, QtWidgets

from ..delegate import ItemDelegate


class TreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setIndentation(10)
        self.setHeaderHidden(True)
        self._item_delegate = ItemDelegate(self)
        self.setItemDelegate(self._item_delegate)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
