# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import Any

# External
from qtpy import QtCore

from . import logger


class SettingsManager:
    """
    Settings Manager for reading/writing to Metahuman Character assembler settings ini file
    """

    QSETTINGS: QtCore.QSettings = None

    def __init__(self) -> None:
        # Store the QSettings
        self.__class__.QSETTINGS = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "Epic Games",
            "MetaHumanForMaya/MHCharacterAssembler",
        )
        self.__class__.QSETTINGS.setFallbacksEnabled(False)
        logger.get_logger().info("Successfully initialized SettingsManager")

    @classmethod
    def get_setting(cls, name: str) -> Any:
        """
        Get the setting with the specified name
        :param name :type str: setting name
        :return :type str or None: setting value
        """
        # If the settings haven't been initialized, raise exception
        if cls.QSETTINGS is None:
            logger.get_logger().error("Unable to load settings, " f"{cls} must be initialized first")
        return cls.QSETTINGS.value(name, None)

    @classmethod
    def set_setting(cls, name: str, value: Any) -> None:
        """
        Add/Overwrite the setting with the specified name and value
        :param name :type str: setting name
        :param value :type any: setting value
        """
        cls.QSETTINGS.setValue(name, value)
