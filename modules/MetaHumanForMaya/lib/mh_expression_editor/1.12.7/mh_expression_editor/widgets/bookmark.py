# Copyright Epic Games, Inc. All Rights Reserved.

import os
import shutil
from functools import partial

from qtpy import QtCore, QtWidgets

from .. import lib
from ..utils import ui, general
from .settings import Settings
from ..resource import Resources

logger = general.get_logger()


class BookmarkMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._parent = parent

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.custom_context_menu)

        self.user_bookmark_path = ""
        self.preset_bookmark_path = ""

    def populate_bookmarks(self):
        self.user_bookmark_path = os.path.join(Settings().get_setting("bookmarks_directory"), Resources().db_name)
        self._create_dir(self.user_bookmark_path)
        self.preset_bookmark_path = Resources().graph_presets_folder_path

        self.populate_dropdown()

    def populate_menu_from_dir(self, directory, sub_menu=None):
        if not sub_menu:
            menu = self
        else:
            menu = QtWidgets.QMenu(sub_menu, parent=self)
            menu.setIcon(ui._get_icon("folder_mid.svg"))
            self.addMenu(menu)

        for _, _, filenames in os.walk(directory):
            for filename in filenames:
                name, _ = os.path.splitext(filename)
                action = menu.addAction(name)
                action.triggered.connect(
                    partial(
                        self._parent.add_view,
                        lib.deserialize_scene(path=os.path.join(directory, filename)),
                        name=name,
                        preset=sub_menu,
                    )
                )
            break

    def populate_dropdown(self):
        self.clear()
        add = self.addAction("Add")
        self.addSeparator()
        self.populate_menu_from_dir(self.preset_bookmark_path, "Presets")
        self.populate_menu_from_dir(self.user_bookmark_path)
        self.addSeparator()
        import_bookmarks = self.addAction("Import")
        export_bookmarks = self.addAction("Export All")

        add.triggered.connect(self._add_bookmark)
        import_bookmarks.triggered.connect(self._import_bookmarks)
        export_bookmarks.triggered.connect(self._export_bookmarks)
        ui.set_icon(add, "plus_mid.svg")
        ui.set_icon(import_bookmarks, "import_mid.svg")
        ui.set_icon(export_bookmarks, "export_mid.svg")

    def custom_context_menu(self, pos):
        if self.sender().activeAction() is None:
            return
        under_cursor_action = self.sender().activeAction().text()
        menu = QtWidgets.QMenu(parent=self)

        remove = menu.addAction("Remove")
        rename = menu.addAction("Rename")
        menu.addSeparator()
        export_bookmark = menu.addAction("Export")

        ui.set_icon(remove, "minus_mid.svg")
        ui.set_icon(rename, "edit_mid.svg")
        ui.set_icon(export_bookmark, "export_mid.svg")

        # triggers
        remove.triggered.connect(lambda: self._remove_bookmark(under_cursor_action))
        rename.triggered.connect(lambda: self._rename_bookmark(under_cursor_action))
        export_bookmark.triggered.connect(lambda: self._export_bookmark(under_cursor_action))

        menu.exec_(self.mapToGlobal(pos))

    # Actions
    # -------------------------------------------------------------------------

    def _add_bookmark(self):
        graph = self._parent.ui["widget"]["graph"].currentWidget()
        text = self._open_text_input_dialog(placeholder="Bookmark name")
        if graph.model is None:
            logger.info("Cannot create a bookmark from the main tab!")
            return
        graph.update_model()
        if text is not None:
            if text:
                lib.serialize_scene(
                    self._parent.ui["widget"]["graph"].currentWidget().model,
                    name=text,
                    path=os.path.join(self.user_bookmark_path),
                )
                self.populate_dropdown()
            else:
                logger.info("Bookmark name cannot be empty.")

    def _remove_bookmark(self, bookmark_name):
        try:
            os.remove(os.path.join(self.user_bookmark_path, bookmark_name + ".json"))
            logger.info(f"File '{bookmark_name}' removed successfully.")
        except FileNotFoundError:
            logger.info(f"File '{bookmark_name}' not found.")
        self.populate_dropdown()

    def _rename_bookmark(self, bookmark_name):
        text = self._open_text_input_dialog(placeholder=bookmark_name)
        if text is not None:
            if text:
                try:
                    old_name = os.path.join(self.user_bookmark_path, bookmark_name + ".json")
                    new_name = os.path.join(self.user_bookmark_path, text + ".json")
                    os.rename(old_name, new_name)
                    logger.info(f"File '{old_name}' renamed to '{new_name}' successfully.")
                except Exception as e:
                    logger.info(f"Error: {e}")
            else:
                logger.info("Bookmark name cannot be empty.")
        self.populate_dropdown()

    def _export_bookmark(self, bookmark_name):
        dir_dialog = QtWidgets.QFileDialog(self._parent)
        dir_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        dir_dialog.setWindowTitle("Export Bookmark")
        if dir_dialog.exec_():
            selected_dir = dir_dialog.selectedFiles()[0]
            shutil.copy2(os.path.join(self.user_bookmark_path, bookmark_name + ".json"), selected_dir)
            logger.info(f"Bookmark '{bookmark_name}' exported to: {selected_dir}")

    def _open_text_input_dialog(self, placeholder=""):
        dialog = QtWidgets.QInputDialog(self._parent)
        dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
        dialog.setWindowTitle("Bookmark Name")
        dialog.setLabelText("Name:")
        line_edit = dialog.findChild(QtWidgets.QLineEdit)
        line_edit.setText(placeholder)
        if dialog.exec_():
            return dialog.textValue()
        return None

    def _export_bookmarks(self):
        dir_dialog = QtWidgets.QFileDialog(self._parent)
        dir_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        dir_dialog.setWindowTitle("Export Bookmarks")
        if dir_dialog.exec_():
            selected_dir = dir_dialog.selectedFiles()[0]
            for _, _, filenames in os.walk(self.user_bookmark_path):
                for filename in filenames:
                    if filename.endswith(".json"):
                        shutil.copy2(os.path.join(self.user_bookmark_path, filename), selected_dir)
                break
            logger.info(f"Bookmarks exported to: {selected_dir}")

    def _import_bookmarks(self):
        file_dialog = QtWidgets.QFileDialog(self._parent)
        file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        file_dialog.setWindowTitle("Import Bookmarks")
        file_dialog.setNameFilter("JSON Files (*.json)")
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            for file_path in selected_files:
                shutil.copy2(file_path, self.user_bookmark_path)
            self.populate_dropdown()
            logger.info("Bookmarks imported successfully.")

    # Utils
    # -------------------------------------------------------------------------
    def _create_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Directory '{path}' created successfully.")
