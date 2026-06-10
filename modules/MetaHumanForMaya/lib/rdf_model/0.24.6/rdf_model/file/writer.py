# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

from typing import cast

import rdf as rdflib

from ..utils import get_logger
from ..model.items import (
    SymmetrySide,
    ExpressionFunction,
    SumExpressionFunction,
    ExpressionFunctionType,
    PhaseExpressionFunction,
    SplitExpressionFunction,
    SubtractExpressionFunction,
)
from ..model.definition import RigDefinition

logger = get_logger()


class RDFWriter:
    def __init__(self, rdf_file: str, rig_definition: RigDefinition) -> None:
        self._rdf_file = rdf_file
        self._rig_definition = rig_definition
        self._writer: rdflib.RigDefinitionBinaryStreamWriter = None

    def _open_writer(self) -> None:
        if not self._rdf_file:
            logger.error("No RDF file path defined.")
            return
        stream = rdflib.FileStream(
            self._rdf_file,
            rdflib.FileStream.AccessMode_Write,
            rdflib.FileStream.OpenMode_Binary,
        )
        self._writer = rdflib.RigDefinitionBinaryStreamWriter(stream)
        logger.info(f"RDF writer created: {self._rdf_file}")

    def _close_writer(self):
        logger.info("Writing RDF file.")
        self._writer.write()
        logger.info(f"RDF writer closed: {self._rdf_file}")

    def write(self) -> None:
        logger.info("rdf writer - start.")
        self._rig_definition.index()
        self._open_writer()

        self._write_descriptor()
        self._write_controls()
        self._write_joints()
        self._write_animated_map_channels()
        self._write_joint_groups()
        self._write_regions()
        self._write_textures()
        self._write_shaders()
        self._write_meshes()
        self._write_split_maps()
        self._write_expressions()
        self._write_psd_definitions()
        self._write_psd_nets()
        self._write_lods()
        self._write_mix_regions()
        self._write_symmetry()
        self._write_rbf_poses()
        self._write_rbf_solvers()
        self._write_twists()
        self._write_swings()
        self._write_skin_transfers()

        self._close_writer()
        logger.info("rdf writer - end.")

    def _write_descriptor(self) -> None:
        w = self._writer
        logger.info("Writing descriptor.")
        desc = self._rig_definition.descriptor
        if desc is None:
            logger.warning("Unable to write descriptor.")
            return
        w.setTranslationUnit(int(desc.translation_unit))
        w.setRotationUnit(int(desc.rotation_unit))
        coord_sys = rdflib.CoordinateSystem()
        coordinate_system = desc.coordinate_system
        coord_sys.xAxis = int(coordinate_system.x_axis)
        coord_sys.yAxis = int(coordinate_system.y_axis)
        coord_sys.zAxis = int(coordinate_system.z_axis)
        w.setCoordinateSystem(coord_sys)
        w.setDBComplexity(desc.db_complexity)
        w.setDBName(desc.db_name)

    def _write_controls(self) -> None:
        w = self._writer
        logger.info("Writing controls.")

        # gui controls
        w.clearGUIControls()
        for gui_control in self._rig_definition.gui_controls:
            w.setGUIControlName(gui_control.index, gui_control.name)
            w.setGUIControlFromValue(gui_control.index, gui_control.from_value)
            w.setGUIControlToValue(gui_control.index, gui_control.to_value)

        # controls
        w.clearControls()
        for control in self._rig_definition.controls:
            w.setControlName(control.index, control.name)
            w.setControlType(control.index, int(control.control_type))
            w.setControlExportedToRig(control.index, control.is_exported)
            w.setControlFromValue(control.index, control.from_value)
            w.setControlToValue(control.index, control.to_value)

        # gui to raw
        w.clearGUIToRaw()
        for mapping in self._rig_definition.gui_to_raw:
            w.setGUIToRawInputIndex(mapping.index, mapping.in_control.index)
            w.setGUIToRawOutputIndex(mapping.index, mapping.out_control.index)
            w.setGUIToRawFromValue(mapping.index, mapping.from_value)
            w.setGUIToRawToValue(mapping.index, mapping.to_value)
            w.setGUIToRawSlopeValue(mapping.index, mapping.slope_value)
            w.setGUIToRawCutValue(mapping.index, mapping.cut_value)

    def _write_joints(self) -> None:
        w = self._writer
        logger.info("Writing joints.")
        w.clearJoints()
        for joint in self._rig_definition.joints:
            w.setJointName(joint.index, joint.name)
            w.setJointColor(joint.index, joint.color)
            w.setJointRadius(joint.index, joint.radius)
        hierarchy = []
        for joint in self._rig_definition.joints:
            if joint.parent is None:
                hierarchy.append(joint.index)
            else:
                hierarchy.append(joint.parent.index)
        w.setJointHierarchy(hierarchy)

    def _write_animated_map_channels(self) -> None:
        pass

    def _write_joint_groups(self) -> None:
        w = self._writer
        logger.info("Writing joint groups.")
        w.clearJointGroups()
        for joint_group in self._rig_definition.joint_groups:
            w.setJointGroupName(joint_group.index, joint_group.name)
            indices = [j.index for j in joint_group.joints]
            w.setJointGroupJointIndices(joint_group.index, indices)

    def _write_regions(self) -> None:
        w = self._writer
        logger.info("Writing regions.")
        w.clearRegions()
        for region in self._rig_definition.regions:
            w.setRegionName(region.index, region.name)
            indices = [j.index for j in region.joints]
            w.setRegionJointIndices(region.index, indices)

    def _write_textures(self) -> None:
        w = self._writer
        # texture masks
        logger.info("Writing texture masks.")
        w.clearTextureMasks()
        for text_mask in self._rig_definition.texture_masks:
            w.setTextureMaskName(text_mask.index, text_mask.name)

        # texture map types
        logger.info("Writing texture map types.")
        w.clearTextureMapTypes()
        for text_map_type in self._rig_definition.texture_map_types:
            w.setTextureMapTypeName(text_map_type.index, text_map_type.name)

        # texture maps
        logger.info("Writing texture maps.")
        w.clearTextureMaps()
        for text_map in self._rig_definition.texture_maps:
            w.setTextureMapName(text_map.index, text_map.name)
            w.setTextureMapTypeIndex(text_map.index, getattr(text_map, "map_type").index)
            w.setTextureMapBase(text_map.index, text_map.is_base)

    def _write_shaders(self) -> None:
        w = self._writer
        logger.info("Writing shaders.")
        w.clearShaders()
        w.clearShaderParameters()
        w.clearShaderInputs()
        for shader in self._rig_definition.shaders:
            w.setShaderName(shader.index, shader.name)
            w.setShaderType(shader.index, int(shader.shader_type))

            # shader parameters
            for shd_parm in shader.parameters:
                w.setShaderParameterName(shd_parm.index, shd_parm.name)
                w.setShaderParameterValue(shd_parm.index, shd_parm.value)
            indices = [shd_param.index for shd_param in shader.parameters]
            w.setShaderParameterIndices(shader.index, indices)

            # shader inputs
            for shd_in in shader.inputs:
                w.setShaderInputName(shd_in.index, shd_in.name)
                w.setShaderInputTextureMapTypeIndex(shd_in.index, getattr(shd_in, "map_type").index)
            indices = [shd_in.index for shd_in in shader.inputs]
            w.setShaderInputIndices(shader.index, indices)

    def _write_meshes(self) -> None:
        w = self._writer
        logger.info("Writing meshes.")
        w.clearMeshes()
        blend_shapes_per_mesh = self._rig_definition.get_blend_shape_channels_by_meshes()
        for mesh in self._rig_definition.meshes:
            w.setMeshName(mesh.index, mesh.name)
            w.setMeshShaderIndex(mesh.index, getattr(mesh, "shader").index)
            w.setMeshExportedToRig(mesh.index, mesh.is_exported)
            w.setMeshVertexCount(mesh.index, mesh.vertex_count)
            w.setMeshUVCount(mesh.index, mesh.uv_count)
            w.setMeshFaceCount(mesh.index, len(mesh.faces))
            for face in mesh.faces:
                w.setMeshFaceVertexIndices(mesh.index, face.index, face.vertex_indices)
            w.setMeshMaximumInfluencePerVertex(mesh.index, mesh.max_IPV)
            w.setMeshBlendShapeChannelCount(mesh.index, len(blend_shapes_per_mesh.get(mesh.name, [])))

    def _write_split_maps(self) -> None:
        w = self._writer
        logger.info("Writing split maps.")
        w.clearSplitMaps()
        for split_map in self._rig_definition.split_maps:
            w.setSplitMapName(split_map.index, split_map.name)
            w.setSplitMapMeshIndex(split_map.index, getattr(split_map, "mesh").index)
            w.setSplitMapWeights(split_map.index, split_map.weights)

    def _write_expressions(self) -> None:
        w = self._writer
        logger.info("Writing expressions.")
        w.clearExpressions()
        w.clearAnimatedMaps()
        w.clearSplitJoints()
        w.clearSplitExpressionFunctions()
        w.clearSubtractExpressionFunctions()
        w.clearSumExpressionFunctions()
        w.clearPhaseExpressionFunctions()
        for exp in self._rig_definition.expressions:
            # base expression
            w.setExpressionName(exp.index, exp.name)
            w.setExpressionType(exp.index, int(exp.expression_type))
            w.setExpressionExportedToRig(exp.index, exp.is_exported)
            w.setExpressionPhaseCount(exp.index, exp.phase_count)

            # controls
            if exp.control:
                w.setExpressionControlIndex(exp.index, exp.control.index)

            # mesh deformers
            mesh_indices = [d.mesh.index for d in exp.mesh_deformers]
            def_types = [int(d.deformation_type) for d in exp.mesh_deformers]
            w.setExpressionMeshIndices(exp.index, mesh_indices)
            w.setExpressionMeshDeformationTypes(exp.index, def_types)

            # animated maps
            for am in exp.animated_maps:
                w.setAnimatedMapTextureMapIndex(am.index, am.texture_map.index)
                indices = [m.index for m in am.texture_masks]
                w.setAnimatedMapTextureMaskIndices(am.index, indices)
            indices = [am.index for am in exp.animated_maps]
            w.setExpressionAnimatedMapIndices(exp.index, indices)

            # function
            if exp.function:
                self._write_function(exp.function)
                if exp.function.index:
                    w.setExpressionFunctionIndex(exp.index, exp.function.index)
                w.setExpressionFunctionType(exp.index, int(exp.function.function_type))

            # regions
            indices = [r.index for r in exp.regions]
            w.setExpressionRegionIndices(exp.index, indices)

    def _write_function(self, function: ExpressionFunction):
        w = self._writer
        if function.function_type == ExpressionFunctionType.Split:
            split_fn = cast(SplitExpressionFunction, function)
            w.setSplitExpressionFunctionSourceExpressionIndex(
                split_fn.index, getattr(split_fn, "source_expression").index
            )
            indices = [sm.index for sm in split_fn.split_maps]
            w.setSplitExpressionFunctionSplitMapIndices(split_fn.index, indices)
            for sj in split_fn.split_joints:
                w.setSplitJointsJointGroupIndex(sj.index, sj.joint_group.index)
                w.setSplitJointsMultiplier(sj.index, sj.multiplier)
                w.setSplitJointsRotation(sj.index, sj.rotation)
            indices = [sj.index for sj in split_fn.split_joints]
            w.setSplitExpressionFunctionSplitJointsIndices(split_fn.index, indices)

        if function.function_type == ExpressionFunctionType.Subtract:
            sub_fn = cast(SubtractExpressionFunction, function)
            w.setSubtractExpressionFunctionMinuendExpressionIndex(
                sub_fn.index, getattr(sub_fn.minuend, "expression").index
            )
            w.setSubtractExpressionFunctionSubtrahendExpressionIndex(
                sub_fn.index, getattr(sub_fn.subtrahend, "expression").index
            )
            w.setSubtractExpressionFunctionMinuendMultiplier(sub_fn.index, sub_fn.minuend.multiplier)
            w.setSubtractExpressionFunctionSubtrahendMultiplier(sub_fn.index, sub_fn.subtrahend.multiplier)

        if function.function_type == ExpressionFunctionType.Sum:
            sum_fn = cast(SumExpressionFunction, function)
            indices = [getattr(e, "expression").index for e in sum_fn.elements]
            w.setSumExpressionFunctionExpressionIndices(sum_fn.index, indices)
            multipliers = [e.multiplier for e in sum_fn.elements]
            w.setSumExpressionFunctionMultipliers(sum_fn.index, multipliers)

        if function.function_type == ExpressionFunctionType.Phase:
            phase_fn = cast(PhaseExpressionFunction, function)
            w.setPhaseExpressionFunctionSourceExpressionIndex(
                phase_fn.index, getattr(phase_fn, "source_expression").index
            )
            w.setPhaseExpressionFunctionSourceExpressionPhase(phase_fn.index, phase_fn.phase_number)

    def _write_psd_definitions(self) -> None:
        w = self._writer
        logger.info("Writing psd definitions.")
        w.clearPSDDefinitions()
        for psd_def in self._rig_definition.psd_definitions:
            w.setPSDDefinitionName(psd_def.index, psd_def.name)
            w.setPSDDefinitionLayer(psd_def.index, psd_def.layer)
            w.setPSDDefinitionComplexExpressionIndex(psd_def.index, getattr(psd_def.complex_expression, "index"))
            w.setPSDDefinitionTargetExpressionIndex(psd_def.index, getattr(psd_def.target_expression, "index"))
            w.setPSDDefinitionCorrectiveExpressionIndex(psd_def.index, getattr(psd_def.corrective_expression, "index"))

    def _write_psd_nets(self) -> None:
        w = self._writer
        logger.info("Writing psd nets.")
        w.clearPSDNets()
        for psd_net in self._rig_definition.psd_nets:
            w.setPSDNetName(psd_net.index, psd_net.name)
            indices = [getattr(psd_in, "expression").index for psd_in in psd_net.inputs]
            w.setPSDNetInputExpressionIndices(psd_net.index, indices)
            multipliers = [psd_in.multiplier for psd_in in psd_net.inputs]
            w.setPSDNetValues(psd_net.index, multipliers)
            w.setPSDNetOutputExpressionIndex(psd_net.index, getattr(psd_net, "output_expression").index)
            if psd_net.psd_definition is not None:
                w.setPSDNetPSDDefinitionIndex(psd_net.index, psd_net.psd_definition.index)

    def _write_lods(self) -> None:
        w = self._writer
        logger.info("Writing lods.")
        w.clearLODs()
        for lod in self._rig_definition.lods:
            indices = [net.index for net in lod.psd_nets]
            w.setLODPSDNetIndices(lod.index, indices)
            indices = [joint.index for joint in lod.joints]
            w.setLODJointIndices(lod.index, indices)
            indices = [am.index for am in lod.animated_map_channels]
            w.setLODAnimatedMapChannelIndices(lod.index, indices)
            indices = [mesh.index for mesh in lod.meshes]
            w.setLODMeshIndices(lod.index, indices)
            indices = [i for i in range(len(self._rig_definition.get_blend_shape_channels_by_exported(lod)))]
            w.setLODBlendShapeChannelIndices(lod.index, indices)

    def _write_mix_regions(self) -> None:
        w = self._writer
        logger.info("Writing mix regions.")
        w.clearMixRegions()
        for mix_region in self._rig_definition.mix_regions:
            w.setMixRegionName(mix_region.index, mix_region.name)
            indices = [jw.joint.index for jw in mix_region.joint_weights]
            w.setMixRegionJointIndices(mix_region.index, indices)
            weights = [jw.weight for jw in mix_region.joint_weights]
            w.setMixRegionJointWeights(mix_region.index, weights)
            indices = [sm.index for sm in mix_region.split_maps]
            w.setMixRegionSplitMapIndices(mix_region.index, indices)

    def _write_symmetry(self) -> None:
        w = self._writer
        logger.info("Writing symmetry.")

        # symmetry joints
        mapping = []
        side = []
        for joint in self._rig_definition.joints:
            sym_jnt = self._rig_definition.symmetry_joints.get(joint.name)
            if sym_jnt is None:
                mapping.append(joint.index)
                side.append(int(SymmetrySide.NoSymmetry))
            else:
                if sym_jnt.pair is None:
                    mapping.append(sym_jnt.joint.index)
                else:
                    mapping.append(sym_jnt.pair.index)
                side.append(sym_jnt.side)
        w.setSymmetryJointMappings(mapping)
        w.setSymmetryJointSides(side)

        # symmetry meshes
        w.clearSymmetryMeshes()
        for sym_mesh in self._rig_definition.symmetry_meshes:
            w.setSymmetryMeshMeshIndex(sym_mesh.index, getattr(sym_mesh.mesh, "index"))
            w.setSymmetryMeshVertexMappings(sym_mesh.index, sym_mesh.vertex_mapping)
            side = [int(vs) for vs in sym_mesh.vertex_side]
            w.setSymmetryMeshVertexSides(sym_mesh.index, side)

    def _write_rbf_poses(self) -> None:
        w = self._writer
        logger.info("Writing rbf poses.")
        w.clearRBFPoses()

        for pose in self._rig_definition.rbf_poses:
            w.setRBFPoseName(pose.index, pose.name)
            indices = [ctrl.index for ctrl in pose.input_controls]
            w.setRBFPoseInputRawControlIndices(pose.index, indices)
            indices = [exp.index for exp in pose.output_expressions]
            w.setRBFPoseOutputExpressionIndices(pose.index, indices)

    def _write_rbf_solvers(self) -> None:
        w = self._writer
        logger.info("Writing rbf solvers.")
        w.clearRBFSolvers()

        for solver in self._rig_definition.rbf_solvers:
            w.setRBFSolverName(solver.index, solver.name)
            w.setRBFSolverType(solver.index, solver.solver_type)
            w.setRBFSolverDistanceMethod(solver.index, solver.distance_method)
            w.setRBFSolverFunctionType(solver.index, solver.function_type)
            jnt_indices = []
            attrs_values = []
            reprs_values = []
            for rbf_inp_jnt in solver.input_joints:
                jnt_indices.append(rbf_inp_jnt.joint.index)
                attrs_values.append(rbf_inp_jnt.jnt_attr_type)
                reprs_values.append(rbf_inp_jnt.jnt_attr_repr)
            w.setRBFSolverInputJointIndices(solver.index, jnt_indices)
            w.setRBFSolverInputJointAttributes(solver.index, attrs_values)
            w.setRBFSolverInputJointAttributeRepresentations(solver.index, reprs_values)
            indices = [pose.index for pose in solver.poses]
            w.setRBFSolverOutputPoseIndices(solver.index, indices)

    def _write_twists(self) -> None:
        w = self._writer
        logger.info("Writing twists.")
        w.clearTwists()

        for twist in self._rig_definition.twists:
            indices = [jnt.index for jnt in twist.inputs]
            w.setTwistInputJointIndices(twist.index, indices)
            indices = [jnt.index for jnt in twist.outputs]
            w.setTwistOutputJointIndices(twist.index, indices)

    def _write_swings(self) -> None:
        w = self._writer
        logger.info("Writing swings.")
        w.clearSwings()

        for twist in self._rig_definition.twists:
            indices = [jnt.index for jnt in twist.inputs]
            w.setSwingInputJointIndices(twist.index, indices)
            indices = [jnt.index for jnt in twist.outputs]
            w.setSwingOutputJointIndices(twist.index, indices)

    def _write_skin_transfers(self) -> None:
        w = self._writer
        logger.info("Writing skin transfers.")
        w.clearSkinTransfers()

        for st in self._rig_definition.skin_transfers:
            w.setSkinTransferGeometryMeshIndex(st.index, st.geo_mesh.index)
            w.setSkinTransferTargetMeshIndex(st.index, st.target_mesh.index)
            w.setSkinTransferSourceMeshIndex(st.index, st.source_mesh.index)
            for i, mapping in enumerate(st.mapping):
                w.setSkinTransferTargetJointIndex(st.index, i, mapping.target_joint.index)
                indices = [jnt.index for jnt in mapping.source_joints]
                w.setSkinTransferSourceJointIndices(st.index, i, indices)
