# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

import struct
from typing import List

import rdf as rdflib

from ..utils import get_logger
from ..version import fileformat_version
from ..exceptions import InvalidIndexException
from ..model.items import (
    LOD,
    Face,
    Mesh,
    Joint,
    Swing,
    Twist,
    PSDNet,
    Region,
    Shader,
    Control,
    RBFPose,
    SplitMap,
    Direction,
    MixRegion,
    RBFSolver,
    Descriptor,
    Expression,
    GUIControl,
    JointGroup,
    ShaderType,
    TextureMap,
    AnimatedMap,
    ControlType,
    JointWeight,
    ShaderInput,
    SplitJoints,
    TextureMask,
    MeshDeformer,
    RotationUnit,
    SkinTransfer,
    SymmetryMesh,
    SymmetrySide,
    PSDDefinition,
    RBFInputJoint,
    RBFSolverType,
    SymmetryJoint,
    ControlMapping,
    ExpressionType,
    TextureMapType,
    DeformationType,
    RBFFunctionType,
    ShaderParameter,
    TranslationUnit,
    CoordinateSystem,
    RBFDistanceMethod,
    AnimatedMapChannel,
    JointAttributeType,
    SkinTransferMapping,
    ExpressionMultiplier,
    SumExpressionFunction,
    ExpressionFunctionType,
    PhaseExpressionFunction,
    SplitExpressionFunction,
    SubtractExpressionFunction,
    JointAttributeRepresentation,
    NoOperationExpressionFunction,
)
from ..model.definition import RigDefinition

logger = get_logger()


class RDFReader:
    def __init__(self, rdf_path: str, rig_definition: RigDefinition) -> None:
        self._rdf_path = rdf_path
        self._rig_definition = rig_definition
        self._reader: rdflib.RigDefinitionBinaryStreamReader = None

        self._shader_parameters: List[ShaderParameter] = []
        self._shader_inputs: List[ShaderInput] = []
        self._animated_maps: List[AnimatedMap] = []
        self._split_joints: List[SplitJoints] = []
        self._split_functions: List[SplitExpressionFunction] = []
        self._subtract_functions: List[SubtractExpressionFunction] = []
        self._sum_functions: List[SumExpressionFunction] = []
        self._phase_functions: List[PhaseExpressionFunction] = []

    def get_reader(self) -> rdflib.RigDefinitionBinaryStreamReader:
        return self._reader

    def _get_shader_parameter(self, index: int) -> ShaderParameter:
        if index < 0 or index >= len(self._shader_parameters):
            raise InvalidIndexException("ShaderParameter", index)
        return self._shader_parameters[index]

    def _get_shader_input(self, index: int) -> ShaderInput:
        if index < 0 or index >= len(self._shader_inputs):
            raise InvalidIndexException("ShaderInput", index)
        return self._shader_inputs[index]

    def _get_animated_map(self, index: int) -> AnimatedMap:
        if index < 0 or index >= len(self._animated_maps):
            raise InvalidIndexException("AnimatedMap", index)
        return self._animated_maps[index]

    def _get_split_joints(self, index: int) -> SplitJoints:
        if index < 0 or index >= len(self._split_joints):
            raise InvalidIndexException("SplitJoints", index)
        return self._split_joints[index]

    def _get_split_function(self, index: int) -> SplitExpressionFunction:
        if index < 0 or index >= len(self._split_functions):
            raise InvalidIndexException("SplitExpressionFunction", index)
        return self._split_functions[index]

    def _get_subtract_function(self, index: int) -> SubtractExpressionFunction:
        if index < 0 or index >= len(self._subtract_functions):
            raise InvalidIndexException("SubtractExpressionFunction", index)
        return self._subtract_functions[index]

    def _get_sum_function(self, index: int) -> SumExpressionFunction:
        if index < 0 or index >= len(self._sum_functions):
            raise InvalidIndexException("SumExpressionFunction", index)
        return self._sum_functions[index]

    def _get_phase_function(self, index: int) -> PhaseExpressionFunction:
        if index < 0 or index >= len(self._phase_functions):
            raise InvalidIndexException("PhaseExpressionFunction", index)
        return self._phase_functions[index]

    def _open_reader(self) -> None:
        if not self._rdf_path:
            raise Exception("No RDF file path defined.")

        ver = read_fileformat_version(self._rdf_path)
        if ver != fileformat_version:
            raise ValueError(f"File format version mismatched, expected {fileformat_version}, got {ver}")

        stream = rdflib.FileStream(
            self._rdf_path,
            rdflib.FileStream.AccessMode_Read,
            rdflib.FileStream.OpenMode_Binary,
        )
        self._reader = rdflib.RigDefinitionBinaryStreamReader(stream)
        self._reader.read()
        if not rdflib.Status_isOk():
            message = rdflib.Status_get().message
            raise Exception(message)
        logger.debug(f"RDF reader created: {self._rdf_path}")

    def read(self) -> RigDefinition:
        logger.info("rdf reader - start.")
        self._open_reader()

        self._read_descriptor()
        self._read_controls()
        self._read_joints()
        self._read_animated_map_channels()
        self._read_joint_groups()
        self._read_regions()
        self._read_textures()
        self._read_shaders()
        self._read_meshes()
        self._read_split_joints()
        self._read_split_maps()
        self._read_animated_maps()
        self._read_expressions()
        self._read_functions()
        self._read_expression_functions()
        self._read_psd_definitions()
        self._read_psd_nets()
        self._read_lods()
        self._read_mix_regions()
        self._read_symmetry()
        self._read_rbf_poses()
        self._read_rbf_solvers()
        self._read_twists()
        self._read_swings()
        self._read_skin_transfers()
        logger.info("rdf reader - end.")
        return self._rig_definition

    def _read_descriptor(self) -> None:
        r = self._reader
        logger.debug("Reading descriptor.")

        translation_unit = TranslationUnit(r.getTranslationUnit())
        rotation_unit = RotationUnit(r.getRotationUnit())
        x_axis = Direction(r.getCoordinateSystem().xAxis)
        y_axis = Direction(r.getCoordinateSystem().yAxis)
        z_axis = Direction(r.getCoordinateSystem().zAxis)
        coordinate_system = CoordinateSystem(x_axis, y_axis, z_axis)
        db_complexity = r.getDBComplexity()
        db_name = r.getDBName()

        descriptor = Descriptor(
            translation_unit,
            rotation_unit,
            coordinate_system,
            db_complexity,
            db_name,
        )

        self._rig_definition.descriptor = descriptor
        logger.debug(descriptor)

    def _read_controls(self) -> None:
        r = self._reader
        logger.debug("Reading controls.")

        # gui controls
        for index in range(r.getGUIControlCount()):
            name = r.getGUIControlName(index)
            from_value = r.getGUIControlFromValue(index)
            to_value = r.getGUIControlToValue(index)
            gui_control = GUIControl(name, from_value, to_value)
            gui_control.index = index
            self._rig_definition.add_gui_control(gui_control)
            logger.debug(gui_control)

        # controls
        for index in range(r.getControlCount()):
            name = r.getControlName(index)
            ctrl_type = ControlType(r.getControlType(index))
            is_exported = r.getControlExportedToRig(index)
            from_value = r.getControlFromValue(index)
            to_value = r.getControlToValue(index)
            control = Control(name, from_value, to_value, ctrl_type, is_exported)
            control.index = index
            self._rig_definition.add_control(control)
            logger.debug(control)

        # gui to raw
        for index in range(r.getGUIToRawCount()):
            in_control = self._rig_definition.gui_controls.at(r.getGUIToRawInputIndex(index))
            out_control = self._rig_definition.controls.at(r.getGUIToRawOutputIndex(index))
            from_value = r.getGUIToRawFromValue(index)
            to_value = r.getGUIToRawToValue(index)
            slope_value = r.getGUIToRawSlopeValue(index)
            cut_value = r.getGUIToRawCutValue(index)
            control_mapping = ControlMapping(in_control, out_control, from_value, to_value, slope_value, cut_value)
            control_mapping.index = index
            self._rig_definition.add_gui_to_raw(control_mapping)
            logger.debug(control_mapping)

    def _read_joints(self) -> None:
        r = self._reader
        logger.debug("Reading joints.")
        for index in range(r.getJointCount()):
            name = r.getJointName(index)
            color = r.getJointColor(index)
            radius = r.getJointRadius(index)
            joint = Joint(name, None, color, radius)
            joint.index = index
            self._rig_definition.add_joint(joint)

        # hierarchy
        for i, parent_i in enumerate(r.getJointHierarchy()):
            joint = self._rig_definition.joints.at(i)
            if i != parent_i:
                parent = self._rig_definition.joints.at(parent_i)
                joint.parent = parent
            logger.debug(joint)

    def _read_animated_map_channels(self) -> None:
        pass

    def _read_joint_groups(self) -> None:
        r = self._reader
        logger.debug("Reading joint groups.")
        for index in range(r.getJointGroupCount()):
            name = r.getJointGroupName(index)
            joint_group = JointGroup(name)
            for i in r.getJointGroupJointIndices(index):
                joint = self._rig_definition.joints.at(i)
                joint_group.add_joint(joint)
            joint_group.index = index
            self._rig_definition.add_joint_group(joint_group)
            logger.debug(joint_group)

    def _read_regions(self) -> None:
        r = self._reader
        logger.debug("Reading regions.")
        for index in range(r.getRegionCount()):
            name = r.getRegionName(index)
            region = Region(name)
            for i in r.getRegionJointIndices(index):
                joint = self._rig_definition.joints.at(i)
                region.add_joint(joint)
            region.index = index
            self._rig_definition.add_region(region)
            logger.debug(region)

    def _read_textures(self) -> None:
        r = self._reader
        # texture masks
        logger.debug("Reading texture masks.")
        for index in range(r.getTextureMaskCount()):
            name = r.getTextureMaskName(index)
            texture_mask = TextureMask(name)
            texture_mask.index = index
            self._rig_definition.add_texture_mask(texture_mask)
            logger.debug(texture_mask)

        # texture map types
        logger.debug("Reading texture map types.")
        for index in range(r.getTextureMapTypeCount()):
            name = r.getTextureMapTypeName(index)
            texture_map_type = TextureMapType(name)
            texture_map_type.index = index
            self._rig_definition.add_texture_map_type(texture_map_type)
            logger.debug(texture_map_type)

        # texture maps
        logger.debug("Reading texture maps.")
        for index in range(r.getTextureMapCount()):
            name = r.getTextureMapName(index)
            map_type = self._rig_definition.texture_map_types.at(r.getTextureMapTypeIndex(index))
            is_base = r.getTextureMapBase(index)
            texture_map = TextureMap(name, map_type, is_base)
            texture_map.index = index
            self._rig_definition.add_texture_map(texture_map)
            logger.debug(texture_map)

    def _read_shaders(self) -> None:
        r = self._reader
        logger.debug("Reading shaders.")

        # shader parameters
        for index in range(r.getShaderParameterCount()):
            name = r.getShaderParameterName(index)
            value = r.getShaderParameterValue(index)
            shader_parameter = ShaderParameter(name, value)
            shader_parameter.index = index
            self._shader_parameters.append(shader_parameter)
            logger.debug(shader_parameter)

        # shader inputs
        for index in range(r.getShaderInputCount()):
            name = r.getShaderInputName(index)
            texture_map_type = self._rig_definition.texture_map_types.at(r.getShaderInputTextureMapTypeIndex(index))
            shader_input = ShaderInput(name, texture_map_type)
            shader_input.index = index
            self._shader_inputs.append(shader_input)
            logger.debug(shader_input)

        # shader
        for index in range(r.getShaderCount()):
            name = r.getShaderName(index)
            shader_type = ShaderType(r.getShaderType(index))
            shader = Shader(name, shader_type)
            for i in r.getShaderParameterIndices(index):
                shader_parameter = self._get_shader_parameter(i)
                shader.add_parameter(shader_parameter)
            for i in r.getShaderInputIndices(index):
                shader_input = self._get_shader_input(i)
                shader.add_input(shader_input)
            shader.index = index
            self._rig_definition.add_shader(shader)
            logger.debug(shader)

    def _read_meshes(self) -> None:
        r = self._reader
        logger.debug("Reading meshes.")
        for index in range(r.getMeshCount()):
            name = r.getMeshName(index)
            shader = self._rig_definition.shaders.at(r.getMeshShaderIndex(index))
            is_exported = r.getMeshExportedToRig(index)
            vertex_count = r.getMeshVertexCount(index)
            uv_count = r.getMeshUVCount(index)
            face_count = r.getMeshFaceCount(index)
            faces = []
            for i in range(face_count):
                face = Face(r.getMeshFaceVertexIndices(index, i))
                face.index = i
                faces.append(face)
            ipv_count = r.getMeshMaximumInfluencePerVertex(index)
            bs_count = r.getMeshBlendShapeChannelCount(index)
            mesh = Mesh(
                name,
                shader,
                is_exported,
                vertex_count,
                uv_count,
                faces,
                ipv_count,
                bs_count,
            )
            mesh.index = index
            self._rig_definition.add_mesh(mesh)
            logger.debug(mesh)

    def _read_split_joints(self) -> None:
        r = self._reader
        logger.debug("Reading split joints.")
        for index in range(r.getSplitJointsCount()):
            joint_group = self._rig_definition.joint_groups.at(r.getSplitJointsJointGroupIndex(index))
            multiplier = r.getSplitJointsMultiplier(index)
            rotation = r.getSplitJointsRotation(index)
            split_joint = SplitJoints(joint_group, multiplier, rotation)
            split_joint.index = index
            self._split_joints.append(split_joint)
            logger.debug(split_joint)

    def _read_split_maps(self) -> None:
        r = self._reader
        logger.debug("Reading split maps.")
        for index in range(r.getSplitMapCount()):
            name = r.getSplitMapName(index)
            mesh = self._rig_definition.meshes.at(r.getSplitMapMeshIndex(index))
            weights = r.getSplitMapWeights(index)
            split_map = SplitMap(name, mesh, weights)
            split_map.index = index
            self._rig_definition.add_split_map(split_map)
            logger.debug(split_map)

    def _read_animated_maps(self) -> None:
        r = self._reader
        logger.debug("Reading animated maps.")
        for index in range(r.getAnimatedMapCount()):
            texture_map = self._rig_definition.texture_maps.at(r.getAnimatedMapTextureMapIndex(index))
            animated_map = AnimatedMap(texture_map)
            for i in r.getAnimatedMapTextureMaskIndices(index):
                texture_mask = self._rig_definition.texture_masks.at(i)
                animated_map.add_texture_mask(texture_mask)

                # animated map channel
                am_name = AnimatedMapChannel.format_name(texture_map.name, texture_mask.name)
                am_channel = self._rig_definition.animated_map_channels.get(am_name)
                if am_channel is None:
                    am_channel = AnimatedMapChannel(texture_map.name, texture_mask.name)
                    self._rig_definition.add_animated_map_channel(am_channel)
                animated_map.add_animated_map_channel(am_channel)
            animated_map.index = index
            self._animated_maps.append(animated_map)
            logger.debug(animated_map)

    def _read_expressions(self) -> None:
        r = self._reader
        logger.debug("Reading expressions.")

        expressions = []
        # expressions
        for index in range(r.getExpressionCount()):
            # base expression
            name = r.getExpressionName(index)
            exp_type = ExpressionType(r.getExpressionType(index))
            is_exported = r.getExpressionExportedToRig(index)
            phase_count = r.getExpressionPhaseCount(index)
            expression = Expression(name, exp_type, is_exported, phase_count)
            expression.index = index

            # control
            ctrl_index = r.getExpressionControlIndex(index)
            if ctrl_index != Control.NO_CONTROL:
                ctrl = self._rig_definition.controls.at(ctrl_index)
                expression.set_control(ctrl)

            # mesh deformers
            mesh_indices = r.getExpressionMeshIndices(index)
            def_types = r.getExpressionMeshDeformationTypes(index)
            for i, mesh_i in enumerate(mesh_indices):
                mesh = self._rig_definition.meshes.at(mesh_i)
                deformation_type = DeformationType(def_types[i])
                mesh_deformer = MeshDeformer(mesh, deformation_type)
                expression.add_mesh_deformer(mesh_deformer)

            # animated maps
            for i in r.getExpressionAnimatedMapIndices(index):
                animated_map = self._get_animated_map(i)
                expression.add_animated_map(animated_map)

            # regions
            for i in r.getExpressionRegionIndices(index):
                region = self._rig_definition.regions.at(i)
                expression.add_region(region)

            expressions.append(expression)
            logger.debug(expression)
        self._rig_definition.add_expressions(expressions)

    def _read_functions(self) -> None:
        r = self._reader
        # split functions
        logger.debug("Reading split functions.")
        for index in range(r.getSplitExpressionFunctionCount()):
            exp = self._rig_definition.expressions.at(r.getSplitExpressionFunctionSourceExpressionIndex(index))
            split_func = SplitExpressionFunction(exp)
            # split maps
            for i in r.getSplitExpressionFunctionSplitMapIndices(index):
                split_map = self._rig_definition.split_maps.at(i)
                split_func.add_split_map(split_map)
            # split joints
            for i in r.getSplitExpressionFunctionSplitJointsIndices(index):
                split_joints = self._get_split_joints(i)
                split_func.add_split_joint(split_joints)
            split_func.index = index
            self._split_functions.append(split_func)
            logger.debug(split_func)

        # subtract functions
        logger.debug("Reading subtract functions.")
        for index in range(r.getSubtractExpressionFunctionCount()):
            exp_1 = self._rig_definition.expressions.at(r.getSubtractExpressionFunctionMinuendExpressionIndex(index))
            exp_2 = self._rig_definition.expressions.at(r.getSubtractExpressionFunctionSubtrahendExpressionIndex(index))
            multiplier_1 = r.getSubtractExpressionFunctionMinuendMultiplier(index)
            multiplier_2 = r.getSubtractExpressionFunctionSubtrahendMultiplier(index)
            sub_func = SubtractExpressionFunction(
                ExpressionMultiplier(exp_1, multiplier_1),
                ExpressionMultiplier(exp_2, multiplier_2),
            )
            sub_func.index = index
            self._subtract_functions.append(sub_func)
            logger.debug(sub_func)

        # sum functions
        logger.debug("Reading sum functions.")
        for index in range(r.getSumExpressionFunctionCount()):
            sum_func = SumExpressionFunction()
            exp_indices = r.getSumExpressionFunctionExpressionIndices(index)
            multipliers = r.getSumExpressionFunctionMultipliers(index)
            for i, exp_i in enumerate(exp_indices):
                exp = self._rig_definition.expressions.at(exp_i)
                exp_multiplier = ExpressionMultiplier(exp, multipliers[i])
                sum_func.add_element(exp_multiplier)
            sum_func.index = index
            self._sum_functions.append(sum_func)
            logger.debug(sum_func)

        # phase functions
        logger.debug("Reading phase functions.")
        for index in range(r.getPhaseExpressionFunctionCount()):
            exp = self._rig_definition.expressions.at(r.getPhaseExpressionFunctionSourceExpressionIndex(index))
            phase_number = r.getPhaseExpressionFunctionSourceExpressionPhase(index)
            phase_func = PhaseExpressionFunction(exp, phase_number)
            phase_func.index = index
            self._phase_functions.append(phase_func)
            logger.debug(phase_func)

    def _read_expression_functions(self) -> None:
        r = self._reader
        logger.debug("Reading expression functions.")
        for index in range(r.getExpressionCount()):
            expression = self._rig_definition.expressions.at(index)
            fn_index = r.getExpressionFunctionIndex(index)
            fn_type = ExpressionFunctionType(r.getExpressionFunctionType(index))
            if fn_type == ExpressionFunctionType.Split:
                expression.function = self._get_split_function(fn_index)  # type: ignore
            if fn_type == ExpressionFunctionType.Subtract:
                expression.function = self._get_subtract_function(fn_index)  # type: ignore
            if fn_type == ExpressionFunctionType.Sum:
                expression.function = self._get_sum_function(fn_index)  # type: ignore
            if fn_type == ExpressionFunctionType.Phase:
                expression.function = self._get_phase_function(fn_index)  # type: ignore
            if fn_type == ExpressionFunctionType.NoOperation:
                expression.function = NoOperationExpressionFunction()

    def _read_psd_definitions(self) -> None:
        r = self._reader
        logger.debug("Reading psd definitions.")
        for index in range(r.getPSDDefinitionCount()):
            name = r.getPSDDefinitionName(index)
            layer = r.getPSDDefinitionLayer(index)
            complex_expr = self._rig_definition.expressions.at(r.getPSDDefinitionComplexExpressionIndex(index))
            target = self._rig_definition.expressions.at(r.getPSDDefinitionTargetExpressionIndex(index))
            corrective = self._rig_definition.expressions.at(r.getPSDDefinitionCorrectiveExpressionIndex(index))
            psd_definition = PSDDefinition(name, layer, complex_expr, target, corrective)
            psd_definition.index = index
            self._rig_definition.add_psd_definition(psd_definition)
            logger.debug(psd_definition)

    def _read_psd_nets(self) -> None:
        r = self._reader
        logger.debug("Reading psd nets.")
        for index in range(r.getPSDNetCount()):
            name = r.getPSDNetName(index)
            psd_net = PSDNet(name)
            in_indices = r.getPSDNetInputExpressionIndices(index)
            values = r.getPSDNetValues(index)
            for i, exp_i in enumerate(in_indices):
                exp = self._rig_definition.expressions.at(exp_i)
                psd_net_input = ExpressionMultiplier(exp, values[i])
                psd_net.add_input(psd_net_input)
            psd_net.output_expression = self._rig_definition.expressions.at(r.getPSDNetOutputExpressionIndex(index))
            psd_net.psd_definition = self._rig_definition.psd_definitions.at(r.getPSDNetPSDDefinitionIndex(index))
            psd_net.index = index
            self._rig_definition.add_psd_net(psd_net)
            logger.debug(psd_net)

    def _read_lods(self) -> None:
        r = self._reader
        logger.debug("Reading lods.")
        for index in range(r.getLODCount()):
            lod = LOD(index)
            for i in r.getLODPSDNetIndices(index):
                lod.add_psd_net(self._rig_definition.psd_nets.at(i))
            for i in r.getLODJointIndices(index):
                lod.add_joint(self._rig_definition.joints.at(i))
            for i in r.getLODAnimatedMapChannelIndices(index):
                lod.add_animated_map_channel(self._rig_definition.animated_map_channels.at(i))
            for i in r.getLODMeshIndices(index):
                lod.add_mesh(self._rig_definition.meshes.at(i))
            if r.getLODBlendShapeChannelIndices(index):
                lod.set_blend_shape_channels(self._rig_definition.get_blend_shape_channels_by_exported(lod))
            lod.index = index
            self._rig_definition.add_lod(lod)
            logger.debug(lod)

    def _read_mix_regions(self) -> None:
        r = self._reader
        logger.debug("Reading mix regions.")
        for index in range(r.getMixRegionCount()):
            name = r.getMixRegionName(index)
            mix_region = MixRegion(name)
            jnt_indices = r.getMixRegionJointIndices(index)
            jnt_weights = r.getMixRegionJointWeights(index)
            for i, jnt_i in enumerate(jnt_indices):
                joint = self._rig_definition.joints.at(jnt_i)
                joint_weight = JointWeight(joint, jnt_weights[i])
                mix_region.add_joint_weight(joint_weight)
            for i in r.getMixRegionSplitMapIndices(index):
                split_map = self._rig_definition.split_maps.at(i)
                mix_region.add_split_map(split_map)
            mix_region.index = index
            self._rig_definition.add_mix_region(mix_region)
            logger.debug(mix_region)

    def _read_symmetry(self) -> None:
        r = self._reader
        logger.debug("Reading symmetry.")

        # symmetry joints
        mapping = r.getSymmetryJointMappings()
        sides = r.getSymmetryJointSides()
        for i, pair_i in enumerate(mapping):
            joint = self._rig_definition.joints.at(i)
            symmetry_joint = SymmetryJoint(joint)
            symmetry_joint.side = SymmetrySide(sides[i])
            if symmetry_joint.side in (SymmetrySide.Left, SymmetrySide.Right):
                pair = self._rig_definition.joints.at(pair_i)
                symmetry_joint.pair = pair
            self._rig_definition.add_symmetry_joint(symmetry_joint)
            logger.debug(symmetry_joint)

        # symmetry meshes
        for index in range(r.getSymmetryMeshCount()):
            mesh = self._rig_definition.meshes.at(r.getSymmetryMeshMeshIndex(index))
            mapping = r.getSymmetryMeshVertexMappings(index)
            sides = []
            for s in r.getSymmetryMeshVertexSides(index):
                sides.append(SymmetrySide(s))
            symmetry_mesh = SymmetryMesh(mesh.name, mesh, mapping, sides)
            symmetry_mesh.index = index
            self._rig_definition.add_symmetry_mesh(symmetry_mesh)
            logger.debug(symmetry_mesh)

    def _read_rbf_poses(self) -> None:
        r = self._reader
        logger.debug("Reading rbf poses.")

        for index in range(r.getRBFPoseCount()):
            pose = RBFPose(r.getRBFPoseName(index))
            for rc_i in r.getRBFPoseInputRawControlIndices(index):
                pose.add_input_control(self._rig_definition.controls.at(rc_i))
            for oe_i in r.getRBFPoseOutputExpressionIndices(index):
                pose.add_output_expression(self._rig_definition.expressions.at(oe_i))

            self._rig_definition.add_rbf_pose(pose)
            logger.debug(pose)

    def _read_rbf_solvers(self) -> None:
        r = self._reader
        logger.debug("Reading rbf solvers.")

        for index in range(r.getRBFSolverCount()):
            solver = RBFSolver(r.getRBFSolverName(index))
            solver.distance_method = RBFDistanceMethod(r.getRBFSolverDistanceMethod(index))
            solver.function_type = RBFFunctionType(r.getRBFSolverFunctionType(index))
            solver.solver_type = RBFSolverType(r.getRBFSolverType(index))
            jnt_indices = r.getRBFSolverInputJointIndices(index)
            jnt_attr_types = r.getRBFSolverInputJointAttributes(index)
            jnt_attr_reps = r.getRBFSolverInputJointAttributeRepresentations(index)
            for jnt_i, jnt_attr_type, jnt_attr_rep in zip(jnt_indices, jnt_attr_types, jnt_attr_reps):
                jnt = self._rig_definition.joints.at(jnt_i)
                assert jnt is not None
                rbf_inp_jnt = RBFInputJoint(
                    jnt,
                    JointAttributeType(jnt_attr_type),
                    JointAttributeRepresentation(jnt_attr_rep),
                )
                solver.add_rbf_input_joint(rbf_inp_jnt)

            for pose_i in r.getRBFSolverOutputPoseIndices(index):
                solver.add_pose(self._rig_definition.rbf_poses.at(pose_i))

            self._rig_definition.add_rbf_solver(solver)
            logger.debug(solver)

    def _read_twists(self) -> None:
        r = self._reader
        logger.debug("Reading twists.")

        for index in range(r.getTwistCount()):
            twist = Twist()
            for jnt_i in r.getTwistInputJointIndices(index):
                twist.inputs.add(self._rig_definition.joints.at(jnt_i))
            for jnt_i in r.getTwistOutputJointIndices(index):
                twist.outputs.add(self._rig_definition.joints.at(jnt_i))

            self._rig_definition.add_twist(twist)
            logger.debug(twist)

    def _read_swings(self) -> None:
        r = self._reader
        logger.debug("Reading swings.")

        for index in range(r.getSwingCount()):
            swing = Swing()
            for jnt_i in r.getSwingInputJointIndices(index):
                swing.inputs.add(self._rig_definition.joints.at(jnt_i))
            for jnt_i in r.getSwingOutputJointIndices(index):
                swing.outputs.add(self._rig_definition.joints.at(jnt_i))

            self._rig_definition.add_swing(swing)
            logger.debug(swing)

    def _read_skin_transfers(self) -> None:
        r = self._reader
        logger.debug("Reading skin transfers.")

        for index in range(r.getSkinTransferCount()):
            st = SkinTransfer(
                self._rig_definition.meshes.at(r.getSkinTransferGeometryMeshIndex(index)),
                self._rig_definition.meshes.at(r.getSkinTransferTargetMeshIndex(index)),
                self._rig_definition.meshes.at(r.getSkinTransferSourceMeshIndex(index)),
            )
            for i in range(r.getSkinTransferMappingCount(index)):
                tji = r.getSkinTransferTargetJointIndex(index, i)
                sjis = r.getSkinTransferSourceJointIndices(index, i)
                mapping = SkinTransferMapping(
                    self._rig_definition.joints.at(tji), [self._rig_definition.joints.at(ji) for ji in sjis]
                )
                st.add_mapping(mapping)
            self._rig_definition.add_skin_transfer(st)
            logger.debug(st)


def read_fileformat_version(filepath) -> str:
    with open(filepath, "rb") as f:
        header = f.read(7)
        if len(header) < 7:
            raise ValueError("Header too short")
        if header[0:3] != b"RDF":
            raise ValueError("Not a valid RDF file")

        (generation,) = struct.unpack("!h", header[3:5])
        (version,) = struct.unpack("!h", header[5:7])

        return f"{generation}.{version}"
