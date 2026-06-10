# Copyright Epic Games, Inc. All Rights Reserved.

import logging
from contextlib import suppress

from .util import source_module
from ..model.joints_matching import (
    NLSJointsMatchingPass,
    NLSJointsMatchingOptions,
    NLSJointsMatchingJointOptions,
)

logger = logging.getLogger("frt_api.file.joints_matching")


class JointsMatchingPresetReadError(Exception):
    pass


class JointsMatchingPresetWriteError(Exception):
    pass


class JointsMatchingFileHandler:
    """
    File handler for reading and writing joints matching options.

    There are two types of joints matching options: random optimization and
    LMA matching.
    """

    def read_joints_matching_preset(self, file_path: str) -> NLSJointsMatchingOptions:
        """
        Reads NLS joints matching options from file.

        @param file_path: File path. (pattern)
        @return Joints matching options. (NLSJointsMatchingOptions)
        @throws FileApiError: If file is corrupted.
        @see NLSJointsMatchingOptions
        """
        options = NLSJointsMatchingOptions()

        py_options = source_module("jm_py_options", file_path).options
        options.name = py_options["name"]
        self._read_py_expressions(options.expressions, py_options)
        self._read_py_passes(options.passes, py_options)

        return options

    def _read_py_expressions(self, expressions, py_options) -> None:
        exp_list = py_options.get("expressions", {}).get("expression", [])

        if len(exp_list) == 0:
            return

        for i in exp_list:
            expressions.append(i.get("expName"))

    def _read_py_passes(self, passes, py_options) -> None:
        pass_list = py_options.get("passes", {}).get("pass", [])

        if len(pass_list) == 0:
            return

        for i in pass_list:
            nls_pass = NLSJointsMatchingPass(i.get("pattern"))

            nls_pass.mesh_name = i.get("meshName")
            nls_pass.sculpt_mesh_name = i.get("sculptMesh")
            nls_pass.start_type = int(i.get("startType"))
            nls_pass.paint_constraint_split_map = i.get("paintConstraintSplitMap", "")

            with suppress(Exception):
                nls_pass.n_iterations = int(i.get("nIterations"))
                nls_pass.translation_regularization = float(i.get("translationRegularization"))
                nls_pass.rotation_regularization = float(i.get("rotationRegularization"))
                nls_pass.strain_weight = float(i.get("strainWeight"))
                nls_pass.bending_weight = float(i.get("bendingWeight"))

            passes.append(nls_pass)

            self._read_py_NLSJointOptions(nls_pass.joint_options, i.get("jointOptions"))

    def _read_py_NLSJointOptions(self, joint_options, jo) -> None:
        if len(jo.get("jointOption", [])) == 0:
            return

        for i in jo.get("jointOption"):
            joint_option = NLSJointsMatchingJointOptions(i.get("name"))
            joint_option.is_variable[0] = bool(i.get("t"))
            joint_option.is_variable[1] = bool(i.get("r"))
            joint_options.append(joint_option)


def read_joints_matching_preset(file_path: str, rig_definition=None) -> NLSJointsMatchingOptions:
    """
    Reads NLS joints matching options from file.

    @param file_path: File path. (pattern)
    @return Joints matching options. (NLSJointsMatchingOptions)
    @throws FileApiError: If file is corrupted.
    @see NLSJointsMatchingOptions
    """

    joints_matching_file_handler = JointsMatchingFileHandler()
    preset = joints_matching_file_handler.read_joints_matching_preset(file_path)
    if rig_definition:
        validate_matching_preset(preset, rig_definition)
    return preset


def validate_matching_preset(preset, rig_definition) -> None:
    for expression in preset.expressions:
        if not rig_definition.get_expression_by_name(expression):
            raise JointsMatchingPresetReadError(
                f"Preset is missing at least one expression. This expression is {expression}"
            )
    rig_definition.joints.get_all_elements()
    for pass_obj in preset.passes:
        if not rig_definition.get_mesh_by_name(pass_obj.mesh_name):
            raise JointsMatchingPresetReadError(
                f"Preset is missing at least one mesh. This mesh is {pass_obj.mesh_name}"
            )
        if not rig_definition.get_mesh_by_name(pass_obj.sculpt_mesh_name):
            raise JointsMatchingPresetReadError(
                f"Preset is missing at least one mesh. This mesh is {pass_obj.sculpt_mesh_name}"
            )
        if not rig_definition.get_split_map_by_name(pass_obj.paint_constraint_split_map):
            raise JointsMatchingPresetReadError(
                f"Preset is missing at least one split map. This split map is {pass_obj.paint_constraint_split_map}"
            )
        for joint in pass_obj.joint_options:
            if not rig_definition.joints.get_element(joint.name):
                raise JointsMatchingPresetReadError(f"Preset is missing at least one joint. This joint is {joint.name}")
