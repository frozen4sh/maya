# Copyright Epic Games, Inc. All Rights Reserved.
"""
Mudule containing UI widgets used in app.
"""
import logging
from typing import List, Callable
from pathlib import Path

from mh_assemble_lib.view.qt import QtCore, QtWidgets
from mh_assemble_lib.control.form import MeshForm, MeshLayoutForm


class QLine(QtWidgets.QFrame):
    """Line widget."""

    def __init__(self, line: QtWidgets.QFrame.Shape) -> None:
        super().__init__()
        self.setFrameShape(line)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)


class QHLine(QLine):
    """Horizontal line widget."""

    def __init__(self) -> None:
        super().__init__(QtWidgets.QFrame.HLine)


class FileChooserForm:
    def __init__(self, label: str, hint: str, caption: str, filter_exp: str):
        self.label: str = label
        self.hint: str = hint
        self.caption: str = caption
        self.filter_exp: str = filter_exp


class QFileChooser(QtWidgets.QWidget):
    """
    A custom widget used for selecting a file path using a FileDialog and an input field.
    """

    BTN_LABEL = "..."

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        form: FileChooserForm,
        on_changed: Callable[[int], None] = None,
    ) -> None:
        super().__init__(parent=parent)
        self._form = form

        self.ly = QtWidgets.QHBoxLayout()
        self.ly.setContentsMargins(0, 0, 0, 0)
        self.lbl = QtWidgets.QLabel(form.label)
        self.lbl.setMinimumHeight(32)

        self.txt_path = QtWidgets.QLineEdit()
        self.txt_path.setAlignment(QtCore.Qt.AlignLeft)
        self.txt_path.textChanged.connect(on_changed)
        self.txt_path.setToolTip(form.hint)

        self.btn = QtWidgets.QPushButton(QFileChooser.BTN_LABEL)
        self.btn.setToolTip(form.hint)
        self.btn.clicked.connect(
            self.open_dialog,
        )

        self.ly.addWidget(self.lbl)
        self.ly.addWidget(self.txt_path)
        self.ly.addWidget(self.btn)
        self.setLayout(self.ly)

    def open_dialog(self) -> None:
        path: str = None
        if self._form.filter_exp is None:
            path = QtWidgets.QFileDialog.getExistingDirectory(
                self, self._form.caption, "", QtWidgets.QFileDialog.ShowDirsOnly
            )
        else:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, self._form.caption, "", self._form.filter_exp)
        if path:
            self.txt_path.setText(path)

    def get_path(self) -> str:
        path = str(self.txt_path.text())
        logging.debug(f"File selected: {path}.")
        if path and Path(path.strip()).exists():
            return path
        return None


class QMeshLayut(QtWidgets.QWidget):
    """
    A custom widget that lists out meshes with checkboxes next to them.
    Selected meshes are processed.
    Meshes are grouped by LODs.
    """

    LOD_LABEL = "LOD "

    def __init__(self, parent: QtWidgets.QWidget, on_changed: Callable[[int], None]) -> None:
        super().__init__(parent=parent)
        self._form = MeshLayoutForm()

        # layout
        self.ly_main = QtWidgets.QVBoxLayout()
        self.ly_main.setContentsMargins(0, 0, 0, 8)

        # label
        self.lbl = QtWidgets.QLabel("Meshes:")
        self.ly_main.addWidget(self.lbl)

        # tree widget
        self.ly = QtWidgets.QGridLayout()
        self.ly.setContentsMargins(0, 0, 0, 8)
        self.ly_main.addLayout(self.ly)
        self.tree_mesh = QtWidgets.QTreeWidget()
        self.tree_mesh.setHeaderHidden(True)
        self.tree_mesh.itemChanged.connect(on_changed)
        self.tree_mesh.setStyleSheet("background-color: #505050")
        self.tree_mesh.setToolTip("Select mesh or meshes to add to rig.")
        self.ly.addWidget(self.tree_mesh, 0, 0, 4, 1)

        # buttons
        self.btn_select_all = QtWidgets.QPushButton("Select all meshes")
        self.btn_select_all.setEnabled(False)
        self.btn_select_all.clicked.connect(self.select_all)
        self.ly_main.addWidget(self.btn_select_all)
        self.btn_deselect_all = QtWidgets.QPushButton("Deselect all meshes")
        self.btn_deselect_all.setEnabled(False)
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        self.ly_main.addWidget(self.btn_deselect_all)

        self.setLayout(self.ly_main)

    # getters
    def get_mesh_count(self) -> int:
        return self._form.get_mesh_count()

    def get_selected_meshes(self) -> List[MeshForm]:
        mesh_forms = []
        iterator = QtWidgets.QTreeWidgetItemIterator(self.tree_mesh, QtWidgets.QTreeWidgetItemIterator.Checked)
        while iterator.value():
            item = iterator.value()
            mesh_name = item.text(0)
            mesh_form = self._form.get_mesh_by_name(mesh_name)
            if mesh_form is not None:
                mesh_forms.append(mesh_form)
            iterator += 1
        return mesh_forms

    def is_all_meshes_selected(self) -> bool:
        selected_count = len(self.get_selected_meshes())
        all_count = self._form.get_mesh_count()
        return selected_count == all_count

    # setters
    def set_mesh_layout(self, form: MeshLayoutForm) -> None:
        logging.debug("Mesh layout initialized.")
        self._form = form
        self.tree_mesh.clear()
        for lod in form.lods:
            parent = QtWidgets.QTreeWidgetItem(self.tree_mesh)
            parent.setText(0, f"{QMeshLayut.LOD_LABEL}{lod.id}")
            parent.setFlags(parent.flags() | QtCore.Qt.ItemIsAutoTristate | QtCore.Qt.ItemIsUserCheckable)
            for mesh in lod.meshes:
                child = QtWidgets.QTreeWidgetItem(parent)
                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                child.setText(0, f"{mesh.name}")
                child.setCheckState(0, QtCore.Qt.Unchecked)
            parent.setExpanded(True)

    # slots
    def select_all(self) -> None:
        self._iterate_over_items(QtCore.Qt.Checked)

    def deselect_all(self) -> None:
        self._iterate_over_items(QtCore.Qt.Unchecked)

    def _iterate_over_items(self, state: QtCore.Qt.CheckState) -> None:
        item = self.tree_mesh.invisibleRootItem()
        for index in range(item.childCount()):
            child = item.child(index)
            child.setCheckState(0, state)
