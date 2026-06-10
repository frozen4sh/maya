# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from mh_pose_editor.api import PoseEditor
    from mh_pose_editor.model import rbf_node


class PoseEditorContext:
    def __init__(self, current_solver: Optional["rbf_node.RBFNode"], solvers: List["rbf_node.RBFNode"]) -> None:
        self._current_solver = current_solver
        self._solvers = solvers

    @property
    def current_solver(self) -> Optional["rbf_node.RBFNode"]:
        return self._current_solver

    @property
    def solvers(self) -> List["rbf_node.RBFNode"]:
        return self._solvers


class EditSolverContextManager:
    def __init__(self, api: "PoseEditor", current_solver: "rbf_node.RBFNode") -> None:
        self._api = api
        self._current_solver = current_solver

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._api.edit_solver(edit=False, solver=self._current_solver)
