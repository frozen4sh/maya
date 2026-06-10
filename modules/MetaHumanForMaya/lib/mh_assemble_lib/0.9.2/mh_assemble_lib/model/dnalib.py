# Copyright Epic Games, Inc. All Rights Reserved.
"""
DNA structure wrapper classes.
"""
import logging
from enum import Enum
from typing import Set, Dict, List, cast

from dna import (
    Status,
    FileStream,
    DataLayer_All,
    BinaryStreamReader,
    DataLayer_Behavior,
    DataLayer_Geometry,
    DataLayer_Definition,
    DataLayer_Descriptor,
)

from mh_assemble_lib.common import DNAReaderException
from mh_assemble_lib.model.unit import RotationUnit, TranslationUnit
from mh_assemble_lib.model.element import (
    UV,
    Normal,
    Point3,
    MeshElement,
    JointElement,
    VertexLayout,
    ControlElement,
    BlendShapeDelta,
    BlendShapeElement,
    AnimatedMapElement,
    SkinClusterElement,
)


class Layer(Enum):
    """DNA file layers enumeration."""

    descriptor = DataLayer_Descriptor
    definition = DataLayer_Definition
    behavior = DataLayer_Behavior
    geometry = DataLayer_Geometry
    all = DataLayer_All


class DNA:
    """
    DNA wrapper class.

    Implement low and high level getter methods.
    """

    def __init__(self, path: str, reader: BinaryStreamReader):
        self.path: str = path
        self._reader: BinaryStreamReader = reader
        self._map_mesh_lod: Dict[int, int] = None

    # DESCRIPTOR
    def get_translation_unit(self) -> TranslationUnit:
        return TranslationUnit(self._reader.getTranslationUnit())

    def get_rotation_unit(self) -> RotationUnit:
        return RotationUnit(self._reader.getRotationUnit())

    def get_name(self) -> str:
        return cast(str, self._reader.getName())

    # DEFINITION
    # joints
    def get_joint_count(self) -> int:
        return cast(int, self._reader.getJointCount())

    def get_joint_name(self, index: int) -> str:
        return cast(str, self._reader.getJointName(index))

    def get_joint_parent_index(self, index: int) -> int:
        return cast(int, self._reader.getJointParentIndex(index))

    def get_neutral_joint_translation(self, index: int) -> Point3:
        translation = cast(List[float], self._reader.getNeutralJointTranslation(index))
        return Point3(translation[0], translation[1], translation[2])

    def get_neutral_joint_rotation(self, index: int) -> Point3:
        rotation = cast(List[float], self._reader.getNeutralJointRotation(index))
        return Point3(rotation[0], rotation[1], rotation[2])

    def get_joints(self) -> List[JointElement]:
        """Return list of JointElement objects agregating joint index and name."""
        joints: List[JointElement] = []
        for i in range(self.get_joint_count()):
            joint = JointElement(i, self.get_joint_name(i))
            joints.append(joint)
        return joints

    def get_neutral_joints(self) -> List[JointElement]:
        """Return list of JointElement objects agregating neutral joint data."""
        joints: List[JointElement] = []
        for i in range(self.get_joint_count()):
            name = self.get_joint_name(i)
            translation = self.get_neutral_joint_translation(i)
            rotation = self.get_neutral_joint_rotation(i)
            parent_index = self.get_joint_parent_index(i)
            joint = JointElement(i, name)
            joint.translation = translation
            joint.rotation = rotation
            joint.parent_index = parent_index
            joints.append(joint)
        return joints

    # controls
    def get_raw_control_count(self) -> int:
        return cast(int, self._reader.getRawControlCount())

    def get_raw_control_name(self, index: int) -> str:
        return cast(str, self._reader.getRawControlName(index))

    def get_raw_controls(self) -> List[ControlElement]:
        """Return list of ControlElement objects agregating raw control data."""
        controls: List[ControlElement] = []
        for i in range(self.get_raw_control_count()):
            name = self.get_raw_control_name(i)
            ctrl = ControlElement(name)
            controls.append(ctrl)
        return controls

    # animated maps
    def get_animated_map_count(self) -> int:
        return cast(int, self._reader.getAnimatedMapCount())

    def get_animated_map_name(self, index: int) -> str:
        return cast(str, self._reader.getAnimatedMapName(index))

    def get_animated_maps(self) -> List[AnimatedMapElement]:
        """Return list of AnimatedMapElement objects agregating animated map data."""
        anim_maps: List[AnimatedMapElement] = []
        for i in range(self.get_animated_map_count()):
            name = self.get_animated_map_name(i)
            anim_map = AnimatedMapElement(name)
            anim_maps.append(anim_map)
        return anim_maps

    # meshes
    def get_mesh_count(self) -> int:
        return cast(int, self._reader.getMeshCount())

    def get_mesh_name(self, index: int) -> str:
        return cast(str, self._reader.getMeshName(index))

    def get_mesh_lod(self, index: int) -> int:
        self._map_mesh_lods()
        return self._map_mesh_lod[index]

    def get_mesh(self, index: int) -> MeshElement:
        """Return MeshElement objects agregating mesh index, name and lod."""
        name = self.get_mesh_name(index)
        lod = self.get_mesh_lod(index)
        mesh = MeshElement(index, name, lod)
        return mesh

    def get_meshes(self) -> List[MeshElement]:
        """Return list of MeshElement objects agregating mesh index, name and lod."""
        meshes: List[MeshElement] = []
        for i in range(self.get_mesh_count()):
            meshes.append(self.get_mesh(i))
        return meshes

    # lods
    def get_lod_count(self) -> int:
        return cast(int, self._reader.getLODCount())

    def get_mesh_indices_for_lod(self, lod: int) -> List[int]:
        return cast(List[int], self._reader.getMeshIndicesForLOD(lod))

    # BEHAVIOR

    # GEOMETRY
    # neutral meshes
    def get_vertex_count(self, mesh_index: int) -> int:
        return cast(int, self._reader.getVertexPositionCount(mesh_index))

    def get_vertex_texture_coordinate_count(self, mesh_index: int) -> int:
        return cast(int, self._reader.getVertexTextureCoordinateCount(mesh_index))

    def get_vertex_uv_layout_count(self, mesh_index: int) -> int:
        return cast(int, self._reader.getVertexLayoutCount(mesh_index))

    def get_face_count(self, mesh_index: int) -> int:
        return cast(int, self._reader.getFaceCount(mesh_index))

    def get_face_vertex_layout_indices(self, mesh_index: int, face_index: int) -> List[int]:
        return self._reader.getFaceVertexLayoutIndices(mesh_index, face_index)

    def get_vertex_positions(self, mesh_index: int) -> List[Point3]:
        positions: List[Point3] = []
        vtx_count = self.get_vertex_count(mesh_index)
        pos_xs = self._reader.getVertexPositionXs(mesh_index)
        pos_ys = self._reader.getVertexPositionYs(mesh_index)
        pos_zs = self._reader.getVertexPositionZs(mesh_index)
        for v in range(vtx_count):
            point = Point3(pos_xs[v], pos_ys[v], pos_zs[v])
            positions.append(point)
        return positions

    def get_vertex_texture_coordinate(self, mesh_index: int) -> List[UV]:
        coordinates: List[UV] = []
        coord_count = self.get_vertex_texture_coordinate_count(mesh_index)
        for c in range(coord_count):
            u, v = self._reader.getVertexTextureCoordinate(mesh_index, c)
            coordinates.append(UV(u, v))
        return coordinates

    def get_vertex_layouts(self, mesh_index: int) -> List[VertexLayout]:
        layouts: List[VertexLayout] = []
        ly_count = self.get_vertex_uv_layout_count(mesh_index)
        for i in range(ly_count):
            vtx_index, uv_index, _ = self._reader.getVertexLayout(mesh_index, i)
            layouts.append(VertexLayout(vtx_index, uv_index))
        return layouts

    def get_vertex_layout(self, mesh_index: int, layout_index: int) -> VertexLayout:
        vtx_index, uv_index, normal_id = self._reader.getVertexLayout(mesh_index, layout_index)
        return VertexLayout(vtx_index, uv_index, normal_id)

    def get_face_vertex_indices(self, mesh_index: int) -> List[List[int]]:
        indices: List[List[int]] = []
        face_count = self.get_face_count(mesh_index)
        for f in range(face_count):
            vtx_ind = self._reader.getFaceVertexLayoutIndices(mesh_index, f)
            indices.append(vtx_ind)
        return indices

    # blend shapes
    def get_blend_shape_target_count(self, mesh_index: int) -> int:
        return cast(int, self._reader.getBlendShapeTargetCount(mesh_index))

    def get_blend_shape_targets(self, mesh_index: int) -> List[BlendShapeElement]:
        """Return list of BlendShapeElement objects agregating blend shape channel index, target index and name."""
        blend_shapes: List[BlendShapeElement] = []
        for t in range(self.get_blend_shape_target_count(mesh_index)):
            channel = self._reader.getBlendShapeChannelIndex(mesh_index, t)
            name = self._reader.getBlendShapeChannelName(channel)
            blend_shapes.append(BlendShapeElement(channel, t, name))
        return blend_shapes

    def get_blend_shape_deltas(self, mesh_index: int, target_index: int) -> List[BlendShapeDelta]:
        """Return list of BlendShapeDelta objects containing blend shape target deltas."""
        bs_deltas: List[BlendShapeDelta] = []
        delta_count = self._reader.getBlendShapeTargetDeltaCount(mesh_index, target_index)
        vtx_delta_indices = self._reader.getBlendShapeTargetVertexIndices(mesh_index, target_index)
        for d in range(delta_count):
            x, y, z = self._reader.getBlendShapeTargetDelta(mesh_index, target_index, d)
            delta = Point3(x, y, z)
            bs_deltas.append(BlendShapeDelta(vtx_delta_indices[d], delta))
        return bs_deltas

    def get_blend_shape_delta_indices(self, mesh_index: int, target_index: int) -> List[int]:
        """Return list of delta indices for given mesh and target."""
        return self._reader.getBlendShapeTargetVertexIndices(mesh_index, target_index)

    def get_blend_shape_delta_values(self, mesh_index: int, target_index: int) -> List[Point3]:
        """Return list of delta values for given mesh and target."""
        delta_values: List[Point3] = []
        delta_count = self._reader.getBlendShapeTargetDeltaCount(mesh_index, target_index)
        for d in range(delta_count):
            x, y, z = self._reader.getBlendShapeTargetDelta(mesh_index, target_index, d)
            delta_values.append(Point3(x, y, z))
        return delta_values

    # skin weights
    def get_maximum_influence_per_vertex(self, mesh_index: int) -> int:
        return cast(int, self._reader.getMaximumInfluencePerVertex(mesh_index))

    def get_skin_weights_joint_indices(self, mesh_index: int) -> List[List[int]]:
        """Return list of skinned joint indices for each vertex, for given mesh."""
        jnt_indices: List[List[int]] = []
        for vtx in range(self.get_vertex_count(mesh_index)):
            jnt_indices.append(self._reader.getSkinWeightsJointIndices(mesh_index, vtx))
        return jnt_indices

    def get_skin_weights_values(self, mesh_index: int) -> List[List[float]]:
        """Return list of skin weights for each vertex, for given mesh."""
        values: List[List[float]] = []
        for vtx in range(self.get_vertex_count(mesh_index)):
            values.append(self._reader.getSkinWeightsValues(mesh_index, vtx))
        return values

    def get_skin_weights(self, mesh_index: int) -> SkinClusterElement:
        """Return list of SkinWeightsElement objects agregating skinning data."""
        ipv = self.get_maximum_influence_per_vertex(mesh_index)
        sw = SkinClusterElement(ipv)
        sw.vtx_joint_indices = self.get_skin_weights_joint_indices(mesh_index)
        sw.vtx_weight_values = self.get_skin_weights_values(mesh_index)
        sw.all_joints = self.get_joints()
        sw.sw_joints = self._get_sw_joints(sw.all_joints, sw.vtx_joint_indices)
        return sw

    # PRIVATE
    def _map_mesh_lods(self) -> None:
        if self._map_mesh_lod is not None:
            return
        self._map_mesh_lod = {}
        for lod in range(self.get_lod_count()):
            mesh_indices = self.get_mesh_indices_for_lod(lod)
            for index in mesh_indices:
                self._map_mesh_lod[index] = lod

    def _get_sw_joints(self, joints: List[JointElement], vtx_joint_indices: List[List[int]]) -> List[JointElement]:
        sw_joints: List[JointElement] = []
        index_set: Set[int] = set()
        for jnts in vtx_joint_indices:
            index_set.update(jnts)
        index_list = list(index_set)
        index_list.sort()
        for jnt in index_list:
            sw_joints.append(joints[jnt])
        return sw_joints

    def get_vertex_normal(self, mesh_index: int, normal_id: int) -> Normal:
        x, y, z = self._reader.getVertexNormal(mesh_index, normal_id)
        return Normal(x, y, z)


class DNAReader:
    """
    Static class for handling DNA files.
    """

    @staticmethod
    def read(path: str, layer: Layer) -> DNA:
        """
        Reads DNA from given file path and creates DNA wrapper object.

        Raise: DNAReaderException
        """
        logging.debug(f"Reading DNA file: {path}.")
        stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
        reader = BinaryStreamReader(stream, layer.value)
        reader.read()
        if not Status.isOk():
            logging.error("DNA file unsuccessfully read.")
            status = Status.get()
            raise DNAReaderException(f"Error loading DNA: {status.message}")
        logging.debug("DNA file successfully read.")
        return DNA(path, reader)
