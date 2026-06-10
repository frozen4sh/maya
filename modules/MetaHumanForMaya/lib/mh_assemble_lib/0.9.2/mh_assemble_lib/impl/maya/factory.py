# Copyright Epic Games, Inc. All Rights Reserved.
import logging

from qtpy.QtCore import Qt

from mh_assemble_lib.view.ui import MHViewer
from mh_assemble_lib.impl.maya.ui import MayaMHViewer
from mh_assemble_lib.context.factory import Factory
from mh_assemble_lib.impl.maya.handler import MayaHandler
from mh_assemble_lib.control.handler_api import Handler


class MayaFactory(Factory):
    """
    Specialization Factory class for Autodesk Maya context.
    """

    def __init__(self):
        super().__init__()

    def create_app(self) -> None:
        pass

    def create_viewer(self) -> MHViewer:
        """Instantiate UI for Maya context."""
        logging.debug("Created MayaMHViewer instance.")
        self._viewer = MayaMHViewer.get_instance()
        self._viewer.destroyed.connect(MayaMHViewer.delete_instance)
        return self._viewer

    def create_handler(self) -> Handler:
        """Instantiate handler for Maya context."""
        logging.debug("Created MayaHandler instance.")
        return MayaHandler()

    def show_viewer(self) -> None:
        """Show UI in Maya context."""
        logging.debug("Show viewer.")
        # if the window is minimized, raise it
        if self._viewer.windowState() & Qt.WindowMinimized:
            self._viewer.setWindowState(Qt.WindowActive)

        # show and make active
        self._viewer.show()
        self._viewer.activateWindow()
