# Copyright Epic Games, Inc. All Rights Reserved.

"""
Example Mapping (MetaHuman)
{
    # Regular expression to validate that the solver follows the correct naming convention for mirroring
    "solver_expression": "(?P<prefix>[a-zA-Z0-9]+)?(?P<side>_[lr]{1}_)(?P<suffix>[a-zA-Z0-9]+)",
    # Regular expression to validate that the joint follows the correct naming convention for mirroring
    "transform_expression": "(?P<prefix>[a-zA-Z0-9]+)?(?P<side>_[lr]{1}_)(?P<suffix>[a-zA-Z0-9]+)",
    "left": {
        # Left side syntax for the solver
        "solver_syntax": "_l_",
        # Left side syntax for the joint
        "transform_syntax": "_l_"
    },
    "right": {
        # Right side syntax for the solver
        "solver_syntax": "_r_",
        # Right side syntax for the joint
        "transform_syntax": "_r_"
    }
}
"""

# Built-in
import copy
import json
from typing import Any, Dict, Optional
from pathlib import Path

# Internal
from mh_pose_editor.log import LOG


class MirrorMapping:
    """
    Class for managing mirror settings
    """

    LEFT = "left"
    RIGHT = "right"

    def __init__(
        self, file_path: Optional[Path] = None, source_side: str = "left", mapping_data: Optional[Dict[str, Any]] = None
    ) -> None:
        # Make a list of valid mappings that should exist in the mirror mapping file
        self._valid_mappings = [MirrorMapping.LEFT, MirrorMapping.RIGHT]
        # If no file path is specified, use the MetaHuman config as the fallback
        if file_path is None and mapping_data is None:
            LOG.debug("No mirror mapping specified, using default MetaHuman conventions")
            file_path = Path(__file__).parents[1] / "resources" / "mirror_mappings" / "metahuman.json"

        self._file_path = file_path
        if mapping_data:
            self._mapping_data = mapping_data

        elif file_path and not mapping_data:
            # Load the json mapping data
            with open(file_path) as f:
                self._mapping_data = json.loads(f.read())

        # Set the solver expression from the file
        self._solver_expression: str = self._mapping_data["solver_expression"]
        # Set the transform expression from the file
        self._transform_expression: str = self._mapping_data["transform_expression"]

        # Set the source side and create defaults
        self._source_side = source_side
        self._source_mapping_data: Dict[str, str] = {}
        self._source_solver_syntax = ""
        self._source_transform_syntax = ""

        self._target_mapping_data: Dict[str, str] = {}
        self._target_solver_syntax = ""
        self._target_transform_syntax = ""
        # Set the source side property to trigger the default values to be updated
        self.source_side = source_side

    @property
    def file_path(self) -> Optional[Path]:
        return self._file_path

    @property
    def mapping_data(self) -> Dict[str, Any]:
        return copy.deepcopy(self._mapping_data)

    @property
    def solver_expression(self) -> str:
        return self._solver_expression

    @property
    def transform_expression(self) -> str:
        return self._transform_expression

    @property
    def source_side(self) -> str:
        return self._source_side

    @source_side.setter
    def source_side(self, side: str) -> None:
        """
        Sets the source side and updates the source/target values accordingly
        :param side: MirrorMapping.LEFT or MirrorMapping.RIGHT
        """
        if side not in self._valid_mappings:
            raise ValueError("Invalid side specified, options are: {}".format(", ".join(self._valid_mappings)))
        self._source_side = side
        self._source_mapping_data = self._mapping_data[self._source_side]
        self._source_solver_syntax = self._source_mapping_data["solver_syntax"]
        self._source_transform_syntax = self._source_mapping_data["transform_syntax"]

        self._target_mapping_data = self._mapping_data[
            MirrorMapping.RIGHT if self._source_side == MirrorMapping.LEFT else MirrorMapping.LEFT
        ]
        self._target_solver_syntax = self._target_mapping_data["solver_syntax"]
        self._target_transform_syntax = self._target_mapping_data["transform_syntax"]

    @property
    def source_solver_syntax(self) -> str:
        return self._source_solver_syntax

    @property
    def source_transform_syntax(self) -> str:
        return self._source_transform_syntax

    @property
    def target_solver_syntax(self) -> str:
        return self._target_solver_syntax

    @property
    def target_transform_syntax(self) -> str:
        return self._target_transform_syntax

    def swap_sides(self) -> None:
        """
        Swap the source side to the opposite of the current side.
        """
        new_target = MirrorMapping.LEFT if self.source_side == MirrorMapping.RIGHT else MirrorMapping.RIGHT
        self.source_side = new_target
