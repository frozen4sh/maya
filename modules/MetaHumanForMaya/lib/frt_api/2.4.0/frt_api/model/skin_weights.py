# Copyright Epic Games, Inc. All Rights Reserved.
from typing import Any, List


class MayaSkinWeights:
    """
    Represents Maya mesh skin weights.

    It can represent 3 different skinning methods:
    METHOD_CLASSIC_LINEAR: Linear skinning method.

    Attributes:
        no_of_influences (int): Maximum number of joint influences per vertex.
        skinning_method (int): Skinning method.
        joints (string[]): List of strings representing influence object names.
        vertices_info (float[][]): Float matrix representing influences per vertex.
            vertices_info[i][j]:
            i: Represents vertex index. Each vertex has its own row.
            j: Each row is made of list of numbers. Odd numbers represents
                influence object index (int). Even numbers represent influence
                weight of previous influence object (float).
    """

    METHOD_CLASSIC_LINEAR = 0

    def __init__(self):
        self.no_of_influences: int = 0
        self.skinning_method: int = MayaSkinWeights.METHOD_CLASSIC_LINEAR
        self.joints: List[str] = []
        self.vertices_info: List[List[Any]] = []

    def copy(self):
        """
        Makes deep copy of a MayaSkinWeights object and all of its inner data.

        @return Copy of self. (MayaJointDataHolder)
        """

        new_sw = MayaSkinWeights()
        new_sw.no_of_influences = self.no_of_influences
        new_sw.skinning_method = self.skinning_method
        new_sw.joints = self.joints[:]
        new_sw.vertices_info = [vi[:] for vi in self.vertices_info]
        return new_sw

    def get_weights_matrix(self):
        """
        Converts MayaSkinWeights.vertices_info data into [nVertices, nJoints] list of lists.
        First index (rows) represents vertex index number, while second index (columns) represents
        joint number. (weights[vtxId][jntId])

        @return Matrix containing skin weights. (float[nVerts, nJoints])
        """

        number_of_vertices = len(self.vertices_info)
        number_of_joints = len(self.joints)
        weights: List[List[Any]] = [[] for i in range(number_of_vertices)]

        for vertex_id, vtx_info in enumerate(self.vertices_info):
            vertex_weights: List[Any] = [0.0 for i in range(number_of_joints)]
            for in_w in range(0, len(vtx_info), 2):
                vertex_weights[vtx_info[in_w]] = vtx_info[in_w + 1]
            weights[vertex_id] = vertex_weights

        return weights

    def get_influence_names_map(self, threshold=0.000001):
        """
        Returns influence map of this skin.

        @return List of sets of influence indices (int) for every vertex. ([set(int[])])
        """

        return [
            {self.joints[vertex_info[i]] for i in range(0, len(vertex_info), 2) if vertex_info[i + 1] > threshold}
            for vertex_info in self.vertices_info
        ]
