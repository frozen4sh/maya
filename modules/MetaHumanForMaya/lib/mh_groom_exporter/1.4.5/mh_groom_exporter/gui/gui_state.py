# Copyright Epic Games, Inc. All Rights Reserved.
import json
import inspect

from ..gui.file_dialog import FileOpenDialog, FileSaveDialog, FileOpenMayaProjectDialog
from ..gui.list_widget import ListWidget
from ..gui.combo_widget import ModelComboWidget


class GuiState:
    def __init__(self, ui):
        """
        initializes with main ui element
        """
        self.ui = ui

    def get_ui_data(self):
        """
        returns dictionary of current ui widget values
        """
        data = dict()

        for name, obj in inspect.getmembers(self.ui):
            if not self.is_handled_type(obj):
                continue

            name = obj.objectName()
            value = obj.data
            data[name] = value

        return data

    def set_ui_data(self, data):
        """
        sets widget data
        """
        for name, obj in inspect.getmembers(self.ui):
            if not self.is_handled_type(obj):
                continue

            name = obj.objectName()
            value = data.get(name, None)

            if value:
                if isinstance(obj, (FileSaveDialog, FileOpenDialog, FileOpenMayaProjectDialog)):
                    obj.data = value

        # need to retrieve data from scene before continue to next widgets
        self.ui.refresh_button.click()

        for name, obj in inspect.getmembers(self.ui):
            if not self.is_handled_type(obj):
                continue

            name = obj.objectName()
            value = data.get(name, None)

            if isinstance(obj, ModelComboWidget):
                obj.data = value

            if isinstance(obj, ListWidget):
                obj.data = value

    def save_data(self, file_path):
        """
        Exports data to disk
        """
        with open(file_path, "w") as outfile:
            json.dump(self.get_ui_data(), outfile, sort_keys=0, indent=4, separators=(",", ":"))

    def load_data(self, file_path):
        """
        Imports data from disk
        """
        data = dict()
        with open(file_path) as json_file:
            data = json.load(json_file)
        self.set_ui_data(data)

    def save_geometry(self, settings):
        """
        Saves geometry of self.ui
        """
        settings.setValue("Geometry", self.ui.saveGeometry())

    def load_geometry(self, settings):
        """
        Retrieves geometry for self.ui
        """
        geometry_value = settings.value("Geometry")
        if geometry_value:
            self.ui.restoreGeometry(geometry_value)

    def get_handled_types(self):
        return (ListWidget, FileSaveDialog, FileOpenDialog, FileOpenMayaProjectDialog, ModelComboWidget)

    def is_handled_type(self, widget):
        return any(isinstance(widget, t) for t in self.get_handled_types())
