# Copyright Epic Games, Inc. All Rights Reserved.

from math import pi
from typing import List, Tuple, Optional

from maya.OpenMaya import MObject, MFnDagNode, MSelectionList
from maya.api.OpenMaya import (
    MPoint,
    MSpace,
    MMatrix,
    MVector,
    MEulerRotation,
    MTransformationMatrix,
)

from mh_assemble_lib.model.element import Normal, Point3
from mh_assemble_lib.impl.maya.properties import MayaSceneOrient


def create_matrix(
    translation: Optional[Tuple[float, float, float]] = None,
    rotation: Optional[Tuple[float, float, float]] = None,
    scale: Optional[Tuple[float, float, float]] = None,
) -> MMatrix:
    translation = MVector(translation or [0.0, 0.0, 0.0])
    rotation = rotation or [
        0.0,
        0.0,
        0.0,
    ]
    rotation = MEulerRotation([v * pi / 180.0 for v in rotation])
    scale = scale or [1.0, 1.0, 1.0]

    transformation_matrix = MTransformationMatrix()
    transformation_matrix.setTranslation(translation, MSpace.kWorld)
    transformation_matrix.setRotation(rotation)
    transformation_matrix.setScale(scale, MSpace.kWorld)
    return transformation_matrix.asMatrix()


def get_translation_from_matrix(matrix: MMatrix) -> List[float]:
    return list(MTransformationMatrix(matrix).translation(MSpace.kWorld))


def get_rotation_from_matrix(matrix: MMatrix) -> List[float]:
    return [v * 180 / pi for v in MTransformationMatrix(matrix).rotation()]


def rotate_matrix(
    source_translation: Optional[Tuple[float, float, float]] = None,
    source_rotation: Optional[Tuple[float, float, float]] = None,
    source_scale: Optional[Tuple[float, float, float]] = None,
    rotation: Optional[Tuple[float, float, float]] = None,
) -> MMatrix:
    matrix = create_matrix(translation=source_translation, rotation=source_rotation, scale=source_scale)
    rotation_matrix = create_matrix(rotation=rotation)
    return matrix * rotation_matrix


class Util:
    @staticmethod
    def point3_to_mpoint(point: Point3, scene_orient: MayaSceneOrient) -> MPoint:
        modified_translation_matrix = rotate_matrix(
            source_translation=point.as_tuple(), rotation=scene_orient.root_orient_delta.as_tuple()
        )
        return MPoint(get_translation_from_matrix(modified_translation_matrix))

    @staticmethod
    def point3_to_position(point: Point3, scene_orient: MayaSceneOrient) -> Point3:
        modified_translation_matrix = rotate_matrix(
            source_translation=point.as_tuple(), rotation=scene_orient.root_orient_delta.as_tuple()
        )
        return Point3(*get_translation_from_matrix(modified_translation_matrix))

    @staticmethod
    def point3_to_orientation(point: Point3, scene_orient: MayaSceneOrient) -> Point3:
        modified_rotation_matrix = rotate_matrix(
            source_rotation=point.as_tuple(), rotation=scene_orient.root_orient_delta.as_tuple()
        )
        return Point3(*get_rotation_from_matrix(modified_rotation_matrix))

    @staticmethod
    def normal_to_mvector(normal: Normal, scene_orient: MayaSceneOrient) -> MVector:
        modified_translation_matrix = rotate_matrix(
            source_translation=normal.as_tuple(), rotation=scene_orient.root_orient_delta.as_tuple()
        )
        return MVector(*get_translation_from_matrix(modified_translation_matrix))

    @staticmethod
    def get_mobject(obj_name: str) -> MObject:
        sel = MSelectionList()
        sel.add(obj_name)
        mobj = MObject()
        sel.getDependNode(0, mobj)
        return mobj

    @staticmethod
    def get_shape(m_object: MObject) -> MObject:
        fn_item = MFnDagNode(m_object)
        return fn_item.child(0)
