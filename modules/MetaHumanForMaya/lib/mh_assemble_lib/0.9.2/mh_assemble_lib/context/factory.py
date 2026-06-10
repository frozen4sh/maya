# Copyright Epic Games, Inc. All Rights Reserved.
import logging

from qtpy.QtWidgets import QApplication

from mh_assemble_lib.view.ui import MHViewer
from mh_assemble_lib.control.handler_api import Handler


class Factory:
    """
    Base class for instantiating context dependent classes.

    Context is an environment in which application is being run.
    Environment can be different DCC applications, such as Maya or Houdini,
    or it can run stand alone.
    For each environment this class needs to be subclassed.
    """

    def __init__(self):
        self._app: QApplication = None
        self._viewer: MHViewer = None

    def create_app(self) -> None:
        """Create application GUI environment."""
        self._app = QApplication()

    def create_viewer(self) -> MHViewer:
        """Instantiate UI for given context."""
        logging.debug("Created MHViewer instance.")
        self._viewer = MHViewer()
        return self._viewer

    def create_handler(self) -> Handler:
        """Instantiate handler for given context."""
        logging.debug("Created Handler instance.")
        return Handler()

    def show_viewer(self) -> None:
        """Show UI in given context."""
        logging.debug("Show viewer.")
        self._viewer.show()
        self._app.exec_()
