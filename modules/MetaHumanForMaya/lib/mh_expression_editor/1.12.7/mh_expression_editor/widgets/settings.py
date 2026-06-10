# Copyright Epic Games, Inc. All Rights Reserved.

import os
import sys
from typing import Any

from qtpy import QtCore, QtWidgets


def _data_dir():
    if sys.platform.startswith("win"):
        return os.environ.get("APPDATA")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support")
    else:
        return os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))


def _documents_dir():
    docs = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
    if not docs:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
    return docs


settings_dict = {
    "auto_load_dna": ("general.save_load", "auto_load_dna", True),
    "bookmarks_directory": (
        "expression_poses.graph",
        "bookmarks_directory",
        os.path.join(_data_dir(), "Epic Games", "MetaHumanForMaya", "MetaHumanExpressionEditor", "bookmarks"),
    ),
    "advanced_propagation": ("expression_poses.graph.advanced", "advanced_propagation", False),
    "highlight_last_selected": (
        "expression_poses.graph",
        "highlight_last_selected",
        True,
    ),
    "preview_selected_node": (
        "expression_poses.graph",
        "preview_selected_node",
        True,
    ),
    "update_analysis_on_control_selection": (
        "expression_poses.graph",
        "update_analysis_on_control_selection",
        False,
    ),
    "general_up_axis": ("general.up_axis", "general_up_axis", "dna"),
    "export_up_axis": ("export.up_axis", "export_up_axis", "z"),
}


class Settings:
    QSETTINGS: QtCore.QSettings = None

    def __init__(self):
        self.__class__.QSETTINGS = QtCore.QSettings(
            QtCore.QSettings.Format.IniFormat,
            QtCore.QSettings.Scope.UserScope,
            "Epic Games",
            "MetaHumanForMaya/MetaHumanExpressionEditor",
        )
        self.__class__.QSETTINGS.setFallbacksEnabled(False)

    @classmethod
    def get_setting(cls, name: str) -> Any:
        if name in settings_dict:
            section, key, default = settings_dict[name]
            return cls.QSETTINGS.value(name, default, type=type(default))

    @classmethod
    def set_setting(cls, name: str, value: Any) -> None:
        for section, key, default in settings_dict.values():
            if key == name:
                cls.QSETTINGS.setValue(name, value)

    @classmethod
    def create_config(cls):
        for key, value in settings_dict.items():
            section, key, default = value
            cls.QSETTINGS.setValue(key, default)

    @classmethod
    def write(cls):
        cls.QSETTINGS.sync()


class SettingsPanel(QtWidgets.QWidget):
    def __init__(self):
        self.config = Settings()
        if not os.path.exists(self.config.QSETTINGS.fileName()):
            if os.path.exists(os.path.join(_documents_dir(), "maya", "mhe", "settings.ini")):
                import configparser

                old_path = os.path.join(_documents_dir(), "maya", "mhe", "settings.ini")
                config = configparser.ConfigParser()
                config.read(old_path)
                for key, value in settings_dict.items():
                    section, name, default = value
                    try:
                        old_value = config.get(section, key)
                    except (configparser.NoSectionError, configparser.NoOptionError):
                        self.config.QSETTINGS.setValue(name, default)
                        continue
                    if isinstance(default, bool):
                        old_value = bool(old_value)
                    if isinstance(default, str):
                        old_value = os.path.join(old_value)
                    self.config.QSETTINGS.setValue(name, old_value if old_value else default)
                os.remove(old_path)
            else:
                self.config.create_config()
