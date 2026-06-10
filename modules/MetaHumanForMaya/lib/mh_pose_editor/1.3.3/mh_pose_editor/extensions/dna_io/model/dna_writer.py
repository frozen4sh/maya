# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import List, Callable

# External
from dna import Status, FileStream, BinaryStreamWriter

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.extensions.dna_io.model.dna_model import Mapping, MHDNAModel


def write_mapping(set_mapping_fn: Callable, set_indicies_fn: Callable, mapping: Mapping, label: str):
    LOG.info(f"writing {label}")
    unique_indices: List[List[int]] = []
    lods: List[int] = []

    for i, idx in enumerate(mapping.lods):
        values = mapping.indices[idx]
        try:
            unique_idx = unique_indices.index(values)
        except ValueError:
            unique_indices.append(values)
            unique_idx = len(unique_indices) - 1
        lods.append(unique_idx)

    for i, indices in enumerate(unique_indices):
        set_indicies_fn(i, indices)

    for i, lod in enumerate(lods):
        set_mapping_fn(i, lod)


class MHDNAWriter:
    def __init__(self, dna_path: str):
        self._dna_path: str = dna_path
        self._writer: BinaryStreamWriter
        self._model: MHDNAModel = MHDNAModel()

    def init_writer(self):
        stream = FileStream(self._dna_path, FileStream.AccessMode_Write, FileStream.OpenMode_Binary)
        self._writer = BinaryStreamWriter(stream)

    def write_header(self):
        LOG.info("writing dna header")
        self._writer.setFileFormatGeneration(self._model.version.generation)
        self._writer.setFileFormatVersion(self._model.version.version)

    def write_descriptor(self):
        LOG.info("writing dna descriptor")
        descriptor = self._model.descriptor
        writer = self._writer
        writer.setName(descriptor.name)
        writer.setArchetype(descriptor.archetype)
        if descriptor.gender is not None:
            writer.setGender(descriptor.gender.value)
        writer.setAge(descriptor.age)
        for key, value in descriptor.metadata:
            writer.setMetaData(key, value)
        writer.setTranslationUnit(descriptor.translation_unit.value)
        writer.setRotationUnit(descriptor.rotation_unit.value)
        writer.setCoordinateSystem(descriptor.coordinate_system.coor_sys)
        writer.setLODCount(descriptor.lod_count)
        writer.setDBMaxLOD(descriptor.max_lod)
        writer.setDBComplexity(descriptor.complexity)
        writer.setDBName(descriptor.db_name)

    def write_definition(self):
        LOG.info("writing dna definition")
        definition = self._model.definition
        writer = self._writer
        for i, name in enumerate(definition.gui_control_names):
            writer.setGUIControlName(i, name)
        for i, name in enumerate(definition.raw_control_names):
            writer.setRawControlName(i, name)
        for i, name in enumerate(definition.joint_names):
            writer.setJointName(i, name)
        writer.setJointHierarchy(definition.joint_hierarchy)
        if (
            "xs" in definition.neutral_joint_translations
            and "ys" in definition.neutral_joint_translations
            and "zs" in definition.neutral_joint_translations
        ):
            vectors = [
                list(triplet)
                for triplet in zip(
                    definition.neutral_joint_translations["xs"],
                    definition.neutral_joint_translations["ys"],
                    definition.neutral_joint_translations["zs"],
                )
            ]
            writer.setNeutralJointTranslations(vectors)
        if (
            "xs" in definition.neutral_joint_rotations
            and "ys" in definition.neutral_joint_rotations
            and "zs" in definition.neutral_joint_rotations
        ):
            vectors = [
                list(triplet)
                for triplet in zip(
                    definition.neutral_joint_rotations["xs"],
                    definition.neutral_joint_rotations["ys"],
                    definition.neutral_joint_rotations["zs"],
                )
            ]
            writer.setNeutralJointRotations(vectors)
        for index, name in enumerate(definition.mesh_names):
            writer.setMeshName(index, name)
        for index, lod in enumerate(definition.lod_mesh_mapping.lods):
            writer.setMeshIndices(index, definition.lod_mesh_mapping.indices[index])
            writer.setLODMeshMapping(index, lod)
        write_mapping(
            writer.setLODJointMapping, writer.setJointIndices, definition.lod_joint_mapping, "lod joints mapping"
        )

        # Animated map names
        writer.clearAnimatedMapNames()
        for i, name in enumerate(definition.animated_map_names):
            writer.setAnimatedMapName(i, name)

        write_mapping(
            writer.setLODAnimatedMapMapping,
            writer.setAnimatedMapIndices,
            definition.lod_animated_maps_mapping,
            "lod animated maps mapping",
        )

        # Blend shape channel names
        writer.clearBlendShapeChannelNames()
        for i, name in enumerate(definition.blend_shape_channel_names):
            writer.setBlendShapeChannelName(i, name)

        # Write blend shapes mapping
        writer.clearMeshBlendShapeChannelMappings()
        for i, (mesh_idx, channel_idx) in enumerate(
            zip(definition.mesh_blend_shape_channel_mapping["from"], definition.mesh_blend_shape_channel_mapping["to"])
        ):
            writer.setMeshBlendShapeChannelMapping(i, mesh_idx, channel_idx)

        write_mapping(
            writer.setLODBlendShapeChannelMapping,
            writer.setBlendShapeChannelIndices,
            definition.lod_blend_shape_mapping,
            "lod blend shapes mapping",
        )

    def write_behavior(self):
        LOG.info("writing dna behavior")
        behavior = self._model.behavior
        writer = self._writer
        writer.setJointRowCount(behavior.row_count)
        writer.setJointColumnCount(behavior.col_count)
        for i, g in enumerate(behavior.joint_groups):
            writer.setJointGroupLODs(i, g.lods)
            writer.setJointGroupInputIndices(i, g.input_indices)
            writer.setJointGroupOutputIndices(i, g.output_indices)
            writer.setJointGroupValues(i, g.values)
            writer.setJointGroupJointIndices(i, g.joint_indices)

        # Controls → GUI to raw mappings
        c = behavior.controls
        writer.setGUIToRawInputIndices(c.conditionals.input_indices)
        writer.setGUIToRawOutputIndices(c.conditionals.output_indices)
        writer.setGUIToRawFromValues(c.conditionals.from_values)
        writer.setGUIToRawToValues(c.conditionals.to_values)
        writer.setGUIToRawSlopeValues(c.conditionals.slope_values)
        writer.setGUIToRawCutValues(c.conditionals.cut_values)

        # PSD expressions
        writer.setPSDCount(c.psd_count)
        writer.setPSDRowIndices(c.psds["rows"])
        writer.setPSDColumnIndices(c.psds["columns"])
        writer.setPSDValues(c.psds["values"])

        # Blend shape channel behavior
        writer.setBlendShapeChannelLODs(behavior.blend_shape_channels.lods)
        writer.setBlendShapeChannelInputIndices(behavior.blend_shape_channels.input_indices)
        writer.setBlendShapeChannelOutputIndices(behavior.blend_shape_channels.output_indices)

        # Animated map behavior
        a = behavior.animated_maps
        writer.setAnimatedMapLODs(a.lods)
        writer.setAnimatedMapInputIndices(a.conditionals.input_indices)
        writer.setAnimatedMapOutputIndices(a.conditionals.output_indices)
        writer.setAnimatedMapFromValues(a.conditionals.from_values)
        writer.setAnimatedMapToValues(a.conditionals.to_values)
        writer.setAnimatedMapSlopeValues(a.conditionals.slope_values)
        writer.setAnimatedMapCutValues(a.conditionals.cut_values)

    def write_rbf_behavior(self):
        LOG.info("writing rbf_behavior behavior")
        rbf_behavior = self._model.rbf_behavior
        if not rbf_behavior:
            return
        writer = self._writer

        write_mapping(
            writer.setLODRBFSolverMapping,
            writer.setRBFSolverIndices,
            rbf_behavior.lod_solver_mapping,
            "lod rbf_behavior solver mapping",
        )

        for i, solver in enumerate(rbf_behavior.solvers):
            writer.setRBFSolverName(i, solver.name)
            writer.setRBFSolverRawControlIndices(i, solver.raw_control_indices)
            writer.setRBFSolverPoseIndices(i, solver.pose_indices)
            writer.setRBFSolverRawControlValues(i, solver.raw_control_values)
            writer.setRBFSolverRadius(i, solver.radius)
            writer.setRBFSolverWeightThreshold(i, solver.weight_threshold)
            writer.setRBFSolverType(i, solver.solver_type.value)
            writer.setRBFSolverAutomaticRadius(i, solver.automatic_radius.value)
            writer.setRBFSolverDistanceMethod(i, solver.distance_method.value)
            writer.setRBFSolverNormalizeMethod(i, solver.normalize_method.value)
            writer.setRBFSolverFunctionType(i, solver.function_type.value)
            writer.setRBFSolverTwistAxis(i, solver.twist_axis.value)
        for i, pose in enumerate(rbf_behavior.poses):
            writer.setRBFPoseName(i, pose.name)
            writer.setRBFPoseScale(i, pose.scale)

    def write_rbf_extension(self):
        LOG.info("writing rbf extension")
        rbf_extension = self._model.rbf_extension
        if not rbf_extension:
            return
        writer = self._writer
        for i, name in enumerate(rbf_extension.pose_control_names):
            writer.setRBFPoseControlName(i, name)
        for i, pose in enumerate(rbf_extension.poses):
            writer.setRBFPoseInputControlIndices(i, pose.input_control_indices)
            writer.setRBFPoseOutputControlIndices(i, pose.output_control_indices)
            writer.setRBFPoseOutputControlWeights(i, pose.output_control_weights)

    def write_joint_metadata(self):
        LOG.info("writing joint metadata")
        joint_matadata = self._model.joint_metadata
        if not joint_matadata:
            return
        writer = self._writer
        for i, rep in enumerate(joint_matadata.joint_representations):
            writer.setJointTranslationRepresentation(i, rep.translation.value)
            writer.setJointRotationRepresentation(i, rep.rotation.value)
            writer.setJointScaleRepresentation(i, rep.scale.value)

    def write_twist_swing(self):
        LOG.info("writing twist swing")
        twist_swing = self._model.twist_swing
        if not twist_swing:
            return
        writer = self._writer
        for i, entry in enumerate(twist_swing.twist):
            writer.setTwistInputControlIndices(i, entry.input_indices)
            writer.setTwistOutputJointIndices(i, entry.output_indices)
            writer.setTwistBlendWeights(i, entry.weights)
            writer.setTwistSetupTwistAxis(i, entry.axis)
        for i, entry in enumerate(twist_swing.swing):
            writer.setSwingInputControlIndices(i, entry.input_indices)
            writer.setSwingOutputJointIndices(i, entry.output_indices)
            writer.setSwingBlendWeights(i, entry.weights)
            writer.setSwingSetupTwistAxis(i, entry.axis)

    def write_geometry(self):
        LOG.info("writing geometry")
        if not self._model.geometry:
            return

        writer = self._writer
        for i, mesh in reversed(list(enumerate(self._model.geometry.meshes))):
            writer.setVertexPositions(i, mesh.positions)
            writer.setVertexTextureCoordinates(i, mesh.texture_coordinates)
            writer.setVertexNormals(i, mesh.normals)
            writer.setVertexLayouts(i, mesh.layouts)

            for j, face in reversed(list(enumerate(mesh.faces))):
                writer.setFaceVertexLayoutIndices(i, j, face)

            writer.setMaximumInfluencePerVertex(i, mesh.maximum_influence_per_vertex)
            for v, sw in reversed(list(enumerate(mesh.skin_weights))):
                writer.setSkinWeightsValues(i, v, sw.values)
                writer.setSkinWeightsJointIndices(i, v, sw.joint_indices)

            writer.clearBlendShapeTargets(i)
            for bs in reversed(mesh.blend_shape_targets):
                writer.setBlendShapeChannelIndex(i, bs.index, bs.channel_index)
                writer.setBlendShapeTargetVertexIndices(i, bs.index, bs.vertex_indices)
                writer.setBlendShapeTargetDeltas(i, bs.index, bs.deltas)

    def write(self, dna_model: MHDNAModel):
        self._model = dna_model
        self.init_writer()
        self.write_header()
        self.write_descriptor()
        self.write_definition()
        self.write_behavior()
        self.write_rbf_behavior()
        self.write_rbf_extension()
        self.write_joint_metadata()
        self.write_twist_swing()
        self.write_geometry()
        self._writer.write()
        if not Status.isOk():
            status = Status.get()
            raise RuntimeError(f"Error saving DNA: {status.message}")
