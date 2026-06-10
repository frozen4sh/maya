# Copyright Epic Games, Inc. All Rights Reserved.
import logging
from typing import List

from maya import cmds

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.model.element import JointElement
from mh_assemble_lib.impl.maya.properties import MayaConfig
from mh_assemble_lib.impl.maya.scene.util import Util


class MayaJointHandler:
    """
    Specialized Maya handler for handling joints.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config
        self._joints: List[JointElement] = []

    def create_joints(self) -> None:
        """Create joints hierarchy on scene."""
        logging.info("Creating joints.")
        self.init_neutral_joints()
        for joint in self._joints:
            self.add_joint_to_scene(joint)
        if self._config.group_by_lod:
            self.parent_root_joints()

    def init_neutral_joints(self) -> None:
        self._joints = self._dna.get_neutral_joints()

    def add_joint_to_scene(self, joint: JointElement) -> None:
        scene_orient = self._config.scene_orient
        in_parent_space = True
        position = joint.translation
        orientation = joint.rotation
        cmds.select(d=True)
        if joint.index == joint.parent_index:
            in_parent_space = False
            position = Util.point3_to_position(joint.translation, scene_orient)
            orientation = Util.point3_to_orientation(joint.rotation, scene_orient)
        else:
            in_parent_space = True
            parent_name = self._joints[joint.parent_index].name
            cmds.select(parent_name)
        cmds.joint(
            p=position.as_tuple(),
            o=orientation.as_tuple(),
            n=joint.name,
            r=in_parent_space,
            a=not in_parent_space,
            scaleCompensate=False,
        )

    def parent_root_joints(self) -> None:
        for joint in self._joints:
            if joint.index == joint.parent_index:
                cmds.parent(joint.name, self._config.top_level_group)
