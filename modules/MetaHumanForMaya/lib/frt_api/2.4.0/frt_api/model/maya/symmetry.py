# Copyright Epic Games, Inc. All Rights Reserved.

import math


class MayaSymmetryInfo:
    """
    Represents flip mirror option information.

    Attributes:
        filter (int): Indicates where in joint pattern is included joint side information (left, center or right).
            There are three filters: contains, starts with and ends with.
        left_label (string): String which indicates that it is on left side.
        right_label (string): String which indicates that it is on right side.
        mirror_direction (int): Mirroring direction.
            It can be: left to right and right to left.
        joint_orientation:
        mirror_plane (int): Indicates across which plane will be done mirroring.
            There are three options: XY, XZ and YZ plane.
    """

    # Constants
    LEFT_TO_RIGHT = 1
    RIGHT_TO_LEFT = 2

    MIRROR_PLANE_XY = 2
    MIRROR_PLANE_XZ = 1
    MIRROR_PLANE_YZ = 0

    JOINT_ORIENTATION_ORIENTATION = 1
    JOINT_ORIENTATION_BEHAVIOR = 2

    NAME_CONTAINS = 1
    NAME_STARTS_WITH = 2
    NAME_ENDS_WITH = 3

    def __init__(self, filter, left_label, right_label, mirror_direction, joint_orientation, rig_definition):
        self.filter = filter
        self.left_label = left_label
        self.right_label = right_label
        self.mirror_direction = mirror_direction
        self.joint_orientation = joint_orientation
        self.mirror_plane = MayaSymmetryInfo.get_mirror_plane(rig_definition)

    @staticmethod
    def get_mirror_plane(rig_definition):
        """
        Gets mirror plane for given rig definition.

        @param rig_definition: Rig definition. (RigDefinition)
        @return Mirror plane. (int)
        """

        directions = [False, False, False]
        if rig_definition.rig_up in ["X-", "X+"] or rig_definition.rig_front in ["X-", "X+"]:
            directions[0] = True
        if rig_definition.rig_up in ["Y-", "Y+"] or rig_definition.rig_front in ["Y-", "Y+"]:
            directions[1] = True
        if rig_definition.rig_up in ["Z-", "Z+"] or rig_definition.rig_front in ["Z-", "Z+"]:
            directions[2] = True
        if not directions[1]:
            return MayaSymmetryInfo.MIRROR_PLANE_XZ
        if not directions[2]:
            return MayaSymmetryInfo.MIRROR_PLANE_XY
        return MayaSymmetryInfo.MIRROR_PLANE_YZ

    @staticmethod
    def get_joint_mirror_name(name, mirror_src_label, mirror_dest_label, filter):
        """
        Gets mirror joint pattern for given joint.

        @param name: Origin joint pattern whose mirror joint pattern is being calculated. (string)
        @param mirror_src_label: String which pattern has to contain in order to have mirror pair. (string)
        @param mirror_dest_label: String which will be replaced instead of mirrorSrcLabel in order to create mirror pair pattern. (string)
        @param filter: Filter indicating whether mirrorSrcLabel should be on beginning, middle or end of joint pattern. (int)
        @return Joint mirror pair pattern. Empty string if joint doesn't have pair. (string)
        """

        if filter == MayaSymmetryInfo.NAME_CONTAINS:
            if name.find(mirror_src_label) != -1:
                return name.replace(mirror_src_label, mirror_dest_label)
            return ""
        if filter == MayaSymmetryInfo.NAME_ENDS_WITH:
            if name.endswith(mirror_src_label):
                return name[: -len(mirror_src_label)] + mirror_dest_label
            return ""
        if filter == MayaSymmetryInfo.NAME_STARTS_WITH:
            if name.startswith(mirror_src_label):
                return mirror_dest_label + name[len(mirror_src_label) :]
            return ""
        return ""


class MayaVtxPair:
    """
    Represents vertex pair.

    Attributes:
        id: Vertex index. (int)
        pairs: List of vertex ids which are pair to given vertex by some criteria. (int[])
        side: Describes vertex side, whether if it is on left or right side. (int)
        pos: Vertex x, y, z position. (float[])
        dist: Distance of vertex from [0.0, 0.0, 0.0]. (float)
    """

    # Constants
    SIDE_RIGHT = 2
    SIDE_LEFT = 1
    SIDE_CENTRAL = 0

    def __init__(self, id_=0, pos=None):
        self.id = id_
        self.pairs = []
        self.side = MayaVtxPair.SIDE_LEFT

        self.pos = [0.0, 0.0, 0.0]
        self.dist = 0.0
        if pos:
            self.pos = pos
            self.dist = math.sqrt(pos[0] * pos[0] + pos[1] * pos[1] + pos[2] * pos[2])


class MayaVtxPairs:
    """
    Represents information about vertex pairs on a single mesh.

    Attributes:
        vtx_pairs: List of MayaVtxPair objects. (MayaVtxPair[])
    """

    def __init__(self):
        self.vtx_pairs = []
