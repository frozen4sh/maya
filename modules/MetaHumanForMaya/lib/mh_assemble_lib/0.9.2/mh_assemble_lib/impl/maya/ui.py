# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

import logging

from qtpy.QtWidgets import QWidget, QApplication

from mh_assemble_lib.common import MayaException
from mh_assemble_lib.view.ui import MHViewer


class MayaMHViewer(MHViewer):
    """
    Specialization MHViewer class for Autodesk Maya context.

    This object instance is created by MayaFactory class.
    Singleton class.
    """

    _instance = None

    @staticmethod
    def get_instance() -> MayaMHViewer:
        """Return singleton instance of a MayaMHViewer."""
        if MayaMHViewer._instance is None:
            parent = MayaMHViewer._get_parent_window()
            MayaMHViewer._instance = MayaMHViewer(parent)
        return MayaMHViewer._instance

    @staticmethod
    def delete_instance() -> None:
        MayaMHViewer._instance = None

    @staticmethod
    def _get_parent_window() -> QWidget:
        for obj in QApplication.topLevelWidgets():
            if obj.objectName() == "MayaWindow":
                return obj
        raise MayaException("Could not find MayaWindow instance.")

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        logging.debug("MHMayaViewer initialized.")
