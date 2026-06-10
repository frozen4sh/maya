# Copyright Epic Games, Inc. All Rights Reserved.
from typing import List, Optional

from .core import DataElement


class Joint(DataElement):
    """
    Joint class.
    """

    def __init__(self):
        super().__init__()
        self.name: str = ""  # (string)
        self.parent: Optional[Joint] = None  # (Joint)
        self.children: List[Joint] = []  # (Joint[])
        self.analog_joint: int = 0  # (int)
        self.sdk_jnt_name: str = ""  # (string)
        self.analog_jnt_name: str = ""  # (string)
        self.off_grp_name: str = ""  # (string)
        self.analog_ctrl_name: str = ""  # (string)
        self.override_color: int = 12  # Default joint color
        self.override_enabled: int = 0  # Default override enabled
        self.radius: float = 1.0  # Default joint radius

    def __str__(self):
        return self.name


class JointGroup:
    """
    JointGroup class.
    """

    def __init__(self):
        self.name: str = ""  # (string)
        self.joints: List[Joint] = []  # (Joint[])

    def __str__(self):
        return self.name

    def intersection(self, joints: List[Joint]) -> List[Joint]:
        """
        Calculates intersection of 2 joint lists.

        Function is member of JointGroup class but takes list of joints
        as argument and returns list of joints instead of joint group.
        @param joints: List of joints. (Joint[])
        @return Joints intersection. (Joint[])
        """

        intersection = []
        for joint in self.joints:
            if joint in joints:
                intersection.append(joint)
        return intersection

    def union(self, joints: List[Joint]) -> List[Joint]:
        """
        Calculates union of 2 joint lists.

        Function is member of JointGroup class but takes list of joints
        as argument and returns list of joints instead of joint group.
        @param joints: List of joints. (Joint[])
        @return Joints union. (Joint[])
        """

        union = self.joints[:]
        for joint in joints:
            if joint not in union:
                union.append(joint)
        return union

    def difference(self, joints: List[Joint]) -> List[Joint]:
        """
        Calculates difference of 2 joint lists.

        Function is member of JointGroup class but takes list of joints
        as argument and returns list of joints instead of joint group.
        @param joints: List of joints. (Joint[])
        @return Joints difference. (Joint[])
        """

        difference = []
        for joint in self.joints:
            if joint not in joints:
                difference.append(joint)
        return difference


class SplitJoint:
    """
    SplitJoint class.
    """

    def __init__(self):
        self.multiplier: float = 0.0  # (float)
        self.joint_group: Optional[JointGroup] = None  # (JointGroup)
        self.rotations: List[float] = [0.0, 0.0, 0.0]  # (float[])

    def __str__(self):
        return self.joint_group.name if self.joint_group else ""
