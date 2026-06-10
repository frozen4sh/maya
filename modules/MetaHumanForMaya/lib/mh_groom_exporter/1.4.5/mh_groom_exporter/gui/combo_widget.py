# Copyright Epic Games, Inc. All Rights Reserved.
from qtpy import QtWidgets

from . import LABEL_WIDTH, BUTTON_WIDTH


class ComboWidget(QtWidgets.QWidget):
    def __init__(self, label_name, parent=None):
        super().__init__(parent)

        self.setObjectName(label_name)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        # Create Label
        self.label = QtWidgets.QLabel(label_name)
        self.label.setFixedWidth(LABEL_WIDTH)

        # Create List
        self.combo_box = QtWidgets.QComboBox()

        # Refresh
        dummy_label = QtWidgets.QLabel()
        dummy_label.setFixedWidth(BUTTON_WIDTH)

        layout.addWidget(self.label)
        layout.addWidget(self.combo_box)
        layout.addWidget(dummy_label)

    def _clear(self):
        self.combo_box.clear()


class ModelComboWidget(ComboWidget):
    def __init__(self, label_name, parent=None):
        super().__init__(label_name, parent)

        self.setObjectName(label_name)

        layout = self.layout()

        self.scene_up_axis_label = QtWidgets.QLabel("Scene Up Axis")
        self.scene_up_axis_label.setFixedWidth(BUTTON_WIDTH)

        self.scene_up_axis_combo_box = QtWidgets.QComboBox()
        self.scene_up_axis_combo_box.setFixedWidth(BUTTON_WIDTH)
        self.scene_up_axis_combo_box.addItems(["Y", "Z"])

        layout.addWidget(self.scene_up_axis_label)
        layout.addWidget(self.scene_up_axis_combo_box)

    @property
    def model(self):
        return self.combo_box.currentText()

    @model.setter
    def model(self, value):
        self.combo_box.setCurrentText(value)

    @property
    def up_axis(self):
        return self.scene_up_axis_combo_box.currentText()

    @up_axis.setter
    def up_axis(self, value):
        self.scene_up_axis_combo_box.setCurrentText(value)

    @property
    def data(self):
        return self.combo_box.currentText(), self.scene_up_axis_combo_box.currentText()

    @data.setter
    def data(self, data):
        self.combo_box.setCurrentText(data[0])
        self.scene_up_axis_combo_box.setCurrentText(data[1])
