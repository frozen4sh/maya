# Copyright Epic Games, Inc. All Rights Reserved.
import os

import qstyle
from qtpy import QtWidgets

icons = qstyle.FontIcons("material")


class FileDialog(QtWidgets.QWidget):
    def __init__(self, label_name):
        super().__init__()

        # Set Name
        self.setObjectName(label_name)

        # Create layout
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        # Create Label
        self.label = QtWidgets.QLabel(label_name)

        # Create Path
        self.line_edit = QtWidgets.QLineEdit()

        # Create Button
        self.button = QtWidgets.QToolButton(self)
        self.button.setText(icons.get("folder"))
        self.button.clicked.connect(self.file_dialog)

        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.button)

    @property
    def data(self):
        return self.line_edit.text()

    @data.setter
    def data(self, path):
        self._set_path(path)

    def _set_path(self, path):
        if path and os.path.exists(path):
            self.line_edit.setText(path)
        else:
            self.line_edit.clear()

    def _clear(self):
        self.line_edit.setText("")

    def file_dialog(self):
        raise NotImplementedError()


class FileOpenMayaProjectDialog(FileDialog):
    def file_dialog(self):
        filepath, filter_ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Workspace File", "", "Maya Project (workspace.mel)"
        )
        if filepath:
            self.data = os.path.dirname(filepath)


class FileOpenDialog(FileDialog):
    def __init__(self, label_name):
        super().__init__(label_name)

    def file_dialog(self):
        filepath, filter_ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "", "Maya Scene (*.mb *.ma)")
        self.data = filepath


class FileSaveDialog(FileDialog):
    def __init__(self, label_name):
        super().__init__(label_name)

    def file_dialog(self):
        filepath, filter_ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", "", "Alembic (*.abc)")
        self.data = filepath

    def _set_path(self, path):
        self.line_edit.setText(path)
