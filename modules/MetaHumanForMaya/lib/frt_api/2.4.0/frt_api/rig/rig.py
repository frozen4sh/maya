# Copyright Epic Games, Inc. All Rights Reserved.

import logging
from math import pi
from typing import Any, Dict, List, Tuple, Union, Optional
from inspect import getfullargspec

import dna
import rdf
import dnacalib2
import dnacalib2 as dnacalib
import maya.api.OpenMaya as om
from maya import cmds

from ..core import FRTApiError, status_validator, status_validator_dnacalib
from ..maya import MeshMayaHandler, JointMayaHandler
from ..model.rig import Expression, PsdInputValue, PlugInputValue, RangedInputValue
from ..publisher import ProgressUpdate, ExpressionChanged, progress_guard
from ..file.dna_file import DNAFileHandler
from ..model.maya.joint import MayaJoint, MayaJointDataHolder
from ..model.rdf.mapper import get_rig_definition
from ..model.skin_weights import MayaSkinWeights
from ..model.maya.anim_curve import (
    MayaAnimCurve,
    MayaAnimCurveKey,
    MayaAnimCurveAttribute,
)
from ..model.rig_definition.skin_weights import SkinningData
from ..model.rig_definition.rig_definition import RigDefinition

logger = logging.getLogger("frt_api.rig")


class MeshNotFoundError(Exception):
    pass


class DeltaRigNotFoundError(Exception):
    pass


def calculate_sculpt(func):
    arg_spec = getfullargspec(func)

    def wrapper(*args, **kwargs):
        rig_data_handler = args[0]
        try:
            expression_name = args[arg_spec.args.index("expression_name")]
            expressions = [
                rig_data_handler.rig_definition.expressions[i].name
                for i in rig_data_handler.get_dependent_expression_indices(expression_name)
            ]
            expressions.insert(0, expression_name)
            calculate_sculpts_expressions = []
            for expression in expressions:
                if expression not in rig_data_handler.calculated_sculpts:
                    calculate_sculpts_expressions.append(expression)
            _calculate_expressions(calculate_sculpts_expressions, rig_data_handler)
        except ValueError:
            logging.warning(
                f"Method {func.__name__} doesn't have argument with pattern expression_name, calculate_sculpt decorator shouldn't be used."
            )
        return func(*args, **kwargs)

    return wrapper


def _calculate_expressions(expressions, rig_data_handler):
    if expressions:
        from .calculation import RigCalculationHandler

        rig_data_handler.set_expressions_dirty(expressions)
        RigCalculationHandler.calculate_expressions(
            rig_data_handler, expressions, RigCalculationHandler.CALCULATE_SCULPT
        )
        rig_data_handler.calculated_sculpts.update(expressions)
        rig_data_handler.set_expressions_clean(expressions)


def calculate_sculpts(func):
    def wrapper(*args, **kwargs):
        rig_data_handler = args[0]
        expressions = []
        for expression in rig_data_handler.rig_definition.expressions:
            if expression.name not in rig_data_handler.calculated_sculpts:
                expressions.append(expression.name)
        _calculate_expressions(expressions, rig_data_handler)
        return func(*args, **kwargs)

    return wrapper


class RigMayaHandler:
    """
    Rig Maya handler.

    Creates rig logic object model which represent assembled rig.
    """

    @staticmethod
    def get_full_name(obj_name, attr_name):
        return obj_name + "." + attr_name

    @staticmethod
    def get_inputs(
        rig_definition: RigDefinition,
    ) -> Tuple[List[Union[PlugInputValue, PsdInputValue]], Dict[Any, Union[PlugInputValue, PsdInputValue]]]:
        """
        Creates inputs data model based on rig definition.
        """

        inputs_dict: Dict[Union[str, Any], Union[PlugInputValue, PsdInputValue]] = {}

        # get expression inputs
        for exp in rig_definition.expressions:
            if exp.assemble_to_rig:
                for attr in exp.expression_attrs:
                    input_full_name = RigMayaHandler.get_full_name(attr.object_name, attr.attr_name)
                    if input_full_name in inputs_dict:
                        plug_in_val = inputs_dict[input_full_name]
                    else:
                        plug_in_val = PlugInputValue(
                            0, attr.object_name, attr.attr_name, attr.min_value, attr.max_value
                        )
                        inputs_dict[input_full_name] = plug_in_val
                    plug_in_val.expressions.append(Expression(exp.name, exp.type, attr.from_value, attr.to_value))

        # update psd inputs
        for psd_net in rig_definition.psd_nets:
            if not (psd_net.output and psd_net.output.object_name and psd_net.output.attr_name):
                continue
            on_off_in_val = None
            if psd_net.on_attr and psd_net.on_attr.object_name and psd_net.on_attr.attr_name:
                on_off_in_val = PlugInputValue(
                    0,
                    psd_net.on_attr.object_name,
                    psd_net.on_attr.attr_name,
                    psd_net.on_attr.min_value,
                    psd_net.on_attr.max_value,
                )
                if on_off_in_val.get_full_name() not in inputs_dict:
                    inputs_dict[on_off_in_val.get_full_name()] = on_off_in_val
                else:
                    on_off_in_val = inputs_dict[on_off_in_val.get_full_name()]
            # psd input value
            psd_in_val = PsdInputValue(
                0,
                psd_net.output.object_name,
                psd_net.output.attr_name,
                psd_net.output.min_value,
                psd_net.output.max_value,
                None,
                on_off_in_val,
            )

            if psd_in_val.get_full_name() in inputs_dict:
                psd_in_val.expressions = inputs_dict[psd_in_val.get_full_name()].expressions[:]

            inputs_dict[psd_in_val.get_full_name()] = psd_in_val
            # get inputs for psd net
            for psdNetIn in psd_net.inputs:
                range_in_val = PlugInputValue(
                    0, psdNetIn.object_name, psdNetIn.attr_name, psdNetIn.min_value, psdNetIn.max_value
                )
                if range_in_val.get_full_name() in inputs_dict:
                    range_in_val = inputs_dict[range_in_val.get_full_name()]
                else:
                    inputs_dict[range_in_val.get_full_name()] = range_in_val
                psd_in_val.ranged_inputs.append(RangedInputValue(range_in_val, psdNetIn.from_value, psdNetIn.to_value))

        # sort imputs
        inputs_list = []
        psd_list = []
        # rest of inputs
        for in_val in list(inputs_dict.values()):
            if in_val.type == PlugInputValue.TYPE_PLUG and in_val not in inputs_list:
                inputs_list.append(in_val)
            elif in_val.type == PlugInputValue.TYPE_PSD:
                psd_list.append(in_val)
        inputs_list.sort(key=lambda item: item.get_interface_name())
        psd_list.sort(key=lambda item: item.get_interface_name())
        inputs_list.extend(psd_list)

        # add index
        for i, in_val in enumerate(inputs_list):
            in_val.id = i
        return inputs_list, inputs_dict


class RigDataHandler:
    @progress_guard(max_value=4)
    @status_validator([dna, rdf, dnacalib])
    def __init__(
        self,
        binary_rig_definition_file_path,
        dna_file_path,
        corrective_blend_shape_pruning_threshold=0.0,
        joint_translation_pruning_threshold=0.0,
        joint_rotation_pruning_threshold=0.0,
        joint_scale_pruning_threshold=0.0,
    ):
        ProgressUpdate.emit(status="rig initialize")

        self.rig_definition, self.rdf_reader = get_rig_definition(binary_rig_definition_file_path)
        ProgressUpdate.emit(status="read rig definition and rdf")

        self.dna_reader: dna.BinaryStreamReader = DNAFileHandler.get_reader(dna_file_path)
        ProgressUpdate.emit(status="read dna")

        self.rig: dnacalib2.Rig = dnacalib.Rig(self.rdf_reader, self.dna_reader)
        ProgressUpdate.emit(status="construct rig object")

        self.rig.setCorrectiveBlendShapePruningThreshold(corrective_blend_shape_pruning_threshold)
        self.rig.setJointPruningThreshold(
            joint_translation_pruning_threshold,
            joint_rotation_pruning_threshold,
            joint_scale_pruning_threshold,
        )
        self.expression_indices: Dict[str, int] = {exp.name: i for i, exp in enumerate(self.rig_definition.expressions)}
        self._joint_indices: Dict[str, int] = {
            joint.name: i for i, joint in enumerate(self.rig_definition.joints.get_all_elements())
        }
        self._mesh_indices: Dict[str, int] = {
            mesh: i for i, mesh in enumerate(self.rig_definition.get_dna_mesh_names())
        }
        self._neutral_mesh_topology = {}
        self._joint_chain_indices = {}
        self.delta_rig = None
        self.calculated_sculpts = set()

    @status_validator_dnacalib
    def save_current_rig_state(self):
        current_reader = dnacalib.DNACalibDNAReader(self.dna_reader)
        self.rig.exportDNA(current_reader)
        self.delta_rig = dnacalib.Rig(self.rdf_reader, current_reader)

    @status_validator_dnacalib
    def get_rig_delta(self) -> dnacalib.RigDelta:
        if not self.delta_rig:
            raise DeltaRigNotFoundError("No saved rig state to calculate delta from.")
        delta = dnacalib.RigDelta(list(range(len(self.rig_definition.expressions))), self.rdf_reader)
        self.rig.calculateDelta(self.delta_rig, delta)
        return delta

    def get_dependent_expression_indices(self, expression_name) -> List[int]:
        value: List[int] = self.rig.getDependentExpressionIndices(self.expression_indices[expression_name])
        return value

    def update_dirty_expressions(self):
        dirty_expressions_indices = set(self.rig.getDirtyExpressionIndices())

        for expression_index, expression in enumerate(self.rig_definition.expressions):
            expression.dirty = expression_index in dirty_expressions_indices

        ExpressionChanged.emit()

    @status_validator_dnacalib
    def set_expressions_dirty(self, expression_names):
        expression_indices = [self.expression_indices[expression_name] for expression_name in expression_names]

        self.rig.setDirtyExpressionIndices(expression_indices)
        self.update_dirty_expressions()

    @status_validator_dnacalib
    def set_expressions_clean(self, expression_names):
        expression_indices = [self.expression_indices[expression_name] for expression_name in expression_names]

        self.rig.clearDirtyExpressionIndices(expression_indices)
        self.update_dirty_expressions()

    def clean_expressions(self, expression_names=None):
        dirty_expression_indices = self.rig.getDirtyExpressionIndices()
        dirty_expression_flags = self.rig.getDirtyExpressionFlags()

        if expression_names is not None:
            temp_dirty_expression_indices = []
            temp_dirty_expression_flags = []
            for expression_name in expression_names:
                try:
                    dirty_expression_index = dirty_expression_indices.index(self.expression_indices[expression_name])
                except ValueError:
                    continue
                temp_dirty_expression_indices.append(dirty_expression_indices[dirty_expression_index])
                temp_dirty_expression_flags.append(dirty_expression_flags[dirty_expression_index])
            dirty_expression_indices = temp_dirty_expression_indices
            dirty_expression_flags = temp_dirty_expression_flags

        expression_indices = []
        for expression_index, dirty_flags in zip(dirty_expression_indices, dirty_expression_flags):
            if not (dirty_flags >> 2) & 1:
                expression_indices.append(expression_index)
        if expression_indices:
            self.rig.clearDirtyExpressionIndices(expression_indices)

    def get_input_names(self):
        rmh = RigMayaHandler()
        inputs, _ = rmh.get_inputs(self.rig_definition)
        count_inputs = 0
        for input_ in inputs:
            if input_.type == PlugInputValue.TYPE_PLUG:
                count_inputs += 1
        temp_raw_control_names = [rigInput.get_full_name() for rigInput in inputs[:count_inputs]]
        raw_control_names = []
        psd_names = []
        for expName in [exp.name for exp in self.rig_definition.expressions if exp.assemble_to_rig]:
            try:
                exp = self.rig_definition.get_expression_by_name(expName)
            except ValueError as e:
                raise ValueError("Expression with pattern %s does not exist in rig definition" % expName) from e

            input_name = str(exp.expression_attrs[0] if exp else "")
            if input_name in temp_raw_control_names and input_name not in raw_control_names:
                raw_control_names.append(input_name)
            elif input_name not in temp_raw_control_names and input_name not in psd_names:
                psd_names.append(input_name)
        return raw_control_names + psd_names

    def get_joint_hierarchy_indices(self, joint_name):
        if joint_name not in self._joint_chain_indices:
            joint_chain_indices = []
            current_joint_index = self._joint_indices[joint_name]
            finished = False
            while not finished:
                joint_chain_indices.append(current_joint_index)
                if current_joint_index == self.dna_reader.getJointParentIndex(current_joint_index):
                    finished = True
                current_joint_index = self.dna_reader.getJointParentIndex(current_joint_index)
            self._joint_chain_indices[joint_name] = joint_chain_indices

        return self._joint_chain_indices[joint_name]

    @status_validator_dnacalib
    def _get_maya_joint_data(self, expression_name=None, phase=None):
        joints = {}
        parent_child_mapping: Dict[str, List[str]] = {}
        root_joint_name = None
        for jnt in self.rig_definition.joints.get_all_elements():
            name = jnt.name
            neutral_transformations = self.rig.getNeutralJoint(self._joint_indices[name])
            if jnt.parent is None:
                root_joint_name = jnt.name
            else:
                parent_name = jnt.parent.name
                if parent_name in parent_child_mapping:
                    parent_child_mapping[parent_name].append(name)
                else:
                    parent_child_mapping[parent_name] = [name]

            joint = [neutral_transformations[3:6]]

            if expression_name and phase is not None:
                transformations = self.rig.getJointAbsolute(
                    self.expression_indices[expression_name], phase - 1, self._joint_indices[name]
                )
                joint.extend([transformations[0:3], transformations[3:6], transformations[6:9]])
            else:
                joint.append(neutral_transformations[0:3])

            joint.append([jnt.override_color, jnt.override_enabled, jnt.radius])

            joints[name] = joint
        if root_joint_name:
            root_joint = RigDataHandler.create_joint(root_joint_name, joints, parent_child_mapping)
            return MayaJointDataHolder([root_joint]), joints
        raise FRTApiError("Root joint not found!")

    @staticmethod
    def create_joint(joint_name, joint_data, hierarchy_mapping):
        maya_joint = MayaJoint()
        maya_joint.name = joint_name
        maya_joint.translate[0] = joint_data[joint_name][1][0]
        maya_joint.translate[1] = joint_data[joint_name][1][1]
        maya_joint.translate[2] = joint_data[joint_name][1][2]
        maya_joint.rotate[0] = 0.0
        maya_joint.rotate[1] = 0.0
        maya_joint.rotate[2] = 0.0
        maya_joint.scale[0] = 1.0
        maya_joint.scale[1] = 1.0
        maya_joint.scale[2] = 1.0
        maya_joint.joint_orient[0] = joint_data[joint_name][0][0]
        maya_joint.joint_orient[1] = joint_data[joint_name][0][1]
        maya_joint.joint_orient[2] = joint_data[joint_name][0][2]
        maya_joint.override_color = joint_data[joint_name][-1][0]
        maya_joint.override_enabled = joint_data[joint_name][-1][1]
        maya_joint.radius = joint_data[joint_name][-1][2]
        try:
            for child_name in hierarchy_mapping[joint_name]:
                child_joint = RigDataHandler.create_joint(child_name, joint_data, hierarchy_mapping)
                child_joint.parent = maya_joint
                maya_joint.children.append(child_joint)
        except KeyError:
            pass
        return maya_joint

    @status_validator_dnacalib
    def get_neutral_joints(self):
        return self.rig.getNeutralJoints()

    @status_validator_dnacalib
    def get_neutral_joint(self, joint_name):
        try:
            return self.rig.getNeutralJoint(self._joint_indices[joint_name])
        except KeyError as e:
            raise FRTApiError(f"Joint {joint_name} doesn't exist in rig.") from e

    def get_neutral_joint_transformation_matrix(self, joint_name):
        joint_chain_indices = self.get_joint_hierarchy_indices(joint_name)

        neutral_joints = self.get_neutral_joints()

        neutral_joint_translations = []
        neutral_joint_rotations = []

        for i in range(0, len(neutral_joints), 9):
            neutral_joint_translations.append(neutral_joints[i : i + 3])
            neutral_joint_rotations.append(neutral_joints[i + 3 : i + 6])

        tm = om.MTransformationMatrix()
        tm.setTranslation(om.MVector(*neutral_joint_translations[joint_chain_indices[0]]), om.MSpace.kTransform)
        tm.setRotation(om.MEulerRotation(*[v * pi / 180 for v in neutral_joint_rotations[joint_chain_indices[0]]]))
        tm = om.MMatrix(tm.asMatrix())

        for index in joint_chain_indices[1:]:
            temp_tm = om.MTransformationMatrix()
            temp_tm.setTranslation(om.MVector(*neutral_joint_translations[index]), om.MSpace.kTransform)
            temp_tm.setRotation(om.MEulerRotation(*[v * pi / 180 for v in neutral_joint_rotations[index]]))
            temp_tm = om.MMatrix(temp_tm.asMatrix())
            tm *= temp_tm

        return tm

    def get_maya_neutral_joints(self):
        maya_joints, _ = self._get_maya_joint_data()
        return maya_joints

    @status_validator_dnacalib
    @calculate_sculpts
    def set_neutral_joints(self, joints):
        self.rig.setNeutralJoints(joints)
        self.update_dirty_expressions()

    @status_validator_dnacalib
    @calculate_sculpts
    def set_neutral_joint(self, joint_name, joint):
        self.rig.setNeutralJoint(self._joint_indices[joint_name], joint)
        self.update_dirty_expressions()

    @status_validator_dnacalib
    @calculate_sculpts
    def set_maya_neutral_joints(self):
        handler = JointMayaHandler()
        maya_joints = handler.get_joints_from_scene(self.rig_definition.joints)
        joints = []
        for maya_joint in maya_joints.get_all_elements():
            joints.extend(maya_joint.translate)
            joints.extend(maya_joint.joint_orient)
            joints.extend(maya_joint.scale)

        self.rig.setNeutralJoints(joints)
        self.update_dirty_expressions()

    @status_validator_dnacalib
    def get_expression_joints(self, expression_name, phase):
        return self.rig.getJointsAbsolute(self.expression_indices[expression_name], phase - 1)

    @status_validator_dnacalib
    def get_expression_joint(self, expression_name, phase, joint_name):
        return self.rig.getJointAbsolute(
            self.expression_indices[expression_name], phase - 1, self._joint_indices[joint_name]
        )

    def get_maya_expression_joints(self, expression_name, phase):
        maya_joints, joint_data = self._get_maya_joint_data(expression_name, phase)

        for index in maya_joints.get_all_element_ids():
            maya_joint = maya_joints.get_element(index)
            maya_joint.rotate[0] = joint_data[maya_joint.name][2][0]
            maya_joint.rotate[1] = joint_data[maya_joint.name][2][1]
            maya_joint.rotate[2] = joint_data[maya_joint.name][2][2]
            maya_joint.scale[0] = joint_data[maya_joint.name][3][0]
            maya_joint.scale[1] = joint_data[maya_joint.name][3][1]
            maya_joint.scale[2] = joint_data[maya_joint.name][3][2]

        return maya_joints

    @status_validator_dnacalib
    @calculate_sculpt
    def set_expression_joint(self, expression_name, phase, joint_name, joint):
        self.rig.setJointAbsolute(
            self.expression_indices[expression_name], phase - 1, self._joint_indices[joint_name], joint
        )
        self.update_dirty_expressions()

    @status_validator_dnacalib
    @calculate_sculpt
    def set_expression_joints(self, expression_name, phase, joints):
        self.rig.setJointsAbsolute(self.expression_indices[expression_name], phase - 1, joints)
        self.update_dirty_expressions()

    @status_validator_dnacalib
    @calculate_sculpt
    def set_maya_expression_joints(self, expression_name, phase):
        joints = []
        handler = JointMayaHandler()
        maya_joints = handler.get_joints_from_scene(self.rig_definition.joints)
        for maya_joint in maya_joints.get_all_elements():
            joints.extend(maya_joint.translate)
            joints.extend(maya_joint.rotate)
            joints.extend(maya_joint.scale)

        self.rig.setJointsAbsolute(self.expression_indices[expression_name], phase - 1, joints)
        self.update_dirty_expressions()

    def _get_geometry_base_mesh_name(self, mesh_name):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            geometry_base_mesh_name = self.rig_definition.get_geometry_base_mesh_name(mesh_name)
            if geometry_base_mesh_name is None:
                raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")
            mesh_name = geometry_base_mesh_name
        return mesh_name

    def get_texture_coordinates(self, mesh_name):
        mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        mesh_index = self.rig_definition.get_dna_mesh_names().index(mesh_name)

        texture_coordinates = []
        for texture_coordinate_index in range(self.dna_reader.getVertexTextureCoordinateCount(mesh_index)):
            u, v = self.dna_reader.getVertexTextureCoordinate(mesh_index, texture_coordinate_index)
            texture_coordinates.append((u, v))
        return texture_coordinates

    def get_mesh_layouts(self, mesh_name):
        mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        mesh_index = self.rig_definition.get_dna_mesh_names().index(mesh_name)

        layouts = []
        for layout_index in range(self.dna_reader.getVertexLayoutCount(mesh_index)):
            position_id, texture_coordinate_id, normal_id = self.dna_reader.getVertexLayout(mesh_index, layout_index)
            layouts.append((position_id, texture_coordinate_id, normal_id))
        return layouts

    def get_dna_faces(self, mesh_name):
        mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        mesh_index = self.rig_definition.get_dna_mesh_names().index(mesh_name)

        dna_faces = []
        for faceIndex in range(self.dna_reader.getFaceCount(mesh_index)):
            dna_faces.append(self.dna_reader.getFaceVertexLayoutIndices(mesh_index, faceIndex))
        return dna_faces

    @status_validator_dnacalib
    def get_mesh_vertex_count(self, mesh_name):
        mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        return self.rig.getVertexCount(self._mesh_indices[mesh_name])

    @status_validator_dnacalib
    def get_neutral_mesh_vertex_positions(self, mesh_name):
        mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        return self.rig.getNeutralMesh(self._mesh_indices[mesh_name])

    def get_selected_mesh(self):
        selected_meshes_in_scene = cmds.ls(sl=True)
        if not selected_meshes_in_scene or (selected_meshes_in_scene and len(selected_meshes_in_scene) != 1):
            raise RuntimeWarning("Exactly one mesh in scene has to be selected.")
        return selected_meshes_in_scene[0]

    def set_maya_neutral_mesh(self, mesh_name):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")

        selected_mesh_in_scene = self.get_selected_mesh()

        handler = MeshMayaHandler()
        vtx_positions = handler.get_mesh_vertex_positions(selected_mesh_in_scene)
        self.set_neutral_mesh(mesh_name, vtx_positions)

    @status_validator_dnacalib
    @calculate_sculpts
    def set_neutral_mesh(self, mesh_name, vtx_positions):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")
        self.rig.setNeutralMesh(self._mesh_indices[mesh_name], vtx_positions)
        self.update_dirty_expressions()

    @status_validator_dnacalib
    @calculate_sculpt
    def get_sculpt_mesh_vertex_positions(self, mesh_name, expression_name, phase):
        return self.rig.getSculpt(self.expression_indices[expression_name], phase - 1, self._mesh_indices[mesh_name])

    @status_validator_dnacalib
    def set_sculpt(self, mesh_name, expression_name, phase, vtx_positions):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")
        self.rig.setSculpt(
            self.expression_indices[expression_name],
            phase - 1,
            self._mesh_indices[mesh_name],
            vtx_positions,
        )
        self.update_dirty_expressions()

    @status_validator_dnacalib
    def get_cbs_mesh_vertex_positions(self, mesh_name, expression_name, phase):
        rig_vertex_positions = self.rig.getNeutralMesh(self._mesh_indices[mesh_name])
        vertices = self.rig.getCorrectiveBlendShapeVertexIndices(
            self.expression_indices[expression_name], phase - 1, self._mesh_indices[mesh_name]
        )
        deltas = self.rig.getCorrectiveBlendShapeDeltas(
            self.expression_indices[expression_name], phase - 1, self._mesh_indices[mesh_name]
        )
        for vertex, delta in zip(vertices, deltas):
            rig_vertex_positions[vertex][0] += delta[0]
            rig_vertex_positions[vertex][1] += delta[1]
            rig_vertex_positions[vertex][2] += delta[2]
        return rig_vertex_positions

    @status_validator_dnacalib
    @calculate_sculpt
    def set_corrective_blend_shape(self, mesh_name, expression_name, phase, vtx_positions):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")
        neutral_vtx_positions = self.get_neutral_mesh_vertex_positions(mesh_name)
        delta_values = []
        delta_indices = []

        for index, (vtx_position, neutral_position) in enumerate(zip(vtx_positions, neutral_vtx_positions)):
            delta = [
                vtx_position[0] - neutral_position[0],
                vtx_position[1] - neutral_position[1],
                vtx_position[2] - neutral_position[2],
            ]
            if any(delta):
                delta_values.append(delta)
                delta_indices.append(index)

        # TODO - to be removed when PyDNACalib2 wrapper is fixed
        if not (delta_values or delta_indices):
            delta_values = [[0.0, 0.0, 0.0]]
            delta_indices = [0]

        self.rig.setCorrectiveBlendShape(
            self.expression_indices[expression_name],
            phase - 1,
            self._mesh_indices[mesh_name],
            delta_indices,
            delta_values,
        )
        self.update_dirty_expressions()

    def get_neutral_mesh_topology(self, mesh_name):
        if mesh_name in self._neutral_mesh_topology:
            return self._neutral_mesh_topology[mesh_name]
        mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        mesh_index = self.rig_definition.get_dna_mesh_names().index(mesh_name)

        dna_faces = []
        for faceIndex in range(self.dna_reader.getFaceCount(mesh_index)):
            dna_faces.append(self.dna_reader.getFaceVertexLayoutIndices(mesh_index, faceIndex))

        layouts = []
        for layout_index in range(self.dna_reader.getVertexLayoutCount(mesh_index)):
            position_id, _, _ = self.dna_reader.getVertexLayout(mesh_index, layout_index)
            layouts.append(position_id)

        faces = []
        edges = []
        for vertex_layout_index_array in dna_faces:
            faces.append(len(vertex_layout_index_array))
            for vertex_layout_index in vertex_layout_index_array:
                edges.append(layouts[vertex_layout_index])

        self._neutral_mesh_topology[mesh_name] = (faces, edges)
        return faces, edges

    def get_derived_skin_weights(self, mesh_name):
        """
        A recursive method which calculates and caches the skinning of meshes that are not part of the DNA file.

        :param mesh_name: Name of the mesh for which the skinning is calculated.
        :return: A list with two elements, where the first element are the joint indices per vertex, and the second
        the influence values per vertex.
        """
        skinning_data: Optional[SkinningData] = self.rig_definition.get_skinning_data(mesh_name)
        if skinning_data:
            return skinning_data

        base_mesh_name = self.rig_definition.get_skinning_base_mesh_name(mesh_name)
        try:
            skinning_data = self.get_skin_weights(base_mesh_name)
        except MeshNotFoundError:
            skinning_data = self.get_derived_skin_weights(base_mesh_name)
        assert skinning_data is not None
        self.rig_definition.set_skinning_data(mesh_name, skinning_data)

        # Transform skinning if necessary using the data from the rig definition.
        mapping = self.rig_definition.get_skinning_joint_mapping(mesh_name)
        if mapping:
            joint_names = [joint.name for joint in self.rig_definition.joints.get_all_elements()]
            mapping_indices = {
                joint_names.index(key): [joint_names.index(value) for value in values]
                for key, values in mapping.items()
                if values
            }

            inverse_mapping_indices = {value: key for key, values in mapping_indices.items() for value in values}

            new_skinning_data = SkinningData()
            for joint_indices, weights in zip(skinning_data.joint_indices, skinning_data.weights):
                new_joint_indices: List[int] = []
                new_weights: List[float] = []
                for joint_index, weight in zip(joint_indices, weights):
                    if joint_index in inverse_mapping_indices:
                        if inverse_mapping_indices[joint_index] in new_joint_indices:
                            new_weights[new_joint_indices.index(inverse_mapping_indices[joint_index])] += weight
                        else:
                            new_joint_indices.append(inverse_mapping_indices[joint_index])
                            new_weights.append(weight)
                    else:
                        if joint_index in new_joint_indices:
                            new_weights[new_joint_indices.index(joint_index)] += weight
                        else:
                            new_joint_indices.append(joint_index)
                            new_weights.append(weight)
                new_skinning_data.joint_indices.append(new_joint_indices)
                new_skinning_data.weights.append(new_weights)

            self.rig_definition.set_skinning_data(mesh_name, new_skinning_data)
            return new_skinning_data

        return skinning_data

    @status_validator_dnacalib
    def get_skin_weights(self, mesh_name):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            if not self.rig_definition.get_skinning_base_mesh_name(mesh_name):
                raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")
            return self.get_derived_skin_weights(mesh_name)

        skinning_data = SkinningData()
        for i in range(self.rig.getVertexCount(self._mesh_indices[mesh_name])):
            weights = self.rig.getSkinWeightValues(self._mesh_indices[mesh_name], i)
            skinning_data.weights.append(weights)
            joint_indices = self.rig.getSkinWeightJointIndices(self._mesh_indices[mesh_name], i)
            skinning_data.joint_indices.append(joint_indices)

        return skinning_data

    def get_maya_skin_weights(self, mesh_name):
        geometry_mesh_name = self._get_geometry_base_mesh_name(mesh_name)
        mesh_index = self.rig_definition.get_dna_mesh_names().index(geometry_mesh_name)
        joint_names = [jnt.name for jnt in self.rig_definition.joints.get_all_elements()]

        maya_skin_weights = MayaSkinWeights()
        maya_skin_weights.no_of_influences = self.dna_reader.getMaximumInfluencePerVertex(mesh_index)

        skinning_data = self.get_skin_weights(mesh_name)

        joints = list({joint_id for joint_indices in skinning_data.joint_indices for joint_id in joint_indices})
        joints.sort()
        maya_skin_weights.joints = [joint_names[i] for i in joints]

        for joint_indices, weights in zip(skinning_data.joint_indices, skinning_data.weights):
            vertex_info = []
            for joint_id, weight in zip(joint_indices, weights):
                vertex_info.append(maya_skin_weights.joints.index(joint_names[joint_id]))
                vertex_info.append(weight)
            maya_skin_weights.vertices_info.append(vertex_info)

        return maya_skin_weights

    @status_validator_dnacalib
    @calculate_sculpts
    def set_skin_weights(self, mesh_name, skin_weights):
        if mesh_name not in self.rig_definition.get_dna_mesh_names():
            raise MeshNotFoundError(f"Mesh {mesh_name} doesn't exist in the DNA file.")
        joint_names = [jnt.name for jnt in self.rig_definition.joints.get_all_elements()]
        for vtx_id, vtx_info in enumerate(skin_weights.vertices_info):
            joint_ids = [joint_names.index(skin_weights.joints[vtx_info[i]]) for i in range(0, len(vtx_info), 2)]
            weights = [vtx_info[i] for i in range(1, len(vtx_info), 2)]
            self.rig.setSkinWeightJointIndices(self._mesh_indices[mesh_name], vtx_id, joint_ids)
            self.rig.setSkinWeightValues(self._mesh_indices[mesh_name], vtx_id, weights)

        self.update_dirty_expressions()
        self.rig_definition.clear_derived_skin_weights(mesh_name)

    def get_animated_map_curves(self, expression):
        try:
            ctrl_name = str(expression.expression_attrs[0])
        except IndexError:
            return {}

        input_names = self.get_input_names()

        inputs = self.dna_reader.getAnimatedMapInputIndices()
        from_values = self.dna_reader.getAnimatedMapFromValues()
        to_values = self.dna_reader.getAnimatedMapToValues()
        slope_values = self.dna_reader.getAnimatedMapSlopeValues()
        cut_values = self.dna_reader.getAnimatedMapCutValues()

        rows = []
        for i, input_ in enumerate(inputs):
            if input_names[input_] == ctrl_name:
                rows.append((from_values[i], to_values[i], slope_values[i], cut_values[i]))

        all_points = []
        for row in rows:
            all_points.append([(row[0] * 40, 0.0), (row[1] * 40, row[1] * row[2] + row[3])])

        anim_curves_list = []
        for map_in_expression in expression.maps_in_expression:
            for i, mask in enumerate(map_in_expression.masks):
                obj_name = f"multiplyCtrl_{expression.name}_{map_in_expression.map.name}_{mask.name}"
                for attr_name in ["input2X", "input2Y", "input2Z"]:
                    curve = MayaAnimCurve()
                    curve.meaning = MayaAnimCurve.MEANING_MASK
                    curve.anim_curve_type = "TU"
                    output = MayaAnimCurveAttribute(obj_name, attr_name)
                    curve.outputs.append(output)

                    for point in all_points[i]:
                        key = MayaAnimCurveKey()
                        key.time = point[0]
                        key.value = point[1]
                        curve.keys.append(key)

                    anim_curves_list.append(curve)

        anim_curves_dict = {}
        for ac in anim_curves_list:
            for output in ac.outputs:
                anim_curves_dict[f"{output.obj_name}.{output.attr_name}"] = ac
        return anim_curves_dict

    def save_rig_data_as_dna(self, dna_file_path: str) -> bool:
        saved: bool = DNAFileHandler.save_dna(self, dna_file_path)
        return saved

    @status_validator_dnacalib
    def is_rig_dirty(self) -> bool:
        if self.rig.getDirtyExpressionIndices():
            return True
        return False
