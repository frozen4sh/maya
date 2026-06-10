# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import TYPE_CHECKING, Optional

# Internal
from mh_pose_editor.model import exceptions

if TYPE_CHECKING:
    from qtpy import QtWidgets

    from mh_pose_editor.api import PoseEditor
    from mh_pose_editor.app import PoseEditorApp
    from mh_pose_editor.model import context


class PoseEditorExtension:
    """
    Base class for extending pose editor with custom utilities that can be dynamically added to the UI
    """

    __category__ = ""

    def __init__(self, api: "PoseEditor", app: Optional["PoseEditorApp"] = None) -> None:
        super().__init__()
        self._app = app
        self._view = None
        self._api = api

    @property
    def api(self) -> "PoseEditor":
        """
        Get the current API

        :return: Reference to the main API interface
        :rtype: epic_pose_editor.main.UERBFAPI
        """

        return self._api

    @property
    def app(self) -> Optional["PoseEditorApp"]:
        """
        Returns the Pose Editor app instance if one exists.
        """
        return self._app

    @property
    def view(self) -> Optional["QtWidgets.QWidget"]:
        """
        Get the current view widget. This should be overridden by custom extensions if you wish to embed a UI for this
        extension into the main PoseEditor UI.

        :return: Reference to the PySide widget associated with this extension
        :rtype: QWidget or None
        """
        return self._view

    def execute(self, context: Optional["context.PoseEditorContext"] = None, **kwargs) -> None:
        """
        Generic entrypoint for executing the extension.

        :param: context: pose editor context containing current solver and all solvers
        :type context: epic_pose_editor.model.context.PoseEditorContext or None
        """
        raise exceptions.PoseEditorFunctionalityNotImplemented(
            f"'execute' function has not been implemented for {self.__class__.__name__}"
        )

    def on_context_changed(self, new_context: "context.PoseEditorContext") -> None:
        """
        Context event called when the current solver is set via the API

        :param new_context: pose editor context containing current solver and all solvers
        :type new_context: epic_pose_editor.model.context.PoseEditorContext or None
        """
        pass
