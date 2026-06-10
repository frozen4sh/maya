# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import Any, Optional

# External
from qtpy import QtCore

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import exceptions


class SettingsManager:
    """
    Settings Manager for reading/writing to PoseEditor settings ini file
    """

    QSETTINGS: QtCore.QSettings = None

    def __init__(self) -> None:
        # Store the QSettings
        self.__class__.QSETTINGS = QtCore.QSettings(
            QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, "Epic Games", "MetaHumanForMaya/MetaHumanPoseEditor"
        )
        self.__class__.QSETTINGS.setFallbacksEnabled(False)
        LOG.debug("Successfully initialized SettingsManager")

    @classmethod
    def get_setting(cls, name: str, fallback: Optional[Any] = None) -> Any:
        """
        Get the setting with the specified name
        :param name :type str: setting name
        :return :type str or None: setting value
        :param fallback: optional fallback value
        """
        # If the settings haven't been initialized, raise exception
        if cls.QSETTINGS is None:
            raise exceptions.PoseEditorSettingsError("Unable to load settings, " f"{cls} must be initialized first")
        return cls.QSETTINGS.value(name, fallback)

    @classmethod
    def set_setting(cls, name: str, value: Any) -> None:
        """
        Add/Overwrite the setting with the specified name and value
        :param name :type str: setting name
        :param value :type any: setting value
        """
        cls.QSETTINGS.setValue(name, value)


SettingsManager()
