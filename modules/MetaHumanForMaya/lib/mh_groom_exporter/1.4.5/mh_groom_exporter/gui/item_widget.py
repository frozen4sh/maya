# Copyright Epic Games, Inc. All Rights Reserved.
from qtpy import QtGui, QtCore, QtWidgets


class TreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent=None, group_names=None):
        super().__init__(parent)

        # ComboBox
        self.QComboBox = QtWidgets.QComboBox()
        self.QComboBox.setEditable(True)
        self.QComboBox.setInsertPolicy(QtWidgets.QComboBox.InsertAtCurrent)

        lineEditPalette = QtGui.QPalette()
        lineEditPalette.setColor(QtGui.QPalette.Base, QtGui.QColor(53, 53, 53))
        self.QComboBox.setPalette(lineEditPalette)

        # ComboBox Items
        self.group_names = group_names
        if not group_names:
            self.group_names = [str(index) for index in range(15)]
        for value in self.group_names:
            self.QComboBox.addItem(value)

        # CheckBox for Guide Export
        self.QGuidesCB = QtWidgets.QWidget()
        self.QCheckBox = QtWidgets.QCheckBox()
        self.QCheckBox.setChecked(True)
        self.QHBoxLayout = QtWidgets.QHBoxLayout(self.QGuidesCB)
        self.QHBoxLayout.addWidget(self.QCheckBox)
        self.QHBoxLayout.setAlignment(QtCore.Qt.AlignCenter)
        self.QHBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.QGuidesCB.setLayout(self.QHBoxLayout)

        # Set Widgets
        self.treeWidget().setItemWidget(self, 1, self.QComboBox)
        self.treeWidget().setItemWidget(self, 2, self.QGuidesCB)

        self.QComboBox.currentIndexChanged.connect(self._itemChanged)
        self.QComboBox.lineEdit().editingFinished.connect(self._editingFinished)

        self.QCheckBox.stateChanged.connect(self._itemChanged)

    @property
    def data(self):
        return self.QComboBox.currentIndex(), self.QComboBox.currentText(), self.QCheckBox.isChecked()

    @data.setter
    def data(self, data):
        self.QComboBox.setCurrentIndex(data[0])
        self.QComboBox.setCurrentText(data[1])
        self.QComboBox.setItemText(data[0], data[1])
        self.QCheckBox.setChecked(data[2])

    @data.setter
    def checked(self, value):
        self.QCheckBox.setChecked(value)

    def _itemChanged(self):
        if self.treeWidget():
            self.treeWidget().itemChanged.emit(self, 1)

    def _editingFinished(self):
        if self.treeWidget():
            self.treeWidget().itemExpanded.emit(self)
