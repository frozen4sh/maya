# Copyright Epic Games, Inc. All Rights Reserved.

# External
from dna import Status, FileStream, DataLayer_All, BinaryStreamReader

# Internal
from mh_pose_editor.extensions.dna_io.model.dna_model import (
    Pose,
    Setup,
    Gender,
    Solver,
    Mapping,
    RBFPose,
    Version,
    Geometry,
    TwistAxis,
    CoorSystem,
    JointGroup,
    MHDNAModel,
    SkinWeight,
    TwistSwing,
    RBFBehavior,
    MeshGeometry,
    RBFExtension,
    RotationUnit,
    JointMetadata,
    RBFSolverType,
    JointRepresent,
    AutomaticRadius,
    RBFFunctionType,
    TranslationUnit,
    BlendShapeTarget,
    RBFDistanceMethod,
    RBFNormalizeMethod,
    JointRepresentation,
)


class MHDNAReader:
    def __init__(self, dna_path: str) -> None:
        self._dna_path: str = dna_path
        self._reader: BinaryStreamReader
        self._model: MHDNAModel = MHDNAModel()

    def init_reader(self) -> BinaryStreamReader:
        stream = FileStream(self._dna_path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
        self._reader = BinaryStreamReader(stream, DataLayer_All)
        self._reader.read()
        if not Status.isOk():
            status = Status.get()
            raise RuntimeError(f"Error loading DNA: {status.message}")
        return self._reader

    def read(self) -> MHDNAModel:
        self._model = MHDNAModel()
        self.init_reader()
        self.read_header()
        self.read_descriptor()
        self.read_definition()
        self.read_behavior()
        self.read_rbf_behavior()
        self.read_rbf_extension()
        self.read_joint_metadata()
        self.read_twist_swing()
        self.read_geometry()
        return self._model

    def read_header(self):
        reader = self._reader
        self._model.version = Version(
            generation=reader.getFileFormatGeneration(), version=reader.getFileFormatVersion()
        )

    def read_descriptor(self):
        reader = self._reader
        descriptor = self._model.descriptor
        descriptor.name = reader.getName()
        descriptor.archetype = reader.getArchetype()
        descriptor.gender = Gender(reader.getGender())
        descriptor.age = reader.getAge()
        descriptor.translation_unit = TranslationUnit(reader.getTranslationUnit())
        descriptor.rotation_unit = RotationUnit(reader.getRotationUnit())
        descriptor.coordinate_system = CoorSystem(reader.getCoordinateSystem())
        descriptor.lod_count = reader.getLODCount()
        descriptor.max_lod = reader.getDBMaxLOD()
        descriptor.complexity = reader.getDBComplexity()
        descriptor.metadata = [
            [k, reader.getMetaDataValue(k)]
            for k in [reader.getMetaDataKey(i) for i in range(reader.getMetaDataCount())]
        ]
        descriptor.db_name = reader.getDBName()

    def read_definition(self):
        reader = self._reader
        definition = self._model.definition
        definition.gui_control_names = [reader.getGUIControlName(i) for i in range(reader.getGUIControlCount())]
        definition.raw_control_names = [reader.getRawControlName(i) for i in range(reader.getRawControlCount())]
        definition.joint_names = [reader.getJointName(i) for i in range(reader.getJointCount())]
        definition.mesh_names = [reader.getMeshName(i) for i in range(reader.getMeshCount())]
        definition.joint_hierarchy = [reader.getJointParentIndex(i) for i in range(len(definition.joint_names))]
        definition.neutral_joint_translations = {
            "xs": list(reader.getNeutralJointTranslationXs()),
            "ys": list(reader.getNeutralJointTranslationYs()),
            "zs": list(reader.getNeutralJointTranslationZs()),
        }
        definition.neutral_joint_rotations = {
            "xs": list(reader.getNeutralJointRotationXs()),
            "ys": list(reader.getNeutralJointRotationYs()),
            "zs": list(reader.getNeutralJointRotationZs()),
        }

        lod_count = reader.getLODCount()
        definition.lod_joint_mapping = Mapping(
            lods=list(range(lod_count)), indices=[list(reader.getJointIndicesForLOD(i)) for i in range(lod_count)]
        )
        definition.lod_mesh_mapping = Mapping(
            lods=list(range(lod_count)), indices=[list(reader.getMeshIndicesForLOD(i)) for i in range(lod_count)]
        )

        definition.blend_shape_channel_names = [
            reader.getBlendShapeChannelName(i) for i in range(reader.getBlendShapeChannelCount())
        ]
        definition.lod_blend_shape_mapping = Mapping(
            lods=list(range(lod_count)),
            indices=[list(reader.getBlendShapeChannelIndicesForLOD(i)) for i in range(lod_count)],
        )

        count = reader.getMeshBlendShapeChannelMappingCount()
        definition.mesh_blend_shape_channel_mapping = {"from": [], "to": []}
        for i in range(count):
            mapping = reader.getMeshBlendShapeChannelMapping(i)
            definition.mesh_blend_shape_channel_mapping["from"].append(mapping.meshIndex)
            definition.mesh_blend_shape_channel_mapping["to"].append(mapping.blendShapeChannelIndex)

        definition.animated_map_names = [reader.getAnimatedMapName(i) for i in range(reader.getAnimatedMapCount())]
        definition.lod_animated_maps_mapping = Mapping(
            lods=list(range(lod_count)), indices=[list(reader.getAnimatedMapIndicesForLOD(i)) for i in range(lod_count)]
        )

    def read_behavior(self):
        reader = self._reader
        behavior = self._model.behavior
        behavior.row_count = reader.getJointRowCount()
        behavior.col_count = reader.getJointColumnCount()
        behavior.joint_groups = [
            JointGroup(
                lods=list(reader.getJointGroupLODs(i)),
                input_indices=list(reader.getJointGroupInputIndices(i)),
                output_indices=list(reader.getJointGroupOutputIndices(i)),
                values=list(reader.getJointGroupValues(i)),
                joint_indices=list(reader.getJointGroupJointIndices(i)),
            )
            for i in range(reader.getJointGroupCount())
        ]
        controls = behavior.controls
        controls.psd_count = reader.getPSDCount()
        controls.conditionals.input_indices = list(reader.getGUIToRawInputIndices())
        controls.conditionals.output_indices = list(reader.getGUIToRawOutputIndices())
        controls.conditionals.from_values = list(reader.getGUIToRawFromValues())
        controls.conditionals.to_values = list(reader.getGUIToRawToValues())
        controls.conditionals.slope_values = list(reader.getGUIToRawSlopeValues())
        controls.conditionals.cut_values = list(reader.getGUIToRawCutValues())
        controls.psds["rows"] = list(reader.getPSDRowIndices())
        controls.psds["columns"] = list(reader.getPSDColumnIndices())
        controls.psds["values"] = list(reader.getPSDValues())

        behavior.blend_shape_channels.lods = list(reader.getBlendShapeChannelLODs())
        behavior.blend_shape_channels.input_indices = list(reader.getBlendShapeChannelInputIndices())
        behavior.blend_shape_channels.output_indices = list(reader.getBlendShapeChannelOutputIndices())

        anim_maps = behavior.animated_maps
        anim_maps.lods = list(reader.getAnimatedMapLODs())
        anim_maps.conditionals.input_indices = list(reader.getAnimatedMapInputIndices())
        anim_maps.conditionals.output_indices = list(reader.getAnimatedMapOutputIndices())
        anim_maps.conditionals.from_values = list(reader.getAnimatedMapFromValues())
        anim_maps.conditionals.to_values = list(reader.getAnimatedMapToValues())
        anim_maps.conditionals.slope_values = list(reader.getAnimatedMapSlopeValues())
        anim_maps.conditionals.cut_values = list(reader.getAnimatedMapCutValues())

    def read_rbf_behavior(self):
        reader = self._reader
        rbf_behavior = self._model.rbf_behavior
        if not rbf_behavior:
            rbf_behavior = RBFBehavior()
            self._model.rbf_behavior = rbf_behavior

        lod_count = reader.getLODCount()
        rbf_behavior.lod_solver_mapping = Mapping(
            lods=list(range(lod_count)), indices=[list(reader.getRBFSolverIndicesForLOD(i)) for i in range(lod_count)]
        )

        for i in range(reader.getRBFSolverCount()):
            rbf_behavior.solvers.append(
                Solver(
                    name=reader.getRBFSolverName(i),
                    raw_control_indices=list(reader.getRBFSolverRawControlIndices(i)),
                    pose_indices=list(reader.getRBFSolverPoseIndices(i)),
                    raw_control_values=list(reader.getRBFSolverRawControlValues(i)),
                    radius=reader.getRBFSolverRadius(i),
                    weight_threshold=reader.getRBFSolverWeightThreshold(i),
                    solver_type=RBFSolverType(reader.getRBFSolverType(i)),
                    automatic_radius=AutomaticRadius(reader.getRBFSolverAutomaticRadius(i)),
                    distance_method=RBFDistanceMethod(reader.getRBFSolverDistanceMethod(i)),
                    normalize_method=RBFNormalizeMethod(reader.getRBFSolverNormalizeMethod(i)),
                    function_type=RBFFunctionType(reader.getRBFSolverFunctionType(i)),
                    twist_axis=TwistAxis(reader.getRBFSolverTwistAxis(i)),
                )
            )
        for i in range(reader.getRBFPoseCount()):
            rbf_behavior.poses.append(Pose(name=reader.getRBFPoseName(i), scale=reader.getRBFPoseScale(i)))

    def read_rbf_extension(self):
        reader = self._reader
        rbf_extension = self._model.rbf_extension
        if not rbf_extension:
            rbf_extension = RBFExtension()
            self._model.rbf_extension = rbf_extension
        rbf_extension.pose_control_names = [
            reader.getRBFPoseControlName(i) for i in range(reader.getRBFPoseControlCount())
        ]
        for i in range(reader.getRBFPoseCount()):
            rbf_extension.poses.append(
                RBFPose(
                    input_control_indices=list(reader.getRBFPoseInputControlIndices(i)),
                    output_control_indices=list(reader.getRBFPoseOutputControlIndices(i)),
                    output_control_weights=list(reader.getRBFPoseOutputControlWeights(i)),
                )
            )

    def read_joint_metadata(self):
        reader = self._reader
        joint_matadata = self._model.joint_metadata
        if not joint_matadata:
            joint_matadata = JointMetadata()
            self._model.joint_metadata = joint_matadata
        joint_matadata.joint_representations = [
            JointRepresentation(
                translation=JointRepresent(reader.getJointTranslationRepresentation(i)),
                rotation=JointRepresent(reader.getJointRotationRepresentation(i)),
                scale=JointRepresent(reader.getJointScaleRepresentation(i)),
            )
            for i in range(reader.getJointCount())
        ]

    def read_twist_swing(self):
        reader = self._reader
        twist_swing = self._model.twist_swing
        if not twist_swing:
            twist_swing = TwistSwing()
            self._model.twist_swing = twist_swing
        for i in range(reader.getTwistCount()):
            twist_swing.twist.append(
                Setup(
                    input_indices=list(reader.getTwistInputControlIndices(i)),
                    output_indices=list(reader.getTwistOutputJointIndices(i)),
                    weights=list(reader.getTwistBlendWeights(i)),
                    axis=reader.getTwistSetupTwistAxis(i),
                )
            )
        for i in range(reader.getSwingCount()):
            twist_swing.swing.append(
                Setup(
                    input_indices=list(reader.getSwingInputControlIndices(i)),
                    output_indices=list(reader.getSwingOutputJointIndices(i)),
                    weights=list(reader.getSwingBlendWeights(i)),
                    axis=reader.getSwingSetupTwistAxis(i),
                )
            )

    def read_geometry(self):
        reader = self._reader
        geometry = self._model.geometry
        if not geometry:
            geometry = Geometry()
            self._model.geometry = geometry

        for i in range(reader.getMeshCount()):
            # Check if mesh is there
            vtx_count = reader.getVertexPositionCount(i)
            positions = []
            tex_coords = []
            normals = []
            layouts = []
            if vtx_count > 0:
                for index in range(vtx_count):
                    positions.append(list(reader.getVertexPosition(i, index)))

                tex_coor_count = reader.getVertexTextureCoordinateCount(i)
                for index in range(tex_coor_count):
                    tex_coords.append(list(reader.getVertexTextureCoordinate(i, index)))

                nor_count = reader.getVertexNormalCount(i)
                for index in range(nor_count):
                    normals.append(list(reader.getVertexNormal(i, index)))

                layouts_count = reader.getVertexLayoutCount(i)
                for index in range(layouts_count):
                    layouts.append(list(reader.getVertexLayout(i, index)))

                faces = [list(reader.getFaceVertexLayoutIndices(i, j)) for j in range(reader.getFaceCount(i))]

                max_influence = reader.getMaximumInfluencePerVertex(i)
                skin_weights = []
                for v in range(reader.getSkinWeightsCount(i)):
                    skin_weights.append(
                        SkinWeight(
                            values=list(reader.getSkinWeightsValues(i, v)),
                            joint_indices=list(reader.getSkinWeightsJointIndices(i, v)),
                        )
                    )

                blend_shape_targets = []
                for t in range(reader.getBlendShapeTargetCount(i)):
                    vertex_indices = list(reader.getBlendShapeTargetVertexIndices(i, t))
                    deltas = [
                        list(reader.getBlendShapeTargetDelta(i, t, v_index)) for v_index in range(len(vertex_indices))
                    ]
                    blend_shape_targets.append(
                        BlendShapeTarget(
                            index=t,
                            channel_index=reader.getBlendShapeChannelIndex(i, t),
                            vertex_indices=vertex_indices,
                            deltas=deltas,
                        )
                    )

                geometry.meshes.append(
                    MeshGeometry(
                        positions=positions,
                        texture_coordinates=tex_coords,
                        normals=normals,
                        layouts=layouts,
                        faces=faces,
                        maximum_influence_per_vertex=max_influence,
                        skin_weights=skin_weights,
                        blend_shape_targets=blend_shape_targets,
                    )
                )
