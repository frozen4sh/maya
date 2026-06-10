# Copyright Epic Games, Inc. All Rights Reserved.

import logging

from maya import cmds

from .core import BaseHandler, MayaSceneError
from ..model.maya.joint import MayaJoint, MayaJointDataHolder
from ..model.maya.symmetry import MayaSymmetryInfo

logger = logging.getLogger("frt_api.maya.joint")


class JointMayaHandler(BaseHandler):
    """
    Joints Maya handler.

    Contains methods for manipulation with joint objects in scene.
    @see BaseHandler
    """

    # Constants
    TRANSLATE_PRUNE = 0.0001
    ROTATE_PRUNE = 0.1
    SCALE_PRUNE = 0.001

    LAYER_JOINTS = "joints_layer"

    def __init__(self):
        super().__init__()

    # ---------------------------
    # Scene joint methods
    # ---------------------------
    @staticmethod
    def get_selected_joints_from_scene(ws=False):
        """
        Gets selected Maya joint objects from scene.

        @param ws: Return attributes in world space. (boolean)
        @return List of MayaJoints which are NOT organized into hierarchy. (maya.node.MayaJoint[])
        """

        logger.debug("Get selected joints from scene.")
        maya_joints = []
        selected_joints = cmds.ls(sl=True, type="joint")
        for joint_name in selected_joints:
            maya_joint = MayaJoint()
            maya_joint.name = joint_name
            maya_joint.override_enabled = int(cmds.getAttr(f"{joint_name}.overrideEnabled"))
            maya_joint.override_color = cmds.getAttr(f"{joint_name}.overrideColor")
            maya_joint.joint_orient = list(*cmds.getAttr(f"{joint_name}.jointOrient"))
            maya_joint.radius = cmds.getAttr(f"{joint_name}.radius")
            maya_joint.scale = list(*cmds.getAttr(f"{joint_name}.scale"))
            if ws:
                maya_joint.translate = cmds.xform(maya_joint.name, query=True, translation=True, ws=True)
                maya_joint.rotate = cmds.xform(maya_joint.name, query=True, rotation=True, ws=True)
            else:
                maya_joint.translate = list(*cmds.getAttr(f"{joint_name}.translate"))
                maya_joint.rotate = list(*cmds.getAttr(f"{joint_name}.rotate"))
            maya_joints.append(maya_joint)
        return maya_joints

    def _get_joints_names_hierarchy_from_scene(self, root_joint, joints_list=None):
        if joints_list is None:
            joints_list = []
        joints_list.append(root_joint)
        for child in root_joint.children:
            self._get_joints_names_hierarchy_from_scene(child, joints_list)
        return joints_list

    def get_joints_from_scene(self, joint_data, frame=None, ws=False):
        """
        Gets Maya joint objects from scene, based on given list of Joint beans.

        @param joint_data: Maya joint data holder. (maya.node.DataHolder)
        @param frame: Frame from which joints will be read. If none, current frame will be used. (int)
        @param ws: Return attributes in world space. (boolean)
        @return Maya joint data holder containing MayaJoints. (maya.node.MayaJointDataHolder)
        @throws MayaSceneError: If joint doesn't exist or bean joints hierarchy is not same as on scene.
        """

        logger.debug("Get joints from scene for given joint data.")
        maya_joints = []

        current_time = cmds.currentTime(query=True)
        if frame:
            cmds.currentTime(frame)

        for jointBean in joint_data:
            maya_joint = self._get_joint_from_scene(jointBean, ws)
            maya_joints.append(maya_joint)

        if frame:
            cmds.currentTime(current_time)

        return MayaJointDataHolder(maya_joints)

    def _get_joint_from_scene(self, joint_bean, ws=False):
        """
        Creates MayaJoint object based on given joint bean object.

        @param joint_bean: Joint bean object. (Joint)
        @param ws: Return attributes in world space. (boolean)
        @throws MayaSceneError: If joint doesn't exist or bean joints hierarchy is not same as on scene.
        """

        # get joint node
        joint_name = self.get_object(joint_bean.name, type="joint", root=False, strict=True)

        # check joint hierarchy
        if joint_bean.parent:
            parent_name = cmds.listRelatives(joint_name, parent=True)[0]
            if not (parent_name and parent_name == joint_bean.parent.name):
                raise MayaSceneError("Wrong joint hierarchy for joint : " + joint_bean.name)

        maya_joint = MayaJoint()
        maya_joint.name = joint_bean.name
        maya_joint.override_enabled = int(cmds.getAttr(f"{joint_name}.overrideEnabled"))
        maya_joint.override_color = cmds.getAttr(f"{joint_name}.overrideColor")
        maya_joint.scale = list(*cmds.getAttr(f"{joint_name}.scale"))
        maya_joint.joint_orient = list(*cmds.getAttr(f"{joint_name}.jointOrient"))
        maya_joint.radius = cmds.getAttr(f"{joint_name}.radius")

        if ws:
            maya_joint.translate = cmds.xform(maya_joint.name, query=True, translation=True, ws=True)
            maya_joint.rotate = cmds.xform(maya_joint.name, query=True, rotation=True, ws=True)
        else:
            maya_joint.translate = list(*cmds.getAttr(f"{joint_name}.translate"))
            maya_joint.rotate = list(*cmds.getAttr(f"{joint_name}.rotate"))

        # recursive call
        for child_joint in joint_bean.children:
            child_maya_joint = self._get_joint_from_scene(child_joint, ws)
            maya_joint.children.append(child_maya_joint)
            child_maya_joint.parent = maya_joint
        return maya_joint

    @staticmethod
    def set_joints_to_scene(joints, ws=False, select=False):
        """
        Sets joint attributes to values given in list.

        Joints hierarchy is not checked, and missing joints are not created.
        @param joints: List of Maya joints objects which are NOT in hierarchy. (maya.node.MayaJoint[])
        @param ws: Joint attribute values are given in world space. (boolean)
        @param select: Indicates if joints has to be selected once they are pasted. (bool)
        @throws MayaSceneError: If joint doesn't exist or there are multiple joints with same pattern on scene.
        """

        logger.debug("Set joints to scene for given joints list.")
        select_list = []
        for maya_joint in joints:
            # get joint node
            joint_names = cmds.ls(maya_joint.name, type="joint")
            if len(joint_names) > 1:
                raise MayaSceneError("Multiple joints with pattern: " + maya_joint.name)
            if len(joint_names) == 0:
                raise MayaSceneError("Unable to find joint with pattern: " + maya_joint.name)
            joint_name = joint_names[0]

            # set joint
            cmds.setAttr(f"{joint_name}.jointOrient", *maya_joint.joint_orient)
            if ws:
                cmds.xform(
                    maya_joint.name,
                    translation=maya_joint.translate,
                    rotation=maya_joint.rotate,
                    ws=True,
                    absolute=True,
                )
            else:
                cmds.setAttr(f"{joint_name}.translate", *maya_joint.translate)
                cmds.setAttr(f"{joint_name}.rotate", *maya_joint.rotate)
            cmds.setAttr(f"{joint_name}.scale", *maya_joint.scale)
            cmds.setAttr(f"{joint_name}.radius", maya_joint.radius)
            select_list.append(joint_name)
        if select:
            cmds.select(select_list, replace=True)

    def setJointsToScene(self, joint_data, ws=False):
        """
        Sets Maya joint objects to scene.

        @param joint_data: Maya joint data holder. (maya.node.MayaJointDataHolder)
        @param ws: Set attributes in world space. (boolean)
        @throws MayaSceneError: If joint hierarchy is not same as on scene.
        """

        logger.debug("Set joints to scene for given joint data.")
        for maya_joint in joint_data.get_all_elements():
            # get joint node
            joint_name = cmds.ls(maya_joint.name, type="joint")
            if len(joint_name) > 1:
                raise MayaSceneError("Multiple joints with pattern: " + maya_joint.name)
            if len(joint_name) == 0:
                joint = cmds.joint(name=maya_joint.name)
                cmds.setAttr(f"{joint}.overrideEnabled", maya_joint.override_enabled)
                cmds.setAttr(f"{joint}.overrideColor", maya_joint.override_color)
            else:
                joint = joint_name[0]

            # check hierarchy
            joint_parent = cmds.listRelatives(joint, parent=True)
            if maya_joint.parent and ((joint_parent is None) or (joint_parent[0] != maya_joint.parent.name)):
                parent_nodes = cmds.ls(maya_joint.parent.name, type="joint")
                if len(parent_nodes) != 1:
                    raise MayaSceneError("Wrong joint hierarchy for joint : " + maya_joint.name)
                cmds.parent(joint, parent_nodes[0])

            if (maya_joint.parent is None) and (cmds.listRelatives(joint, parent=True) is not None):
                raise MayaSceneError("Wrong joint hierarchy for joint : " + maya_joint.name)

            cmds.setAttr(f"{joint}.jointOrient", *maya_joint.joint_orient)
            if ws:
                cmds.xform(
                    maya_joint.name,
                    translation=maya_joint.translate,
                    rotation=maya_joint.rotate,
                    ws=True,
                    absolute=True,
                )
            else:
                cmds.setAttr(f"{joint}.translate", *maya_joint.translate)
                cmds.setAttr(f"{joint}.rotate", *maya_joint.rotate)
            cmds.setAttr(f"{joint}.scale", *maya_joint.scale)
            cmds.setAttr(f"{joint}.radius", maya_joint.radius)
            cmds.setAttr(f"{joint}.segmentScaleCompensate", 0)

            # add to layer
            if not maya_joint.parent:
                joints_layer = self.get_display_layer(self.LAYER_JOINTS, self.COLOR_LAYER_JOINTS)
                cmds.editDisplayLayerMembers(joints_layer, joint, noRecurse=True)

    def append_joints_to_scene(self, joint_data, ws=False):
        """
        Sets Maya joint objects to scene.

        Joints are added to scene if joint with same pattern does not exist.
        Otherwise, existing joint is not changed.
        @param joint_data: Maya joint data holder. (maya.node.MayaJointDataHolder)
        @param ws: Return attributes in world space. (boolean)
        @throws MayaSceneError: If joint hierarchy is not same as on scene.
        """

        logger.debug("Append joints to scene for given joint data.")

        for mayaJoint in joint_data.get_all_elements():
            # get joint node
            joint_names = cmds.ls(mayaJoint.name, type="joint")
            if len(joint_names) > 1:
                raise MayaSceneError("Multiple joints with pattern: " + mayaJoint.name)
            if len(joint_names) == 0:
                joint_name = cmds.joint(name=mayaJoint.name)
                cmds.setAttr(f"{joint_name}.overrideEnabled", mayaJoint.override_enabled)
                cmds.setAttr(f"{joint_name}.overrideColor", mayaJoint.override_color)

                if mayaJoint.parent:
                    parent_nodes = cmds.ls(mayaJoint.parent.name, type="joint")
                    if len(parent_nodes) != 1:
                        raise MayaSceneError("Wrong joint hierarchy for joint : " + mayaJoint.name)
                    cmds.parent(joint_name, parent_nodes[0])

                cmds.setAttr(f"{joint_name}.jointOrient", mayaJoint.joint_orient)
                if ws:
                    cmds.xform(mayaJoint.name, t=mayaJoint.translate, ro=mayaJoint.rotate, ws=True, absolute=True)
                else:
                    cmds.setAttr(f"{joint_name}.translate", *mayaJoint.translate)
                    cmds.setAttr(f"{joint_name}.rotate", *mayaJoint.rotate)
                cmds.setAttr(f"{joint_name}.scale", *mayaJoint.scale)
                cmds.setAttr(f"{joint_name}.radius", mayaJoint.radius)
                cmds.setAttr(f"{joint_name}.segmentScaleCompensate", 0)
            else:
                joint_name = joint_names[0]

            # add to layer
            if not mayaJoint.parent:
                joints_layer = self.get_display_layer(self.LAYER_JOINTS, self.COLOR_LAYER_JOINTS)
                cmds.editDisplayLayerMembers(joints_layer, joint_name, noRecurse=True)

    # ---------------------------
    # Driven key methods
    # ---------------------------
    def set_driven_key_for_neutral_joints(self, joints_naming_dict, joints_data, add_key_on_root=False):
        """
        Sets time-line driven keys for neutral expression for joints in scene.

        These driven key do NOT have drivers.
        @param joints_naming_dict: Dictionary contains joint naming mapping. ({string: string})
        @param joints_data: Maya joint data holder containing MayaJoints. (maya.node.MayaJointDataHolder)
        @param add_key_on_root: Indicates if keyframes should be added on root joints. (boolean)
        """

        logger.debug("Set driven keys for neutral joints in scene.")
        for mayaJoint in joints_data.get_all_elements():
            # do not apply for root joints
            if mayaJoint.parent or add_key_on_root:
                # check if joint is analog
                joint_name = mayaJoint.name
                if mayaJoint.name in joints_naming_dict:
                    joint_name = joints_naming_dict[mayaJoint.name]
                # add neutral driven keys
                cmds.setKeyframe(joint_name, attribute="translateX")
                cmds.setKeyframe(joint_name, attribute="translateY")
                cmds.setKeyframe(joint_name, attribute="translateZ")
                cmds.setKeyframe(joint_name, attribute="rotateX")
                cmds.setKeyframe(joint_name, attribute="rotateY")
                cmds.setKeyframe(joint_name, attribute="rotateZ")
                cmds.setKeyframe(joint_name, attribute="scaleX")
                cmds.setKeyframe(joint_name, attribute="scaleY")
                cmds.setKeyframe(joint_name, attribute="scaleZ")

    def set_driven_key_for_expression_joints(
        self,
        joints_naming_dict,
        driver,
        start_value,
        end_values,
        neutral_joints_data,
        phases_joints_data,
        use_pruning=True,
    ):
        """
        Sets driven keys for expression phase joints.

        @param joints_naming_dict: Dictionary contains joint naming mapping. ({string: string})
        @param driver: Driver object and attribute. (string)
        @param start_value: Driver start value. (float)
        @param end_values: Driver end values, one for each phase. (float[])
        @param neutral_joints_data: Maya joint data holder containing neutral MayaJoints. (MayaJointDataHolder)
        @param phases_joints_data: List of Maya joint data holder containing phase MayaJoints. (MayaJointDataHolder[])
        @param use_pruning: Indicates if prune changes less than prune values should be considered. (boolean)
        """

        logger.debug("Set driven keys for joints for driver: " + driver)
        for neutral_joint in neutral_joints_data.get_all_elements():
            phases_joints = []
            for phase_jnts_data in phases_joints_data:
                phase_jnt = phase_jnts_data.get_element(neutral_joint.name)
                if phase_jnt:
                    phases_joints.append(phase_jnt)

            # check if joint is analog
            joint_name = neutral_joint.name
            if neutral_joint.name in joints_naming_dict:
                joint_name = joints_naming_dict[neutral_joint.name]

            if use_pruning:
                translate_prune = JointMayaHandler.TRANSLATE_PRUNE
                rotate_prune = JointMayaHandler.ROTATE_PRUNE
                scale_prune = JointMayaHandler.SCALE_PRUNE
            else:
                translate_prune = 0.0
                rotate_prune = 0.0
                scale_prune = 0.0

            if_driven_keys = [False, False, False, False, False, False, False, False, False]
            for phase_joint in phases_joints:
                if abs(neutral_joint.translate[0] - phase_joint.translate[0]) > translate_prune:
                    if_driven_keys[0] = True
                if abs(neutral_joint.translate[1] - phase_joint.translate[1]) > translate_prune:
                    if_driven_keys[1] = True
                if abs(neutral_joint.translate[2] - phase_joint.translate[2]) > translate_prune:
                    if_driven_keys[2] = True
                if abs(neutral_joint.rotate[0] - phase_joint.rotate[0]) > rotate_prune:
                    if_driven_keys[3] = True
                if abs(neutral_joint.rotate[1] - phase_joint.rotate[1]) > rotate_prune:
                    if_driven_keys[4] = True
                if abs(neutral_joint.rotate[2] - phase_joint.rotate[2]) > rotate_prune:
                    if_driven_keys[5] = True
                if abs(neutral_joint.scale[0] - phase_joint.scale[0]) > scale_prune:
                    if_driven_keys[6] = True
                if abs(neutral_joint.scale[1] - phase_joint.scale[1]) > scale_prune:
                    if_driven_keys[7] = True
                if abs(neutral_joint.scale[2] - phase_joint.scale[2]) > scale_prune:
                    if_driven_keys[8] = True

            # add driven keys
            if if_driven_keys[0]:
                cmds.setDrivenKeyframe(
                    joint_name + ".translateX",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.translate[0] - neutral_joint.translate[0]
                    cmds.setDrivenKeyframe(
                        joint_name + ".translateX",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[1]:
                cmds.setDrivenKeyframe(
                    joint_name + ".translateY",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.translate[1] - neutral_joint.translate[1]
                    cmds.setDrivenKeyframe(
                        joint_name + ".translateY",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[2]:
                cmds.setDrivenKeyframe(
                    joint_name + ".translateZ",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.translate[2] - neutral_joint.translate[2]
                    cmds.setDrivenKeyframe(
                        joint_name + ".translateZ",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[3]:
                cmds.setDrivenKeyframe(
                    joint_name + ".rotateX",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.rotate[0] - neutral_joint.rotate[0]
                    cmds.setDrivenKeyframe(
                        joint_name + ".rotateX",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[4]:
                cmds.setDrivenKeyframe(
                    joint_name + ".rotateY",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.rotate[1] - neutral_joint.rotate[1]
                    cmds.setDrivenKeyframe(
                        joint_name + ".rotateY",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[5]:
                cmds.setDrivenKeyframe(
                    joint_name + ".rotateZ",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.rotate[2] - neutral_joint.rotate[2]
                    cmds.setDrivenKeyframe(
                        joint_name + ".rotateZ",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[6]:
                cmds.setDrivenKeyframe(
                    joint_name + ".scaleX",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.scale[0] - neutral_joint.scale[0]
                    cmds.setDrivenKeyframe(
                        joint_name + ".scaleX",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[7]:
                cmds.setDrivenKeyframe(
                    joint_name + ".scaleY",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.scale[1] - neutral_joint.scale[1]
                    cmds.setDrivenKeyframe(
                        joint_name + ".scaleY",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            if if_driven_keys[8]:
                cmds.setDrivenKeyframe(
                    joint_name + ".scaleZ",
                    currentDriver=driver,
                    driverValue=start_value,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                for i, phase_joint in enumerate(phases_joints):
                    val = phase_joint.scale[2] - neutral_joint.scale[2]
                    cmds.setDrivenKeyframe(
                        joint_name + ".scaleZ",
                        currentDriver=driver,
                        driverValue=end_values[i],
                        value=val,
                        inTangentType="linear",
                        outTangentType="linear",
                    )

    def mirror_joints(self, neutral_joints, maya_symmetry_info):
        """
        Mirrors joints asymmetric in scene.

        If no joint is selected mirrors all joints.
        @param neutral_joints: Maya joint data holder. (maya.node.MayaJointDataHolder)
        @param maya_symmetry_info: Mirror info. (maya.node.MayaSymmetryInfo)
        @return True if successfully mirrored. (boolean)
        """
        logger.debug("Mirror joints.")
        try:
            cmds.undoInfo(openChunk=True)

            # get scene joints
            src_joints = self.get_selected_joints_from_scene()

            # prepare data
            mirror_src_label = (
                maya_symmetry_info.left_label
                if maya_symmetry_info.mirror_direction == MayaSymmetryInfo.LEFT_TO_RIGHT
                else maya_symmetry_info.right_label
            )
            mirror_dest_label = (
                maya_symmetry_info.left_label
                if maya_symmetry_info.mirror_direction == MayaSymmetryInfo.RIGHT_TO_LEFT
                else maya_symmetry_info.right_label
            )

            # mirror joints
            for srcJoint in src_joints:
                dest_joint_name = MayaSymmetryInfo.get_joint_mirror_name(
                    srcJoint.name, mirror_src_label, mirror_dest_label, maya_symmetry_info.filter
                )

                if not dest_joint_name or (
                    (not neutral_joints.has_element(dest_joint_name) or not neutral_joints.has_element(srcJoint.name))
                    and (
                        not neutral_joints.has_element(dest_joint_name.split("|")[-1])
                        or not neutral_joints.has_element(srcJoint.name.split("|")[-1])
                    )
                ):
                    continue
                dest_joint_node_name = self.get_object(dest_joint_name, type="joint")

                if not dest_joint_node_name:
                    continue

                neutral_src_joint = neutral_joints.get_element(srcJoint.name)
                neutral_dest_joint = neutral_joints.get_element(dest_joint_name)
                if not neutral_src_joint or not neutral_dest_joint:
                    neutral_src_joint = neutral_joints.get_element(srcJoint.name.split("|")[-1])
                    neutral_dest_joint = neutral_joints.get_element(dest_joint_name.split("|")[-1])

                diff_joint = srcJoint.delta(neutral_src_joint)

                try:
                    cmds.setAttr(
                        f"{dest_joint_node_name}.scale",
                        *[
                            neutral_dest_joint.scale[0] + diff_joint.scale[0],
                            neutral_dest_joint.scale[1] + diff_joint.scale[1],
                            neutral_dest_joint.scale[2] + diff_joint.scale[2],
                        ],
                    )
                except RuntimeError:
                    continue

                if maya_symmetry_info.joint_orientation == MayaSymmetryInfo.JOINT_ORIENTATION_ORIENTATION:
                    if maya_symmetry_info.mirror_plane == MayaSymmetryInfo.MIRROR_PLANE_XY:
                        cmds.setAttr(
                            f"{dest_joint_node_name}.translate",
                            *[
                                neutral_dest_joint.translate[0] + diff_joint.translate[0],
                                neutral_dest_joint.translate[1] + diff_joint.translate[1],
                                neutral_dest_joint.translate[2] - diff_joint.translate[2],
                            ],
                        )
                        cmds.setAttr(
                            f"{dest_joint_node_name}.rotate",
                            *[
                                neutral_dest_joint.rotate[0] - diff_joint.rotate[0],
                                neutral_dest_joint.rotate[1] - diff_joint.rotate[1],
                                neutral_dest_joint.rotate[2] + diff_joint.rotate[2],
                            ],
                        )
                    if maya_symmetry_info.mirror_plane == MayaSymmetryInfo.MIRROR_PLANE_XZ:
                        cmds.setAttr(
                            f"{dest_joint_node_name}.translate",
                            *[
                                neutral_dest_joint.translate[0] + diff_joint.translate[0],
                                neutral_dest_joint.translate[1] - diff_joint.translate[1],
                                neutral_dest_joint.translate[2] + diff_joint.translate[2],
                            ],
                        )
                        cmds.setAttr(
                            f"{dest_joint_node_name}.rotate",
                            *[
                                neutral_dest_joint.rotate[0] - diff_joint.rotate[0],
                                neutral_dest_joint.rotate[1] + diff_joint.rotate[1],
                                neutral_dest_joint.rotate[2] - diff_joint.rotate[2],
                            ],
                        )
                    if maya_symmetry_info.mirror_plane == MayaSymmetryInfo.MIRROR_PLANE_YZ:
                        cmds.setAttr(
                            f"{dest_joint_node_name}.translate",
                            *[
                                neutral_dest_joint.translate[0] - diff_joint.translate[0],
                                neutral_dest_joint.translate[1] + diff_joint.translate[1],
                                neutral_dest_joint.translate[2] + diff_joint.translate[2],
                            ],
                        )
                        cmds.setAttr(
                            f"{dest_joint_node_name}.rotate",
                            *[
                                neutral_dest_joint.rotate[0] + diff_joint.rotate[0],
                                neutral_dest_joint.rotate[1] - diff_joint.rotate[1],
                                neutral_dest_joint.rotate[2] - diff_joint.rotate[2],
                            ],
                        )
                elif maya_symmetry_info.joint_orientation == MayaSymmetryInfo.JOINT_ORIENTATION_BEHAVIOR:
                    cmds.setAttr(
                        f"{dest_joint_node_name}.translate",
                        *[
                            neutral_dest_joint.translate[0] - diff_joint.translate[0],
                            neutral_dest_joint.translate[1] - diff_joint.translate[1],
                            neutral_dest_joint.translate[2] - diff_joint.translate[2],
                        ],
                    )
                    cmds.setAttr(
                        f"{dest_joint_node_name}.rotate",
                        *[
                            neutral_dest_joint.rotate[0] + diff_joint.rotate[0],
                            neutral_dest_joint.rotate[1] + diff_joint.rotate[1],
                            neutral_dest_joint.rotate[2] + diff_joint.rotate[2],
                        ],
                    )
        except Exception:  # pylint: disable=try-except-raise
            raise
        finally:
            cmds.undoInfo(closeChunk=True)

    def flip_joints(self, neutral_joints, maya_symmetry_info):
        """
        Flips joints asymmetric in scene.

        If no joint is selected flips all joints.
        @param neutral_joints: Maya joint data holder. (maya.node.MayaJointDataHolder)
        @param maya_symmetry_info: Mirror info. (maya.node.MayaSymmetryInfo)
        @return True if successfully flipped. (boolean)
        """

        logger.debug("Flip joints.")
        try:
            cmds.undoInfo(openChunk=True)
            joint_selection = [joint.name for joint in self.get_selected_joints_from_scene()]

            for joint_name in joint_selection:
                dest_joint_name = MayaSymmetryInfo.get_joint_mirror_name(
                    joint_name,
                    maya_symmetry_info.left_label,
                    maya_symmetry_info.right_label,
                    maya_symmetry_info.filter,
                )
                if not dest_joint_name:
                    dest_joint_name = MayaSymmetryInfo.get_joint_mirror_name(
                        joint_name,
                        maya_symmetry_info.right_label,
                        maya_symmetry_info.left_label,
                        maya_symmetry_info.filter,
                    )
                if dest_joint_name:
                    dest_joint_node = self.get_object(dest_joint_name, type="joint")
                    if dest_joint_node:
                        cmds.select(dest_joint_node, add=True)

            # get scene joints
            src_joints = self.get_selected_joints_from_scene()
            cmds.select(joint_selection, replace=True)

            # flip joints
            for srcJoint in src_joints:
                dest_joint_name = MayaSymmetryInfo.get_joint_mirror_name(
                    srcJoint.name,
                    maya_symmetry_info.left_label,
                    maya_symmetry_info.right_label,
                    maya_symmetry_info.filter,
                )
                if not dest_joint_name:
                    dest_joint_name = MayaSymmetryInfo.get_joint_mirror_name(
                        srcJoint.name,
                        maya_symmetry_info.right_label,
                        maya_symmetry_info.left_label,
                        maya_symmetry_info.filter,
                    )
                # for central joints
                if not dest_joint_name and (
                    neutral_joints.has_element(srcJoint.name)
                    or neutral_joints.has_element(srcJoint.name.split("|")[-1])
                ):
                    dest_joint_name = srcJoint.name
                if not dest_joint_name or (
                    (not neutral_joints.has_element(dest_joint_name) or not neutral_joints.has_element(srcJoint.name))
                    and (
                        not neutral_joints.has_element(dest_joint_name.split("|")[-1])
                        or not neutral_joints.has_element(srcJoint.name.split("|")[-1])
                    )
                ):
                    continue
                dest_joint_node = self.get_object(dest_joint_name, type="joint")
                if not dest_joint_node:
                    continue

                neutral_src_joint = neutral_joints.get_element(srcJoint.name)
                neutral_dest_joint = neutral_joints.get_element(dest_joint_name)
                if not neutral_src_joint or not neutral_dest_joint:
                    neutral_src_joint = neutral_joints.get_element(srcJoint.name.split("|")[-1])
                    neutral_dest_joint = neutral_joints.get_element(dest_joint_name.split("|")[-1])
                diff_joint = srcJoint.delta(neutral_src_joint)

                try:
                    cmds.xform(
                        dest_joint_node,
                        scale=[
                            neutral_dest_joint.scale[0] + diff_joint.scale[0],
                            neutral_dest_joint.scale[1] + diff_joint.scale[1],
                            neutral_dest_joint.scale[2] + diff_joint.scale[2],
                        ],
                    )
                except RuntimeError:
                    continue

                if maya_symmetry_info.joint_orientation == MayaSymmetryInfo.JOINT_ORIENTATION_ORIENTATION:
                    if maya_symmetry_info.mirror_plane == MayaSymmetryInfo.MIRROR_PLANE_XY:
                        cmds.xform(
                            dest_joint_node,
                            translation=[
                                neutral_dest_joint.translate[0] + diff_joint.translate[0],
                                neutral_dest_joint.translate[1] + diff_joint.translate[1],
                                neutral_dest_joint.translate[2] - diff_joint.translate[2],
                            ],
                        )
                        cmds.xform(
                            dest_joint_node,
                            rotation=[
                                neutral_dest_joint.rotate[0] - diff_joint.rotate[0],
                                neutral_dest_joint.rotate[1] - diff_joint.rotate[1],
                                neutral_dest_joint.rotate[2] + diff_joint.rotate[2],
                            ],
                        )
                    if maya_symmetry_info.mirror_plane == MayaSymmetryInfo.MIRROR_PLANE_XZ:
                        cmds.xform(
                            dest_joint_node,
                            translation=[
                                neutral_dest_joint.translate[0] + diff_joint.translate[0],
                                neutral_dest_joint.translate[1] - diff_joint.translate[1],
                                neutral_dest_joint.translate[2] + diff_joint.translate[2],
                            ],
                        )
                        cmds.xform(
                            dest_joint_node,
                            rotation=[
                                neutral_dest_joint.rotate[0] - diff_joint.rotate[0],
                                neutral_dest_joint.rotate[1] + diff_joint.rotate[1],
                                neutral_dest_joint.rotate[2] - diff_joint.rotate[2],
                            ],
                        )
                    if maya_symmetry_info.mirror_plane == MayaSymmetryInfo.MIRROR_PLANE_YZ:
                        cmds.xform(
                            dest_joint_node,
                            translation=[
                                neutral_dest_joint.translate[0] - diff_joint.translate[0],
                                neutral_dest_joint.translate[1] + diff_joint.translate[1],
                                neutral_dest_joint.translate[2] + diff_joint.translate[2],
                            ],
                        )
                        cmds.xform(
                            dest_joint_node,
                            rotation=[
                                neutral_dest_joint.rotate[0] + diff_joint.rotate[0],
                                neutral_dest_joint.rotate[1] - diff_joint.rotate[1],
                                neutral_dest_joint.rotate[2] - diff_joint.rotate[2],
                            ],
                        )
                elif maya_symmetry_info.joint_orientation == MayaSymmetryInfo.JOINT_ORIENTATION_BEHAVIOR:
                    cmds.xform(
                        dest_joint_node,
                        translation=[
                            neutral_dest_joint.translate[0] - diff_joint.translate[0],
                            neutral_dest_joint.translate[1] - diff_joint.translate[1],
                            neutral_dest_joint.translate[2] - diff_joint.translate[2],
                        ],
                    )
                    cmds.xform(
                        dest_joint_node,
                        rotation=[
                            neutral_dest_joint.rotate[0] + diff_joint.rotate[0],
                            neutral_dest_joint.rotate[1] + diff_joint.rotate[1],
                            neutral_dest_joint.rotate[2] + diff_joint.rotate[2],
                        ],
                    )
        except Exception:  # pylint: disable=try-except-raise
            raise
        finally:
            cmds.undoInfo(closeChunk=True)

    def set_to_neutral_joints(self, neutral_joints):
        """
        Set joints to neutral pose in scene.

        If no joint is selected sets all joints to neutral.
        @param neutral_joints: Maya joint data holder. (maya.node.MayaJointDataHolder)
        @return True if successfully set to neutral. (boolean)
        """

        logger.debug("Set joints to neutral.")
        try:
            cmds.undoInfo(openChunk=True)
            joint_selection = self.get_selected_joints_from_scene()

            # set to neutral joints
            for joint in joint_selection:
                if neutral_joints.has_element(joint.name):
                    neutral_joint = neutral_joints.get_element(joint.name)
                elif neutral_joints.has_element(joint.name.split("|")[-1]):
                    neutral_joint = neutral_joints.get_element(joint.name.split("|")[-1])
                else:
                    continue
                cmds.xform(f"{joint.name}", translation=neutral_joint.translate)
                cmds.xform(f"{joint.name}", rotation=neutral_joint.rotate)
                cmds.xform(f"{joint.name}", scale=neutral_joint.scale)
        except Exception:  # pylint: disable=try-except-raise
            raise
        finally:
            cmds.undoInfo(closeChunk=True)

    def scale_scene_expression_joints(self, scale, joints_data):
        """
        Scale scene expression by scale coefficient.

        If no joint is selected scale all joints.
        @param scale: Scale factor. (float)
        @param joints_data: Maya joint data holder. (maya.node.MayaJointDataHolder)
        @return True if successfully calculated. (boolean)
        """

        logger.debug("Scale selected joints expression.")
        try:
            cmds.undoInfo(openChunk=True)
            if joints_data is None:
                raise RuntimeWarning("Neutral joints not found")

            # get scene joints
            src_joints = self.get_selected_joints_from_scene()

            # set to neutral joints
            for src_joint in src_joints:
                resolved_neutral_joint = src_joint.name
                if not joints_data.has_element(src_joint.name):
                    resolved_neutral_joint = src_joint.name.split("|")[-1]
                if not joints_data.has_element(resolved_neutral_joint):
                    continue
                neutral_joint = joints_data.get_element(resolved_neutral_joint)

                src_joint.multiply(scale, neutral_joint)

                cmds.xform(f"{src_joint.name}", translation=src_joint.translate)
                cmds.xform(f"{src_joint.name}", rotation=src_joint.rotate)
                cmds.xform(f"{src_joint.name}", scale=src_joint.scale)
        finally:
            cmds.undoInfo(closeChunk=True)

    def neutralize_scene_expression_joints_by_master(
        self, source_neutral_joints, master_neutral_joints, master_expression_joints
    ):
        """
        This function will neutralize joints in scene in way that joints that
        do not move in master character on give expression do not move in scene either.

        If no joint is selected scale all joints.
        @param character: Character whose joints are scaled. (CharacterDef)
        @param masterCharacter: Master character pattern. (string)
        @param expression_name: Expression to neutralize scene joints by. (string)
        @return True if successfully calculated. (boolean)
        """

        logger.debug("Scale selected joints expression.")
        try:
            # source expression joints
            src_expression_joints = self.get_joints_from_scene(source_neutral_joints)

            # open undo chunk
            cmds.undoInfo(openChunk=True)

            for srcJoint in src_expression_joints.get_all_elements():
                m_neutral_joint = master_neutral_joints.get_element(srcJoint.name)
                m_exp_joint = master_expression_joints.get_element(srcJoint.name)
                src_neutral_joint = source_neutral_joints.get_element(srcJoint.name)
                if not m_neutral_joint.compare_change(m_exp_joint, 0.000001) and src_neutral_joint.compare_change(
                    srcJoint, 0.000001
                ):
                    # set joint to neutral
                    joint_name = self.get_object(srcJoint.name, type="joint", root=False, strict=True)
                    cmds.setAttr(f"{joint_name}.translate", *src_neutral_joint.translate)
                    cmds.setAttr(f"{joint_name}.rotate", *src_neutral_joint.rotate)
                    cmds.setAttr(f"{joint_name}.scale", *src_neutral_joint.scale)
        finally:
            # close undo chunk
            cmds.undoInfo(closeChunk=True)
        return True
