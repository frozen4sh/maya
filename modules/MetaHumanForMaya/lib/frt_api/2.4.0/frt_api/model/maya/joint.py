# Copyright Epic Games, Inc. All Rights Reserved.
from typing import List, Union, Optional

from ..rig_definition.core import DataHolder, DataElement


class MayaJoint(DataElement):
    """
    Represents Maya scene joint node.

    This class also inherits DataElement. By doing that, this class can be used
    in DataHolder classes as element.

    Attributes:
        name (string): Joint pattern.
        override_enabled (int): Represents Maya joint overrideEnabled attribute.
        override_color (int): Represents Maya joint override_color attribute.
        translate ([float, float, float]): Joint parent space translations.
        rotate ([float, float, float]): Joint parent space rotations.
        scale ([float, float, float]): Joint parent space scale.
        joint_orient ([float, float, float]): Joint orientation.
        radius (float): Joint radius size.
        parent (MayaJoint): Parent joint.
        children (MayaJoint[]): List of child joints.

    @see .util.DataElement
    """

    def __init__(self):
        self.name: str = ""
        self.override_enabled: int = 0
        self.override_color: int = 0
        self.translate: List[float] = [0.0, 0.0, 0.0]
        self.rotate: List[float] = [0.0, 0.0, 0.0]
        self.scale: List[float] = [0.0, 0.0, 0.0]
        self.joint_orient: List[float] = [0.0, 0.0, 0.0]
        self.radius: float = 1

        self.parent: Optional[MayaJoint] = None
        self.children: List[MayaJoint] = []

    def shallow_copy(self) -> "MayaJoint":
        new = MayaJoint()
        new.name = self.name
        new.override_enabled = self.override_enabled
        new.override_color = self.override_color
        new.translate = self.translate[:]
        new.rotate = self.rotate[:]
        new.scale = self.scale[:]
        new.joint_orient = self.joint_orient[:]
        new.radius = self.radius
        new.parent = self.parent
        new.children = self.children[:]
        return new

    def get_value(self, name: str) -> Optional[Union[float, List]]:
        """
        Gets translate, rotate or scale attribute value based on given
        string input.

        @param name: Attribute pattern. (string)
        @return Attribute value for given string pattern. (float)
        """

        name = name.lower()

        if name in ("t", "translate"):
            return self.translate[:]
        if name in ("tx", "translatex"):
            return self.translate[0]
        if name in ("ty", "translatey"):
            return self.translate[1]
        if name in ("tz", "translatez"):
            return self.translate[2]

        if name in ("r", "rotate"):
            return self.rotate[:]
        if name in ("rx", "rotatex"):
            return self.rotate[0]
        if name in ("ry", "rotatey"):
            return self.rotate[1]
        if name in ("rz", "rotatez"):
            return self.rotate[2]

        if name in ("s", "scale"):
            return self.scale[:]
        if name in ("sx", "scalex"):
            return self.scale[0]
        if name in ("sy", "scaley"):
            return self.scale[1]
        if name in ("sz", "scalez"):
            return self.scale[2]

        return None

    # other methods
    def delta(self, neutral: "MayaJoint") -> "MayaJoint":
        """
        Returns joint delta (joint - neutral).

        @param neutral: Joint in neutral position. Constant. (MayaJoint)
        @return Joint delta. (MayaJoint)
        """

        result = self.shallow_copy()
        result.translate[0] -= neutral.translate[0]
        result.translate[1] -= neutral.translate[1]
        result.translate[2] -= neutral.translate[2]
        result.rotate[0] -= neutral.rotate[0]
        result.rotate[1] -= neutral.rotate[1]
        result.rotate[2] -= neutral.rotate[2]
        result.scale[0] -= neutral.scale[0]
        result.scale[1] -= neutral.scale[1]
        result.scale[2] -= neutral.scale[2]
        return result

    def add(self, joint: "MayaJoint", neutral: "MayaJoint"):
        """
        Adds joint to self.
        This method changes self.
        Formula: self = self + joint - neutral.

        @param joint: Joint which will be added to self. Constant. (MayaJoint)
        @param neutral: Joint in neutral position. Constant. (MayaJoint)
        """

        self.translate[0] += joint.translate[0] - neutral.translate[0]
        self.translate[1] += joint.translate[1] - neutral.translate[1]
        self.translate[2] += joint.translate[2] - neutral.translate[2]
        self.rotate[0] += joint.rotate[0] - neutral.rotate[0]
        self.rotate[1] += joint.rotate[1] - neutral.rotate[1]
        self.rotate[2] += joint.rotate[2] - neutral.rotate[2]
        self.scale[0] += joint.scale[0] - neutral.scale[0]
        self.scale[1] += joint.scale[1] - neutral.scale[1]
        self.scale[2] += joint.scale[2] - neutral.scale[2]

    def subtract(self, joint: "MayaJoint", neutral: "MayaJoint"):
        """
        Subtracts joint from self.
        This method changes self.
        Formula: self = self - joint + neutral.

        @param joint: Joint which will be subtracted from self. Constant. (MayaJoint)
        @param neutral: Joint in neutral position. Constant. (MayaJoint)
        """

        self.translate[0] = self.translate[0] - joint.translate[0] + neutral.translate[0]
        self.translate[1] = self.translate[1] - joint.translate[1] + neutral.translate[1]
        self.translate[2] = self.translate[2] - joint.translate[2] + neutral.translate[2]
        self.rotate[0] = self.rotate[0] - joint.rotate[0] + neutral.rotate[0]
        self.rotate[1] = self.rotate[1] - joint.rotate[1] + neutral.rotate[1]
        self.rotate[2] = self.rotate[2] - joint.rotate[2] + neutral.rotate[2]
        self.scale[0] = self.scale[0] - joint.scale[0] + neutral.scale[0]
        self.scale[1] = self.scale[1] - joint.scale[1] + neutral.scale[1]
        self.scale[2] = self.scale[2] - joint.scale[2] + neutral.scale[2]

    def multiply(self, coef: float, neutral: "MayaJoint"):
        """
        Multiplies joint with coefficient.
        This method changes self.
        Formula: self = coef * self - (1 - coef) * neutral.

        @param coef: Multiply coefficient. Constant. (float)
        @param neutral: Joint in neutral position. Constant. (MayaJoint)
        """

        self.translate[0] = coef * self.translate[0] + (1 - coef) * neutral.translate[0]
        self.translate[1] = coef * self.translate[1] + (1 - coef) * neutral.translate[1]
        self.translate[2] = coef * self.translate[2] + (1 - coef) * neutral.translate[2]
        self.rotate[0] = coef * self.rotate[0] + (1 - coef) * neutral.rotate[0]
        self.rotate[1] = coef * self.rotate[1] + (1 - coef) * neutral.rotate[1]
        self.rotate[2] = coef * self.rotate[2] + (1 - coef) * neutral.rotate[2]
        self.scale[0] = coef * self.scale[0] + (1 - coef) * neutral.scale[0]
        self.scale[1] = coef * self.scale[1] + (1 - coef) * neutral.scale[1]
        self.scale[2] = coef * self.scale[2] + (1 - coef) * neutral.scale[2]

    def compare_change(self, joint: "MayaJoint", threshold: float = 0.0) -> bool:
        """
        Compares self with given joint if there is difference between joint
        positions with given threshold.

        Values which are compared are: translate, rotate, scale and joint_orient.
        @param joint: Joint. Constant. (MayaJoint)
        @param threshold: Comparison threshold. (float)
        @return True if change exists, False otherwise. (boolean)
        """

        for diff in [self.translate[i] - joint.translate[i] for i in range(3)]:
            if abs(diff) > threshold:
                return True
        for diff in [self.rotate[i] - joint.rotate[i] for i in range(3)]:
            if abs(diff) > threshold:
                return True
        for diff in [self.scale[i] - joint.scale[i] for i in range(3)]:
            if abs(diff) > threshold:
                return True
        return any(abs(diff) > threshold for diff in [self.joint_orient[i] - joint.joint_orient[i] for i in range(3)])


class MayaJointDataHolder(DataHolder):
    """
    Class holding Maya scene joints data.

    Inherits .util.DataHolder class.
    This class implements method for joints data manipulation as well.

    @see .util.DataHolder
    @see MayaJoint
    """

    def copy(self) -> "MayaJointDataHolder":
        """
        Makes deep copy of a MayaJointDataHolder object and all of its
        inner data.

        @return Copy of self. (MayaJointDataHolder)
        """

        new_joint_list = []
        new_joint_dict = {}
        for joint in self._node_list:
            new_joint = joint.shallow_copy()
            new_joint.children = []
            new_joint_list.append(new_joint)
            new_joint_dict[new_joint.name] = new_joint
        new_root_joint_list = []
        for new_joint in new_joint_list:
            if new_joint.parent:
                new_joint.parent = new_joint_dict[new_joint.parent.name]
                new_joint.parent.children.append(new_joint)
            else:
                new_root_joint_list.append(new_joint)

        return MayaJointDataHolder(new_root_joint_list)

    def get_all_joint_names(self) -> List[str]:
        """
        Gets a list of all joints names sorted first in depth.

        @return List of joint names (string[])
        """

        return [elem.name for elem in self._node_list]

    def add(self, jnt_data_holder: "MayaJointDataHolder", neutral_data_holder: "MayaJointDataHolder"):
        """
        Adds joints data to self.
        This method changes self.
        Formula: self = self + joint - neutral.

        @param jnt_data_holder: Data holder containing joint which will be added. Constant. (MayaJointDataHolder)
        @param neutral_data_holder: Data holder containing neutral joints. Constant. (MayaJointDataHolder)
        """

        for self_joint in self._node_list:
            pose_joint = jnt_data_holder.get_element(self_joint.name)
            neutral_joint = neutral_data_holder.get_element(self_joint.name)
            if pose_joint and neutral_joint:
                self_joint.add(pose_joint, neutral_joint)

    def subtract(self, jnt_data_holder: "MayaJointDataHolder", neutral_data_holder: "MayaJointDataHolder"):
        """
        Subtracts joints data from self.
        This method changes self.
        Formula: self = self - joint + neutral.

        @param jnt_data_holder: Data holder containing joint which will be subtracted. Constant. (MayaJointDataHolder)
        @param neutral_data_holder: Data holder containing neutral joints. Constant. (MayaJointDataHolder)
        """

        for self_joint in self._node_list:
            pose_joint = jnt_data_holder.get_element(self_joint.name)
            neutral_joint = neutral_data_holder.get_element(self_joint.name)
            if pose_joint and neutral_joint:
                self_joint.subtract(pose_joint, neutral_joint)

    def multiply(self, coef: float, neutral_data_holder: "MayaJointDataHolder"):
        """
        Multiplies self with coefficient.
        This method changes self.
        Formula: self = coef * self + (1 - coef) * neutral.

        @param coef: Multiply coefficient. (float)
        @param neutral_data_holder: Data holder containing neutral joints. Constant. (MayaJointDataHolder)
        """

        for self_joint in self._node_list:
            neutral_joint = neutral_data_holder.get_element(self_joint.name)
            if neutral_joint:
                self_joint.multiply(coef, neutral_joint)

    def scale(self, scale: float, pivot: List[float]):
        """
        Scales Maya joint for given scale and pivot.
        This method changes self. It changes translate and radius values.
        Formula: if root joint: self = pivot + (self - pivot) * scale,
                 if not root joint: self = self * scale.

        @param scale: Scale coefficient. (float)
        @param pivot: Scale pivot point. (float[])
        """

        for self_joint in self._node_list:
            if self_joint in self._root_list:
                self_joint.translate[0] = pivot[0] + (self_joint.translate[0] - pivot[0]) * scale
                self_joint.translate[1] = pivot[1] + (self_joint.translate[1] - pivot[1]) * scale
                self_joint.translate[2] = pivot[2] + (self_joint.translate[2] - pivot[2]) * scale
            else:
                self_joint.translate[0] *= scale
                self_joint.translate[1] *= scale
                self_joint.translate[2] *= scale
            self_joint.radius *= scale
