# Copyright Epic Games, Inc. All Rights Reserved.

"""
Wrapper classes for DNA data.
"""
from __future__ import annotations


class Point3:
    """
    Point in 3D space with x, y, z coordinates.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z

    def as_tuple(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    def vector_add(self, point: Point3) -> None:
        self.x += point.x
        self.y += point.y
        self.z += point.z


class UV:
    """
    UV coordinates.
    """

    def __init__(self, u: float = 0.0, v: float = 0.0):
        self.u: float = u
        self.v: float = v

    def as_tuple(self) -> tuple[float, float]:
        return (self.u, self.v)


class VertexLayout:
    """
    UV layout defining vertex index and UV index pairs.
    """

    def __init__(self, vtx_index: int, uv_index: int, normal_index: int = None):
        self.vtx_index: int = vtx_index
        self.uv_index: int = uv_index
        self.normal_index: int = normal_index


class JointElement:
    """
    DNA Joint wrapper class.
    """

    def __init__(self, index: int, name: str):
        self.index: int = index
        self.name: str = name
        self.translation: Point3 = Point3()
        self.rotation: Point3 = Point3()
        self.parent_index: int = index


class MeshElement:
    """
    DNA mesh wrapper class.
    """

    def __init__(self, index: int, name: str, lod: int):
        self.index: int = index
        self.name: str = name
        self.lod: int = lod
        self.poly_faces: list[int] = None
        self.poly_connections: list[int] = None


class BlendShapeElement:
    """
    DNA blend shape wrapper class.
    """

    def __init__(self, channel_index: int, tgt_index: int, name: str):
        self.channel_index: int = channel_index
        self.tgt_index: int = tgt_index
        self.name: str = name


class BlendShapeDelta:
    """
    DNA blend shape delta wrapper class.
    """

    def __init__(self, vtx_index: int, delta: Point3):
        self.vtx_index: int = vtx_index
        self.delta: Point3 = delta


class SkinClusterElement:
    """
    DNA skin cluster wrapper class.
    """

    def __init__(self, ipv: int):
        self.ipv: int = ipv
        self.all_joints: list[JointElement] = []
        self.sw_joints: list[JointElement] = []
        self.vtx_joint_indices: list[list[int]] = []
        self.vtx_weight_values: list[list[float]] = []

    def get_vertex_count(self) -> int:
        return len(self.vtx_joint_indices)

    def get_sw_joint_indices(self) -> list[int]:
        return [j.index for j in self.sw_joints]

    def get_sw_joint_names(self) -> list[str]:
        return [j.name for j in self.sw_joints]


class ControlElement:
    """
    DNA raw controll wrapper class.
    """

    def __init__(self, name: str):
        self.name: str = name
        self.obj_name: str = None
        self.attr_name: str = None
        self.obj_name, self.attr_name = self.name.split(".")


class AnimatedMapElement:
    """
    DNA animated map wrapper class.
    """

    def __init__(self, name: str):
        self.name: str = name
        self.attr_name: str = name.replace(".", "_")
        self.map_name: str = None
        self.mask_name: str = None
        self.map_name, self.mask_name = self.name.split(".")


class Normal:
    """Vertex Normal"""

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x: float = x
        self.y: float = y
        self.z: float = z

    def as_tuple(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z
