# Copyright Epic Games, Inc. All Rights Reserved.

import os
import re
import json
import uuid
import tempfile
import contextlib
from itertools import combinations
from collections import deque

import dna
import rdf
import dnacalib2 as dnacalib
from maya import cmds
from frt_api import FRTApiError, ProgressEnd, ProgressStart, ProgressUpdate
from frt_api.rig import (
    LODGeneration,
    RigDataHandler,
    RigCalculationHandler,
    MLJointsMatchingHandler,
    match_joints,
)
from frt_api.file import read_joints_matching_preset
from frt_api.maya import MayaSceneError
from frt_api.file.dna_file import DNAFileHandler
from frt_api.model.rig_definition.view import TargetExpView, ExpressionInView

from .model import NodeModel, SceneModel
from .utils import dcc
from .resource import Resources

TEMP_DNA_FILE_PATH = rf"{tempfile.gettempdir()}/{str(uuid.uuid4())}.dna"


class RigCompatibilityError(Exception):
    pass


class MissingBlendShapes(RigCompatibilityError):
    def __init__(self):
        super().__init__("Blends shapes missing in the MetaHuman DNA.")


class WrongLODCount(RigCompatibilityError):
    def __init__(self):
        super().__init__("LOD count not correct in the MetaHuman DNA.")


def save_dna(rig, dna_file_path, inverse_rotation):
    stream = dna.FileStream(
        dna_file_path,
        dna.FileStream.AccessMode_Write,
        dna.FileStream.OpenMode_Binary,
    )

    output_reader = dnacalib.DNACalibDNAReader(rig.dna_reader)
    rig.rig.exportDNA(output_reader)

    if inverse_rotation != [0.0, 0.0, 0.0]:
        rotate_command = dnacalib.RotateCommand([-v for v in inverse_rotation], [0.0, 0.0, 0.0])
        rotate_command.run(output_reader)

    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(output_reader)
    writer.write()


def get_dnacalib2_version_info():
    return dnacalib.VersionInfo.getVersionString()


def get_db_name(dna_file_path):
    try:
        dna_reader = DNAFileHandler.get_reader(dna_file_path)
        return dna_reader.getDBName()
    except IndexError:
        return None
    except ValueError:
        return None
    except FRTApiError:
        return None


def validate_blend_shapes(rdf_reader, dna_reader):
    rdf_blend_shapes = {}
    dna_blend_shapes = {}

    for mesh_index in range(rdf_reader.getMeshCount()):
        rdf_blend_shapes[rdf_reader.getMeshName(mesh_index)] = []

    for mesh_index in range(dna_reader.getMeshCount()):
        dna_blend_shapes[dna_reader.getMeshName(mesh_index)] = []

    for expression_index in range(rdf_reader.getExpressionCount()):
        if rdf_reader.getExpressionExportedToRig(expression_index):
            mesh_indices = rdf_reader.getExpressionMeshIndices(expression_index)
            mesh_deformation_types = rdf_reader.getExpressionMeshDeformationTypes(expression_index)
            for mesh_index, deformation_type in zip(mesh_indices, mesh_deformation_types):
                if deformation_type in [rdf.DeformationType_BlendShapesOnly, rdf.DeformationType_JointsAndBlendShapes]:
                    rdf_blend_shapes[rdf_reader.getMeshName(mesh_index)].append(
                        rdf_reader.getExpressionName(expression_index)
                    )

    for mesh_blend_shape_mapping_index in range(dna_reader.getMeshBlendShapeChannelMappingCount()):
        mapping = dna_reader.getMeshBlendShapeChannelMapping(mesh_blend_shape_mapping_index)
        dna_blend_shapes[dna_reader.getMeshName(mapping.meshIndex)].append(
            dna_reader.getBlendShapeChannelName(mapping.blendShapeChannelIndex)
        )

    rdf_blend_shapes = {key: value for key, value in rdf_blend_shapes.items() if value}

    for key in rdf_blend_shapes:
        if not sorted(dna_blend_shapes[key]) == sorted(rdf_blend_shapes[key]):
            raise MissingBlendShapes


def validate_lods(rdf_reader, dna_reader):
    if not rdf_reader.getLODCount() == dna_reader.getLODCount():
        raise WrongLODCount


def validate_rdf_compatibility(rdf_file_path, dna_file_path):
    stream = rdf.FileStream(
        rdf_file_path,
        rdf.FileStream.AccessMode_Read,
        rdf.FileStream.OpenMode_Binary,
    )
    rdf_reader = rdf.RigDefinitionBinaryStreamReader(stream)
    rdf_reader.read()

    dna_reader = DNAFileHandler.get_reader(dna_file_path)

    validators = [validate_blend_shapes, validate_lods]
    for validator in validators:
        validator(rdf_reader, dna_reader)


def calculate_rotation_vector(source_up_axis, destination_up_axis):
    if source_up_axis == destination_up_axis:
        return [0.0, 0.0, 0.0]
    if source_up_axis == "y":
        if destination_up_axis == "z":
            return [90.0, 0.0, 0.0]
    elif source_up_axis == "z":
        if destination_up_axis == "y":
            return [-90.0, 0.0, 0.0]
    raise FRTApiError(f"Unsupported up axis combination, from {source_up_axis} to {destination_up_axis}")


def orient_dna(dna_file_path, selected_up_axis):
    dna_reader = DNAFileHandler.get_reader(dna_file_path)
    coordinate_system = dna_reader.getCoordinateSystem()
    if coordinate_system.yAxis == 2:
        dna_up_axis = "y"
    elif coordinate_system.zAxis == 2:
        dna_up_axis = "z"
    else:
        dna_up_axis = "x"
    if selected_up_axis == "dna":
        up_axis = dna_up_axis
    else:
        up_axis = selected_up_axis
    if up_axis not in ["y", "z"]:
        raise FRTApiError("Wrong coordinate system specified in the provided MetaHuman DNA, Y-up and Z-up supported.")

    rotation_vector = calculate_rotation_vector(dna_up_axis, up_axis)

    if rotation_vector == [0.0, 0.0, 0.0]:
        return dna_file_path, up_axis, rotation_vector

    dna_reader = DNAFileHandler.get_reader(dna_file_path)
    dna_calib_reader = dnacalib.DNACalibDNAReader(dna_reader)
    rotate_command = dnacalib.RotateCommand(rotation_vector, [0.0, 0.0, 0.0])
    rotate_command.run(dna_calib_reader)

    temp_dna_file_path = TEMP_DNA_FILE_PATH
    stream = dna.FileStream(
        temp_dna_file_path,
        dna.FileStream.AccessMode_Write,
        dna.FileStream.OpenMode_Binary,
    )
    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(dna_calib_reader)
    writer.write()
    return temp_dna_file_path, up_axis, rotation_vector


def get_body_type_metadata(rig):
    return rig.dna_reader.getMetaDataValue("BodyType")


def initialize_ml_joints_matching_handler(rig, rotation):
    return MLJointsMatchingHandler(rig, [-v for v in rotation])


def add_neck_rotations(rig, main_expressions, neck_joints_animation):
    head_turns_data = {}
    for main_expression in main_expressions:
        head_turns_data[main_expression] = neck_joints_animation[main_expression]
    RigCalculationHandler.add_head_turns(rig, head_turns_data)


def add_phase_expression_view_data(rig, view_data):
    for expression_name, config in view_data.items():
        exp = rig.rig_definition.get_expression_by_name(expression_name)
        exp.neutral_range = config["neutral_range"]
        exp.phases = config["phase_numbers"]
        view_data = config["view"]
        if view_data:
            view = TargetExpView(exp)
            exp.view = view
            view_expression = rig.rig_definition.get_expression_by_name(view_data["expression_name"])
            view.expressions_in_view = [
                ExpressionInView(
                    expression=view_expression, frame=view_data["frame"], multiplier=view_data["multiplier"]
                )
            ]


def get_head_turn_matching_data(rig, expression_name, neck_joints, group_name):
    removed_connections = dcc.remove_neck_rotations(rig, neck_joints, group_name)

    target_shapes = {}
    rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
    for mesh_name in rig.rig_definition.lod_meshes[0].meshes:
        for mie in rig_expression.meshes_in_expression:
            if mie.mesh.name == mesh_name:
                if mie.is_blends():
                    target_shapes[mesh_name] = dcc.get_mesh_vertex_positions(f"{group_name}|{mesh_name}")
                else:
                    target_shapes[mesh_name] = rig.get_neutral_mesh_vertex_positions(mesh_name)

    expression_joints = get_expression_joints_from_scene(rig, group_name)
    dcc.reconnect_neck_joints(rig, removed_connections, neck_joints, group_name)

    return target_shapes, expression_joints


def get_sculpt_mesh_names(rig, expressions=None):
    expressions = expressions or rig.rig_definition.expressions
    sculpt_mesh_names = set()
    for exp in expressions:
        for mie in exp.meshes_in_expression:
            if mie.type in [2, 3]:
                sculpt_mesh_names.add(mie.mesh.name)
    return sculpt_mesh_names


def get_modeling_expressions(rig, skip_expressions):
    modeling_expressions = {}
    for expression in rig.rig_definition.expressions:
        if expression.type == 1 and expression.name not in skip_expressions:
            for mie in expression.meshes_in_expression:
                if mie.is_blends():
                    modeling_expressions[expression.name] = NodeModel(expression.name, 0)
                    break
            if expression.name not in modeling_expressions:
                if expression.assemble_to_rig:
                    modeling_expressions[expression.name] = NodeModel(expression.name, 0)
                else:
                    if expression.generates:
                        if (
                            expression.generates[0].function.function_type == 1
                            and expression.generates[0].assemble_to_rig == 1
                        ):
                            modeling_expressions[expression.name] = NodeModel(expression.name, 0)
    for expression in rig.rig_definition.expressions:
        if expression.type == 4 and expression.name not in skip_expressions:
            psd_definition = rig.rig_definition.get_psd_def_for_expression(expression.name)
            exp = NodeModel(expression.name, psd_definition.layer)
            if psd_definition.layer == 1:
                for exp_multi in psd_definition.complex_pose_build:
                    if exp_multi.expression.name in modeling_expressions:
                        exp.inputs.append(exp_multi.expression.name)
            else:
                expressions_added = set()
                for sub_set in reversed(psd_definition.sub_sets):
                    superset_added = False
                    super_sets = {temp.target_pose.name for temp in sub_set.super_sets}
                    for super_set in super_sets:
                        if super_set in exp.inputs:
                            superset_added = True
                            break
                    if not superset_added:
                        for exp_multi in sub_set.complex_pose_build:
                            expressions_added.add(exp_multi.expression.name)
                        exp.inputs.append(sub_set.target_pose.name)
                for exp_multi in psd_definition.complex_pose_build:
                    expression_name = exp_multi.expression.name
                    if (
                        expression_name not in expressions_added
                        and expression_name in modeling_expressions
                        and expression_name not in exp.inputs
                    ):
                        exp.inputs.append(exp_multi.expression.name)

            modeling_expressions[expression.name] = exp

    return sort_nodes_by_layer(modeling_expressions)


def get_inverse_psd_combinations(rig):
    psd_combinations = {}
    for row_index, column_index in zip(rig.dna_reader.getPSDRowIndices(), rig.dna_reader.getPSDColumnIndices()):
        if row_index not in psd_combinations:
            psd_combinations[row_index] = []
        psd_combinations[row_index].append(column_index)

    inverse_psd_combinations = {}
    for psd_index, raw_controls in psd_combinations.items():
        inverse_psd_combinations[tuple(sorted(raw_controls))] = psd_index

    return inverse_psd_combinations


def get_raw_control_names(rig, control_renaming):
    control_renaming = control_renaming or {}
    raw_control_names = []
    for i in range(rig.dna_reader.getRawControlCount()):
        if rig.dna_reader.getRawControlName(i) in control_renaming:
            raw_control_names.append(control_renaming[rig.dna_reader.getRawControlName(i)])
        else:
            raw_control_names.append(rig.dna_reader.getRawControlName(i))
    return raw_control_names


def get_control_type(rig, control_name):
    for control_index in range(rig.rdf_reader.getControlCount()):
        if rig.rdf_reader.getControlName(control_index) == control_name:
            return rig.rdf_reader.getControlType(control_index)
    return rdf.ControlType_Unspecified


def get_driver_joints(rig, pose_name):
    driver_joints = []
    for rbf_solver_index in range(rig.rdf_reader.getRBFSolverCount()):
        for pose_index in rig.rdf_reader.getRBFSolverOutputPoseIndices(rbf_solver_index):
            for output_expression_index in rig.rdf_reader.getRBFPoseOutputExpressionIndices(pose_index):
                if rig.rdf_reader.getExpressionName(output_expression_index) == pose_name:
                    for joint_index in rig.rdf_reader.getRBFSolverInputJointIndices(rbf_solver_index):
                        if rig.rdf_reader.getJointName(joint_index) not in driver_joints:
                            driver_joints.append(rig.rdf_reader.getJointName(joint_index))
    return driver_joints


def get_joint_controls_output_indices_mapping(rig, raw_control_names):
    mapping = {}

    for rbf_solver_index in range(rig.rdf_reader.getRBFSolverCount()):
        rbf_input_indices = rig.rdf_reader.getRBFSolverInputJointIndices(rbf_solver_index)
        for rbf_input_index in rbf_input_indices:
            for i, raw_control in enumerate(raw_control_names):
                if raw_control.startswith(rig.dna_reader.getJointName(rbf_input_index)):
                    for pose_index in rig.rdf_reader.getRBFSolverOutputPoseIndices(rbf_solver_index):
                        for output_expression_index in rig.rdf_reader.getRBFPoseOutputExpressionIndices(pose_index):
                            if i in mapping:
                                mapping[i].add(
                                    (
                                        rig.rdf_reader.getExpressionName(output_expression_index),
                                        rig.rdf_reader.getExpressionControlIndex(output_expression_index),
                                    )
                                )
                            else:
                                mapping[i] = {
                                    (
                                        rig.rdf_reader.getExpressionName(output_expression_index),
                                        rig.rdf_reader.getExpressionControlIndex(output_expression_index),
                                    )
                                }
    return mapping


def extend_expression_data_with_rbf_data(rig, expression_data, additional_mapping):
    new_expression_data = {}
    for expression_name, all_phase_data in expression_data.items():
        updated_all_phase_data = []
        psd = rig.rig_definition.get_psd_def_for_expression(expression_name)
        if psd:
            for phase_data in all_phase_data:
                additional_values = {}
                remove_key = []
                for key in phase_data:
                    if key in additional_mapping:
                        remove_key.append(key)
                        for pose_name, control_index in additional_mapping[key]:
                            rig_expression = rig.rig_definition.get_expression_by_name(pose_name)
                            if rig_expression.function.input.name == psd.corrective_pose.name:
                                additional_values[control_index] = 1.0
                            else:
                                for subset in psd.sub_sets:
                                    if rig_expression.function.input.name == subset.corrective_pose.name:
                                        additional_values[control_index] = 1.0
                if additional_values:
                    updated_phase_data = {k: v for k, v in phase_data.items() if k not in remove_key}
                    updated_phase_data.update(additional_values)
                    updated_all_phase_data.append(updated_phase_data)
                else:
                    updated_all_phase_data.append(phase_data)
        else:
            updated_all_phase_data = all_phase_data
        new_expression_data[expression_name] = updated_all_phase_data
    return new_expression_data


def get_expression_raw_controls_mapping(rig, map_for_control_activation=False, control_renaming=None, rbf_data=None):
    expression_data = {}
    phase_expressions = {}
    raw_control_names = get_raw_control_names(rig, control_renaming)
    inverse_psd_combinations = get_inverse_psd_combinations(rig)

    for exp in rig.rig_definition.expressions:
        if exp.assemble_to_rig and len(exp.get_phase_numbers()) == 1:
            if exp.type == 1:
                if exp.assemble_to_rig:
                    expression_data[exp.name] = [{raw_control_names.index(str(exp.expression_attrs[0])): 1.0}]
            elif exp.type == 2:
                if exp.assemble_to_rig:
                    if exp.function:
                        expression_data[exp.function.input.name] = [
                            {
                                raw_control_names.index(str(generated_expression.expression_attrs[0])): 1.0
                                for generated_expression in exp.function.input.generates
                            }
                        ]
            elif exp.type == 5:
                if str(exp.expression_attrs[0]) in raw_control_names:
                    expression_data[exp.name] = [{raw_control_names.index(str(exp.expression_attrs[0])): 1.0}]
                elif get_control_type(rig, exp.expression_attrs[0].object_name) == rdf.ControlType_RBF:
                    driver_joints = get_driver_joints(rig, exp.name)
                    source_expression = exp.function.input.function.input1
                    neck_joint_animation = rbf_data["neck_joints_animation"]
                    try:
                        expression_data[exp.name] = [
                            {
                                raw_control_names.index(f"{driver_joint}.{rotation_attribute}"): neck_joint_animation[
                                    source_expression.name
                                ][driver_joint][attribute_index]
                                for driver_joint in driver_joints
                                for attribute_index, rotation_attribute in enumerate(dcc.ROTATION_ATTRIBUTES)
                            }
                        ]
                        for main_expression_name in rbf_data["main_expressions"]:
                            if main_expression_name in source_expression.name:
                                expression_data[main_expression_name] = expression_data[exp.name]
                    except KeyError:
                        print(f"Could not find {source_expression.name} in RBF data for {exp.name}.")

    for exp in rig.rig_definition.expressions:
        if exp.assemble_to_rig and len(exp.get_phase_numbers()) == 1:
            if exp.type == 5:
                if exp.function.function_type == 1 and exp.function.input.function.input1.name not in expression_data:
                    source_corrective = exp.function.input
                    temp_controls = {}
                    for generated in source_corrective.generates:
                        if generated.expression_attrs:
                            if str(generated.expression_attrs[0]) in raw_control_names:
                                temp_controls[raw_control_names.index(str(generated.expression_attrs[0]))] = 1.0
                            elif get_control_type(rig, exp.expression_attrs[0].object_name) == rdf.ControlType_RBF:
                                for control_data in expression_data[generated.name]:
                                    temp_controls.update(control_data)
                    if temp_controls:
                        for multi in source_corrective.function.input2.function.inputs:
                            if multi.expression.name in expression_data:
                                if map_for_control_activation:
                                    temp_controls.update(
                                        {
                                            key: value * multi.multiplier
                                            for key, value in expression_data[multi.expression.name][0].items()
                                        }
                                    )
                                for combination_length in range(1, len(list(temp_controls.keys())) + 1):
                                    for combination in combinations(list(temp_controls.keys()), combination_length):
                                        if tuple(sorted(combination)) in inverse_psd_combinations:
                                            temp_controls.update(
                                                {
                                                    key: value * multi.multiplier
                                                    for key, value in expression_data[multi.expression.name][0].items()
                                                }
                                            )
                    else:
                        multipliers_added = set()
                        multipliers_skipped = set()
                        for multi in source_corrective.function.input2.function.inputs:
                            net_added = False
                            if (
                                multi.expression.type == 1
                                and source_corrective.generates
                                and len(source_corrective.generates) == 1
                            ):
                                multipliers_added.add(multi.expression.name)
                                net_added = True
                                psd_net = rig.rig_definition.get_psd_net_by_output(source_corrective.generates[0].name)
                                temp_controls.update(
                                    {
                                        raw_control_names.index(str(input_)): input_.max_value
                                        for input_ in psd_net.inputs
                                    }
                                )
                            if multi.expression.name in expression_data and (
                                not net_added or map_for_control_activation
                            ):
                                multipliers_added.add(multi.expression.name)
                                if not map_for_control_activation and multi.multiplier < 1.0:
                                    continue
                                temp_controls.update(
                                    {
                                        key: value * multi.multiplier
                                        for key, value in expression_data[multi.expression.name][0].items()
                                    }
                                )
                            if multi.expression.name not in multipliers_added:
                                multipliers_skipped.add(multi.expression.name)
                        for psd_definition in rig.rig_definition.psd_definitions:
                            multipliers = {
                                multi.expression.name: multi.multiplier for multi in psd_definition.complex_pose_build
                            }
                            if set(multipliers.keys()) == multipliers_skipped:
                                temp_controls.update(expression_data[psd_definition.target_pose.name][0])

                    expression_data[source_corrective.function.input1.name] = [temp_controls]
                elif exp.function.function_type == 2 and exp.function.input2.name not in expression_data:
                    temp_controls = {}
                    for multi in exp.function.input2.function.inputs:
                        if multi.expression.name in expression_data:
                            temp_controls.update(
                                {
                                    key: value * multi.multiplier
                                    for key, value in expression_data[multi.expression.name][0].items()
                                }
                            )
                        elif f"{multi.expression.name}_cor" in expression_data:  # TODO: add view expressions
                            temp_controls.update(
                                {
                                    key: value
                                    for key, value in expression_data[f"{multi.expression.name}_cor"][0].items()
                                }
                            )
                    if exp.name in expression_data:
                        temp_controls.update({key: value for key, value in expression_data[exp.name][0].items()})
                    expression_data[exp.function.input1.name] = [temp_controls]
        elif len(exp.get_phase_numbers()) > 1 and not exp.assemble_to_rig:
            phase_expression_name_pattern = re.compile(rf"{exp.name}_ph(\d)")
            if exp.type == 1:
                for expression_name in expression_data:
                    phase_match = re.match(phase_expression_name_pattern, expression_name)
                    if phase_match is not None and not exp.function:
                        if exp.name not in phase_expressions:
                            phase_expressions[exp.name] = []
                        phase_expressions[exp.name].append(expression_data[expression_name][0])
            elif exp.type == 5:
                for expression_name in expression_data:
                    phase_match = re.match(phase_expression_name_pattern, expression_name)
                    if phase_match is not None and exp.function:
                        phase_index = int(phase_match.groups()[0])
                        target_expression_name = exp.function.input.function.input1.name
                        if target_expression_name not in phase_expressions:
                            phase_expressions[target_expression_name] = []
                        existing_raw_control_activations = {
                            raw_control_names.index(str(input_.expression.expression_attrs[0])): input_.multiplier
                            for input_ in exp.function.input.function.input2.function.inputs
                            if input_.expression.name in expression_data
                            and (map_for_control_activation or input_.multiplier == 1.0)
                        }
                        if len(phase_expressions[target_expression_name]) < phase_index:
                            phase_expressions[target_expression_name].append(existing_raw_control_activations)
                        else:
                            phase_expressions[target_expression_name][phase_index - 1].update(
                                existing_raw_control_activations
                            )
                        phase_expressions[target_expression_name][phase_index - 1].update(
                            expression_data[expression_name][0]
                        )

        expression_data.update(phase_expressions)

    for exp in rig.rig_definition.expressions:
        if exp.type not in [1, 4] and exp.name in expression_data:
            del expression_data[exp.name]

    return expression_data


def get_expression_analysis_mapping(rig, control_renaming, head_turns_data):
    expression_data = get_expression_raw_controls_mapping(
        rig, map_for_control_activation=True, control_renaming=control_renaming, rbf_data=head_turns_data
    )
    raw_control_names = get_raw_control_names(rig, control_renaming)

    analysis_mapping = {}

    for expression_name, all_phase_activations in expression_data.items():
        for expression_activations in all_phase_activations:
            rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
            raw_controls = [
                (raw_control_names[raw_control_index], max_value)
                for raw_control_index, max_value in expression_activations.items()
            ]
            if rig_expression.type == 1:
                analysis_mapping[(expression_name, 1)] = raw_controls
            else:
                psd_definition = rig.rig_definition.get_psd_def_for_expression(expression_name)
                analysis_mapping[(expression_name, psd_definition.layer + 1)] = raw_controls

    return analysis_mapping


def get_expression_joints_mapping(rig, control_renaming, head_turns_data):
    expression_data = get_expression_raw_controls_mapping(
        rig, control_renaming=control_renaming, rbf_data=head_turns_data
    )
    raw_control_names = get_raw_control_names(rig, control_renaming)
    joint_controls_output_indices_mapping = get_joint_controls_output_indices_mapping(rig, raw_control_names)
    expression_data = extend_expression_data_with_rbf_data(rig, expression_data, joint_controls_output_indices_mapping)
    inverse_psd_combinations = get_inverse_psd_combinations(rig)

    joint_names_per_expression = {}
    for expression_name, all_phase_activations in expression_data.items():
        raw_control_activations = {}
        for expression_activations in all_phase_activations:
            raw_control_activations.update(expression_activations)
        try:
            control_set = raw_control_activations

            control_combinations = {}

            for combination_length in range(1, len(control_set) + 1):
                for combination in combinations(control_set, combination_length):
                    if tuple(sorted(combination)) in inverse_psd_combinations:
                        if combination_length not in control_combinations:
                            control_combinations[combination_length] = []
                        control_combinations[combination_length].append(tuple(sorted(combination)))

            max_key = max(control_combinations.keys())

            control_indices = [inverse_psd_combinations[tuple(sorted(key))] for key in control_combinations[max_key]]
        except ValueError:
            control_indices = list(raw_control_activations.keys())
        joint_names = set()
        for joint_group_index in range(rig.dna_reader.getJointGroupCount()):
            for control_index in control_indices:
                if control_index in rig.dna_reader.getJointGroupInputIndices(joint_group_index):
                    for joint_index in rig.dna_reader.getJointGroupJointIndices(joint_group_index):
                        joint_names.add(rig.dna_reader.getJointName(joint_index))
        joint_names_per_expression[expression_name] = list(joint_names)

    return joint_names_per_expression


def get_expression_joints_from_scene(rig, group_name):
    scene_joints = dcc.get_joints_from_scene(rig, group_name)

    expression_joints = []
    for joint in rig.rig_definition.joints.get_all_elements():
        long_joint_name = f"{group_name}{dcc.get_joint_long_name(rig, joint.name)}"
        expression_joints.extend(scene_joints[long_joint_name].translate)
        expression_joints.extend(scene_joints[long_joint_name].rotate)
        expression_joints.extend(scene_joints[long_joint_name].scale)

    return expression_joints


def get_raw_control_values(rig, control_renaming):
    raw_control_names = get_raw_control_names(rig, control_renaming)

    control_values = {}
    for raw_control_name in raw_control_names:
        if cmds.objExists(raw_control_name):
            control_value = cmds.getAttr(raw_control_name)
            if isinstance(control_value, list):
                joint_name, attribute_name = raw_control_name.split(".")
                control_value = cmds.getAttr(f"head_grp{dcc.get_joint_long_name(rig, joint_name)}.{attribute_name}")
            control_values[raw_control_name] = control_value
        else:
            control_values[raw_control_name] = 0.0

    return control_values


def get_raw_to_gui(rig, control_renaming, head_turns_data):
    return {
        "raw_ctrl_names": [rig.dna_reader.getRawControlName(x) for x in range(rig.dna_reader.getRawControlCount())],
        "gui_ctrl_names": [rig.dna_reader.getGUIControlName(x) for x in range(rig.dna_reader.getGUIControlCount())],
        "raw_cut_values": rig.dna_reader.getGUIToRawCutValues(),
        "raw_slope_values": rig.dna_reader.getGUIToRawSlopeValues(),
        "gtroi": rig.dna_reader.getGUIToRawOutputIndices(),
        "gtrii": rig.dna_reader.getGUIToRawInputIndices(),
        "expressions_to_raw": expression_to_raw(rig, control_renaming, head_turns_data),
    }


def analyze_frame(rig, expression_controls_mapping, control_renaming):
    control_values = get_raw_control_values(rig, control_renaming)
    expression_weights = {}
    for (expression_name, layer), controls in expression_controls_mapping.items():
        raw_value = 1.0
        for ctrl, max_value in controls:
            if max_value:
                with contextlib.suppress(KeyError):
                    raw_value *= max(0, control_values[ctrl] / max_value)
        value = raw_value ** (1 / layer)
        expression_weights[expression_name] = value

    return expression_weights


def assemble_rig_editing_scene(
    rig,
    dna_file_path,
    callbacks,
    callback,
    node_name,
    cbs_pruning_threshold,
    joint_pruning_threshold,
    head_main_exp,
    neck_joints,
    neck_joints_values,
    left_arm_joint_name,
    eye_aim_control_name,
    right_eye_control_name,
    gui_object_name,
    up_axis,
    rotation,
):
    dcc.remove_callbacks(callbacks)
    dcc.ensure_plugin_available("cbsNode")
    dcc.assemble_rig_editing_scene(
        rig, left_arm_joint_name, eye_aim_control_name, right_eye_control_name, gui_object_name, up_axis, rotation
    )

    ProgressStart.emit(max_value=2)
    ProgressUpdate.emit(status="Creating DNACalib node...")
    dcc.add_dna_calib_node(
        node_name,
        dna_file_path,
        Resources().rdf_file_path,
        cbs_pruning_threshold,
        joint_pruning_threshold,
        head_main_exp,
        neck_joints,
        neck_joints_values,
        rotation,
    )
    dcc.camera_position()
    callbacks = [dcc.add_gui_ctrl_callbacks(callback)]
    ProgressEnd.emit()
    return callbacks


def get_main_expression_controls(rig, expression_name, split_expressions):
    rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
    if rig_expression.type == 1:
        return {}
    psd_definition = rig.rig_definition.get_psd_def_for_expression(expression_name)
    if psd_definition:
        result = {multiplier.expression.name: multiplier.multiplier for multiplier in psd_definition.complex_pose_build}
        multipliers = set(result.keys())
        for target_expression, main_expressions in split_expressions.items():
            if multipliers == set(main_expressions):
                continue
            if multipliers.issuperset(set(main_expressions)):
                multipliers.difference_update(set(main_expressions))
                multipliers.add(target_expression)
                result[target_expression] = 1.0
                for main_expression in main_expressions:
                    result[target_expression] *= result[main_expression]
        return {multiplier: result[multiplier] for multiplier in multipliers}
    return {}


def get_main_expressions(rig, expression_name):
    rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
    if rig_expression.type == 1:
        return [expression_name], {expression_name: 1.0}, {}
    psd_definition = rig.rig_definition.get_psd_def_for_expression(expression_name)
    if psd_definition:
        expressions = {
            multiplier.expression.name: multiplier.multiplier for multiplier in psd_definition.complex_pose_build
        }
        psd_matrix = {
            psd_definition.corrective_pose.name: list(expressions.keys()),
        }
        input_names = sorted(list(expressions.keys()))

        expressions[psd_definition.corrective_pose.name] = 1.0
        for subset in psd_definition.sub_sets:
            expressions[subset.corrective_pose.name] = 1.0
            multipliers = set([multi.expression.name for multi in subset.complex_pose_build])
            psd_matrix[subset.corrective_pose.name] = list(multipliers)

        return input_names, expressions, psd_matrix
    return [], {}, {}


def get_preview_psd_data(rig, input_names, expressions, psd_matrix, split_expressions):
    merged_expression_indices = []
    merged_expression_drivers = []

    for split_expression, main_expressions in split_expressions.items():
        if split_expression in psd_matrix:
            input_names.append(split_expression)
            merged_expression_indices.append(len(input_names) - 1)
            merged_expression_drivers.append(input_names.index(main_expressions[0]))
            split_expression_count = 0
            for expression_name in main_expressions:
                rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
                if rig_expression.assemble_to_rig:
                    split_expression_count += 1
                else:
                    split_expression_count += len(rig_expression.generates)
            rig_split_expression = rig.rig_definition.get_expression_by_name(split_expression)
            if not rig_split_expression.assemble_to_rig:
                split_expression_count /= len(rig_split_expression.generates)
            merged_expression_drivers.append(split_expression_count)
            del psd_matrix[split_expression]
            for psd in psd_matrix:
                if set(main_expressions).issubset(set(psd_matrix[psd])):
                    temp = set(psd_matrix[psd])
                    temp.difference_update(set(main_expressions))
                    psd_matrix[psd] = list(temp)
                    psd_matrix[psd].append(main_expressions[0])

    psd_names = list(psd_matrix.keys())

    blend_shape_names = input_names + psd_names

    psd_indices = []
    control_indices = []
    weights = []

    for psd in psd_names:
        input_expressions = psd_matrix[psd]
        for input_expression in input_expressions:
            psd_indices.append(blend_shape_names.index(psd))
            control_indices.append(blend_shape_names.index(input_expression))
            weights.append(1.0 / expressions[input_expression])

    return {
        "input_names": input_names,
        "psd_names": psd_names,
        "merged_expression_indices": merged_expression_indices,
        "merged_expression_drivers": merged_expression_drivers,
        "psd_indices": psd_indices,
        "control_indices": control_indices,
        "weights": weights,
    }


def assemble_skin_editing_scene(
    rig,
    dna_file_path,
    selected_lods,
    callbacks,
    callback,
    left_arm_joint_name,
    eye_aim_control_name,
    right_eye_control_name,
    gui_object_name,
    up_axis,
    rotation,
):
    dcc.remove_callbacks(callbacks)
    callbacks = dcc.assemble_skin_editing_scene(
        rig,
        selected_lods,
        callback,
        left_arm_joint_name,
        eye_aim_control_name,
        right_eye_control_name,
        gui_object_name,
        up_axis,
        rotation,
    )

    ProgressStart.emit(max_value=1)
    ProgressUpdate.emit(status="Adding RigLogic node")
    dcc.add_rig_logic_node(dna_file_path.replace("\\", "/"))
    ProgressEnd.emit()

    dcc.camera_position()
    return callbacks


def ordered_calculation(rig, expression_names=None):
    if not expression_names:
        expression_names = [expression.name for expression in rig.rig_definition.expressions]
    RigCalculationHandler.ordered_calculation(rig, expression_names)


def update_skin(rig, meshes):
    dcc.update_skin(rig, meshes)
    ordered_calculation(rig)


def optimize_rig(rig, jm_files):
    for file_name in jm_files:
        options = read_joints_matching_preset(file_name)
        match_joints(rig, options)
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status="Calculating new corrective blend shapes.")
        calculate_expressions(rig)
        ProgressEnd.emit()


def modify_current_rig_state_with_commands(rig, runnable, dna_file_path):
    reader = dnacalib.DNACalibDNAReader(rig.dna_reader)
    rig.rig.exportDNA(reader)

    runnable.run(reader)

    stream = dna.FileStream(
        dna_file_path,
        dna.FileStream.AccessMode_Write,
        dna.FileStream.OpenMode_Binary,
    )
    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(reader)
    writer.write()


def custom_body_dna_check(body_dna_file_path, neck_joints):
    dna_reader = DNAFileHandler.get_reader(body_dna_file_path)
    joint_names = [dna_reader.getJointName(i) for i in range(dna_reader.getJointCount())]

    missing_joints = []

    if joint_names and joint_names[0] != "root":
        missing_joints.append("root")

    for neck_joint in neck_joints:
        if neck_joint not in joint_names:
            missing_joints.append(neck_joint)
    return missing_joints


def export(
    rig,
    body_scene_file_path,
    export_folder_path,
    character_name,
    neck_joints,
    up_axis,
    up_axis_dna_rotation,
    up_axis_body_dna_rotation,
    up_axis_body_scene_orient,
    material_names,
):
    ProgressStart.emit(max_value=3)

    ProgressUpdate.emit(status="Checking body scene...")
    if body_scene_file_path.endswith(".dna"):
        missing_joints = custom_body_dna_check(body_scene_file_path, neck_joints)
    else:
        missing_joints = dcc.custom_body_file_check(body_scene_file_path, neck_joints)
    if missing_joints:
        ProgressEnd.emit()
        cmds.warning(f"Missing joints in body file: {', '.join(missing_joints)}.")
        return

    ProgressUpdate.emit(status="Preparing MetaHuman DNA...")
    export_dna_file_path = f"{export_folder_path}/{character_name}.dna"

    cmd = dnacalib.RotateCommand(up_axis_dna_rotation, [0.0, 0.0, 0.0])
    modify_current_rig_state_with_commands(rig, cmd, export_dna_file_path)

    ProgressUpdate.emit(status="Getting rig data")
    export_rig = RigDataHandler(
        Resources().rdf_file_path,
        export_dna_file_path,
    )
    ProgressEnd.emit()

    ProgressStart.emit(max_value=6)

    current_up_axis = cmds.upAxis(ax=True, query=True)

    ProgressUpdate.emit(status="Assembling scene")
    dcc.assemble_fbx_export_scene(export_rig, up_axis)
    ProgressUpdate.emit(status="Adding body")
    dcc.add_body(
        export_rig,
        body_scene_file_path,
        neck_joints,
        up_axis_body_dna_rotation,
        up_axis_body_scene_orient,
        neck_joints[0],
    )
    ProgressUpdate.emit(status="Changing material names")
    dcc.update_material_names(material_names)
    ProgressUpdate.emit(status="Exporting FBX files")
    dcc.export_fbx(export_rig, export_folder_path, character_name, up_axis)

    cmds.upAxis(ax=current_up_axis)

    ProgressUpdate.emit(status="Reading MetaHuman DNA")
    stream = dna.FileStream(
        export_dna_file_path,
        dna.FileStream.AccessMode_Read,
        dna.FileStream.OpenMode_Binary,
    )
    data_layers = (
        dna.DataLayer_Behavior
        | dna.DataLayer_RBFBehavior
        | dna.DataLayer_JointBehaviorMetadata
        | dna.DataLayer_TwistSwingBehavior
    )
    reader = dna.BinaryStreamReader(stream, data_layers)
    reader.read()

    ProgressUpdate.emit(status="Writing MetaHuman DNA")
    stream = dna.FileStream(
        export_dna_file_path,
        dna.FileStream.AccessMode_Write,
        dna.FileStream.OpenMode_Binary,
    )
    writer = dna.BinaryStreamWriter(stream)
    writer.setFrom(reader)
    writer.write()

    ProgressEnd.emit()


def assemble_neutral_editing_scene(rig, geo_view_selected, callbacks, callback, up_axis):
    dcc.remove_callbacks(callbacks)
    callbacks = dcc.assemble_neutral_editing_scene(rig, geo_view_selected, callback, up_axis)
    dcc.camera_position()
    return callbacks


def get_dna_lods(rig):
    load_meshes = {}
    for load in rig.rig_definition.lod_meshes:
        load_meshes[load.name] = {}
        for mesh_name in load.meshes:
            load_meshes[load.name][mesh_name] = False
    return load_meshes


def get_dna_joints(rig):
    joints = {}
    all_joints = rig.rig_definition.joints.get_all_elements()

    for joint in all_joints:
        if joint.name not in joints:
            joints[joint.name] = {}
        for child in joint.children:
            if child.name not in joints:
                joints[child.name] = {}
            joints[joint.name][child.name] = joints[child.name]

    result = {}
    for key, value in joints.items():
        result[key] = value

    return {all_joints[0].name: result.get(all_joints[0].name)}


def get_rig_geo(group_name):
    meshes = {}
    head_grp = get_hierarchy_as_dict("head_grp", visible_only=True, node_type="transform")
    meshes["head_grp"] = head_grp
    edit_grp = get_hierarchy_as_dict(group_name, visible_only=True, node_type="transform")
    meshes[group_name] = edit_grp
    return meshes


def get_rig_jnt(group_name):
    joints = {}
    edit_grp = get_hierarchy_as_dict(group_name, visible_only=True, node_type="joint")
    joints[group_name] = edit_grp
    return joints


def get_hierarchy_as_dict(root_node, visible_only=False, node_type=None):
    hierarchy_dict = {}
    children = cmds.listRelatives(root_node, children=True, fullPath=True) or []
    if node_type:
        children = [c for c in children if cmds.objectType(c) == node_type]
    if visible_only:
        children = [c for c in children if cmds.getAttr(c + ".visibility")]
    for child in children:
        child_name = cmds.ls(child, long=True)[0]
        hierarchy_dict[child_name] = (
            get_hierarchy_as_dict(child, visible_only=visible_only, node_type=node_type) or True
        )

    return hierarchy_dict


def update_neutral_meshes(rig, scene_mesh_names, rotation):
    ProgressStart.emit(max_value=4)

    ProgressUpdate.emit(status="Updating neutral meshes")

    try:
        dcc.select_objects_by_name(scene_mesh_names)
    except ValueError as e:
        raise RuntimeError(e)

    for dir_path, _, file_names in os.walk(Resources().vertex_joint_mapping_folder_path):
        for file_name in file_names:
            if file_name.endswith(".csv"):
                mesh_name = f"lod0|{file_name.split('.')[0]}"

                if dcc.check_scene_for_object_by_name(mesh_name):
                    surface_joints_mapping = {}
                    volumetric_joints_mapping = {}
                    with open(os.path.join(dir_path, file_name)) as f:
                        for line in f:
                            parts = line.strip().split(" ")
                            joint_name, vertex_id = parts[0], int(parts[1])
                            if len(parts) == 2:
                                surface_joints_mapping[joint_name] = vertex_id
                            elif len(parts) == 5:
                                volumetric_joints_mapping[joint_name] = (
                                    vertex_id,
                                    [float(part) for part in parts[2:]],
                                )

                    ProgressUpdate.emit(status=f"Update volumetric joints: {mesh_name}", hold=True)
                    dcc.update_volumetric_joints(mesh_name, volumetric_joints_mapping, rotation)

                    ProgressUpdate.emit(status=f"Update surface joints: {mesh_name}", hold=True)
                    dcc.update_surface_joints(mesh_name, surface_joints_mapping)
        break
    ProgressUpdate.emit(status="Set neutral joints")
    try:
        rig.set_maya_neutral_joints()
    except MayaSceneError as e:
        raise RuntimeError(e)

    for scene_mesh_name in scene_mesh_names:
        if dcc.check_scene_for_object_by_name(scene_mesh_name):
            mesh_name = scene_mesh_name.split("|")[1]
            vertex_positions = dcc.get_mesh_vertex_positions(scene_mesh_name)

            ProgressUpdate.emit(status=f"Set neutral: {mesh_name}", hold=True)
            rig.set_neutral_mesh(mesh_name, vertex_positions)

    ProgressUpdate.emit(status="Calculate neutral mesh")
    calculate_expressions(rig, calculate_new_sculpts=True)
    ProgressUpdate.emit(status="Done")
    ProgressEnd.emit()


def update_neutral_joints(rig):
    ProgressStart.emit(max_value=3)

    ProgressUpdate.emit(status="Set neutral joints")
    try:
        rig.set_maya_neutral_joints()
    except MayaSceneError as e:
        raise RuntimeError(e)

    ProgressUpdate.emit(status="Calculate neutral joints")
    calculate_expressions(rig)
    ProgressUpdate.emit(status="Done")
    ProgressEnd.emit()


def calculate_lower_lods(rig, source_lod):
    lod_generation = LODGeneration(Resources().lod_generation_model_description_path, source_lod)
    return lod_generation.apply(rig)


def expression_to_raw(rig, control_renaming, head_turns_data):
    expression_raw_control_indices_activation = get_expression_raw_controls_mapping(
        rig, map_for_control_activation=True, control_renaming=control_renaming, rbf_data=head_turns_data
    )
    raw_control_names = get_raw_control_names(rig, control_renaming)

    return {
        expression_name: {
            raw_control_names[raw_control_index]: activation
            for expression_activations in all_phase_activations
            for raw_control_index, activation in expression_activations.items()
        }
        for expression_name, all_phase_activations in expression_raw_control_indices_activation.items()
    }


def get_expressions_to_fix_data(rig, dirty_expressions=None):
    expressions_to_fix = {}
    expressions_triggering_fix = set()
    for psd_def in rig.rig_definition.psd_definitions:
        deformable_meshes = set(
            [mie.mesh.name for mie in psd_def.target_pose.meshes_in_expression if mie.type in [2, 3]]
        )
        for exp_multiplier in psd_def.complex_pose_build:
            multiplier_deformable_meshes = set(
                [mie.mesh.name for mie in exp_multiplier.expression.meshes_in_expression if mie.type in [2, 3]]
            )
            if (
                multiplier_deformable_meshes
                and (
                    not multiplier_deformable_meshes.issubset(deformable_meshes)
                    and not deformable_meshes.issubset(multiplier_deformable_meshes)
                )
                or (exp_multiplier.multiplier < 1.0 and exp_multiplier.expression.assemble_to_rig)
            ):
                if dirty_expressions is None or (
                    dirty_expressions is not None and exp_multiplier.expression.name in dirty_expressions
                ):
                    expressions_triggering_fix.add(exp_multiplier.expression.name)
                    if psd_def.layer in expressions_to_fix:
                        expressions_to_fix[psd_def.layer].append(psd_def.name)
                    else:
                        expressions_to_fix[psd_def.layer] = [psd_def.name]
    return expressions_to_fix, list(expressions_triggering_fix)


def calculate_expressions(rig, calculate_new_sculpts=False):
    dirty_expressions = {rig.rig_definition.expressions[index].name for index in rig.rig.getDirtyExpressionIndices()}

    max_psd_layer = 0
    for psd_def in rig.rig_definition.psd_definitions:
        if psd_def.layer > max_psd_layer:
            max_psd_layer = psd_def.layer

    expressions_to_fix, _ = get_expressions_to_fix_data(rig, dirty_expressions)

    for psd_layer in range(max_psd_layer + 1):
        if calculate_new_sculpts:
            calculation_filter = RigCalculationHandler.create_calculation_filter(
                rig, RigCalculationHandler.CALCULATE_SCULPT
            )
            calculation_filter.setMaxPSDLevel(psd_layer)
            rig.rig.calculateExpressions(calculation_filter)
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig, RigCalculationHandler.CALCULATE_CORRECTIVE
        )
        calculation_filter.setMaxPSDLevel(psd_layer)
        rig.rig.calculateExpressions(calculation_filter)
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig, RigCalculationHandler.CALCULATE_SCULPT
        )
        calculation_filter.setMaxPSDLevel(psd_layer)
        rig.rig.calculateExpressions(calculation_filter)
        rig.update_dirty_expressions()

        if psd_layer + 1 in expressions_to_fix:
            for psd_def_name in expressions_to_fix[psd_layer + 1]:
                psd_def = rig.rig_definition.get_psd_def_by_name(psd_def_name)
                RigCalculationHandler.calculate_expression(
                    rig, psd_def.complex_pose.name, RigCalculationHandler.CALCULATE_CORRECTIVE
                )

                for mie in psd_def.target_pose.meshes_in_expression:
                    for phase in psd_def.target_pose.get_phase_numbers():
                        if mie.type in [2, 3]:
                            neutral_joints = rig.get_neutral_joints()
                            cmx_joints = rig.get_expression_joints(psd_def.complex_pose.name, 1)
                            cor_joints = rig.get_expression_joints(psd_def.corrective_pose.name, phase)
                            tgt_joints = [
                                (
                                    cmx_joint_value - neutral_joint_value + cor_joint_value
                                    if i % 9 not in [3, 4, 5]
                                    else cmx_joint_value + cor_joint_value
                                )
                                for i, (cmx_joint_value, neutral_joint_value, cor_joint_value) in enumerate(
                                    zip(cmx_joints, neutral_joints, cor_joints)
                                )
                            ]
                            rig.set_expression_joints(psd_def.target_pose.name, phase, tgt_joints)

                            neutral_mesh = rig.get_neutral_mesh_vertex_positions(mie.mesh.name)
                            cmx_cbs = rig.get_cbs_mesh_vertex_positions(mie.mesh.name, psd_def.complex_pose.name, 1)
                            cor_cbs = rig.get_cbs_mesh_vertex_positions(
                                mie.mesh.name, psd_def.corrective_pose.name, phase
                            )
                            tgt_cbs = [
                                [
                                    cmx_vtx[0] - neutral_vtx[0] + cor_vtx[0],
                                    cmx_vtx[1] - neutral_vtx[1] + cor_vtx[1],
                                    cmx_vtx[2] - neutral_vtx[2] + cor_vtx[2],
                                ]
                                for cmx_vtx, neutral_vtx, cor_vtx in zip(cmx_cbs, neutral_mesh, cor_cbs)
                            ]
                            rig.set_corrective_blend_shape(mie.mesh.name, psd_def.target_pose.name, phase, tgt_cbs)

                            RigCalculationHandler.calculate_expression(
                                rig, psd_def.target_pose.name, RigCalculationHandler.CALCULATE_SCULPT
                            )


def serialize_scene(scene, name=None, path=None):
    if not name or not path:
        return
    file_path = os.path.join(path, name)
    with open(f"{file_path}.json", "w") as json_file:
        json.dump(scene, json_file, indent=2, default=vars)


def deserialize_scene(path=None):
    try:
        with open(path) as json_file:
            scene = json.load(json_file)
    except Exception:
        return None
    scn = SceneModel()
    for name, value in scene["nodes"].items():
        scn.nodes.update({name: NodeModel(**value)})
    return scn


def populate_branch(scene_model, whole_scene):
    old_scene_model = scene_model.nodes.copy()
    for node_model in old_scene_model.values():
        node = whole_scene.get_node_by_name(node_model.name)

        for node_out in node.outputs:
            output_que = deque([node_out])
            while output_que:
                current = output_que.popleft()
                if not scene_model.nodes.get(current.name):
                    new_node = NodeModel().copy(whole_scene.get_node_by_name(current.name))
                    scene_model.nodes[current.name] = new_node
                    try:
                        node_model.outputs.index(current.name)
                    except ValueError:
                        node_model.outputs.append(current.name)
                for out in current.outputs:
                    if not scene_model.nodes.get(out.name):
                        new_node = NodeModel().copy(whole_scene.get_node_by_name(out.name))
                        scene_model.nodes[out.name] = new_node
                    output_que.append(out)

        scene_model.nodes[node_model.name] = node_model
    scene_model.nodes = sort_nodes_by_layer(scene_model.nodes)
    return scene_model


def sort_nodes_by_layer(nodes):
    nodes = dict(sorted(nodes.items(), key=lambda item: item[1].layer))
    for node_name, node in nodes.items():
        for input_exp in node.inputs:
            if input_exp in nodes:
                if node_name not in nodes[input_exp].outputs:
                    nodes[input_exp].outputs.append(node_name)
    return nodes


def get_phase_expression_control_activation(rig, expression_name, phase):
    rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
    if rig_expression.type == 1:
        phase_expression = rig.rig_definition.get_expression_by_name(f"{expression_name}_ph{phase}")
        try:
            return [(str(phase_expression.expression_attrs[0]), 1.0)]
        except AttributeError:
            return []
    elif rig_expression.type == 4:
        controls = []
        psd_definition = rig.rig_definition.get_psd_def_for_expression(expression_name)
        for multiplier in psd_definition.complex_pose_build:
            if multiplier.expression.assemble_to_rig:
                controls.append((str(multiplier.expression.expression_attrs[0]), multiplier.multiplier))
        if psd_definition.corrective_pose.assemble_to_rig:
            controls.append((str(psd_definition.corrective_pose.expression.expression_attrs[0]), 1.0))
        else:
            for expression in psd_definition.corrective_pose.generates:
                phase_expression = rig.rig_definition.get_expression_by_name(f"{expression.name}_ph{phase}")
                controls.append((str(phase_expression.expression_attrs[0]), 1.0))
        return controls
    return []
