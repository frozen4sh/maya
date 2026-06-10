# Copyright Epic Games, Inc. All Rights Reserved.

from typing import TYPE_CHECKING, List, Optional
from dataclasses import field, dataclass

from .shader import Shader
from ..maya.symmetry import MayaVtxPairs

if TYPE_CHECKING:
    from .expression import Expression


class Mesh:
    """
    Mesh class.
    """

    def __init__(self):
        self.name: str = ""  # (string)
        self.file_exists: bool = False  # (boolean)
        self.file_path: str = ""  # (string)
        self.file_exists_symmetric: bool = False  # (boolean)
        self.file_symmetric_path: str = ""  # (string)
        self.shader: Optional[Shader] = None  # (Shader)
        self.maya_vtx_pairs: Optional[MayaVtxPairs] = None  # (MayaVtxPairs)

    def __str__(self):
        return self.name


class SplitMap:
    """
    SplitMap class.
    """

    def __init__(self):
        self.name: str = ""  # (string)
        self.mesh: Optional[Mesh] = None  # (Mesh)
        self.value: List[float] = []  # (float[])

    def __str__(self):
        return self.name


class MeshInExpression:
    """
    Class representing mesh which is deformed by expression.

    Mesh can be deformed by skin cluster, blend shape or both.
    """

    JOINTS = 1
    BLENDS = 2
    JOINTS_AND_BLENDS = 3

    def __init__(self):
        self.type: int = 0  # (int)
        self.mesh: Optional[Mesh] = None  # (Mesh)
        self.expression: Optional[Expression] = None  # (Expression)

    def __str__(self):
        exp_str = self.expression.name if self.expression else ""
        mesh_str = self.mesh.name if self.mesh else ""
        return exp_str + "_" + mesh_str

    def is_blends(self):
        """
        Indicates if mesh is deformed by blend shape.

        @return True if mesh has blend shape. (boolean)
        """

        return self.type in [MeshInExpression.BLENDS, MeshInExpression.JOINTS_AND_BLENDS]


@dataclass
class LodMeshes:
    """
    LodMeshes
    """

    name: Optional[str] = ""  # (pattern)
    meshes: List[str] = field(default_factory=list)  # (pattern[])

    def __str__(self):
        return self.name
