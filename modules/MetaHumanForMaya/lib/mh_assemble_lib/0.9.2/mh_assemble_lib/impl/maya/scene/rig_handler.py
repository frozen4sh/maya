# Copyright Epic Games, Inc. All Rights Reserved.
import logging
from types import ModuleType
from importlib.util import module_from_spec, spec_from_loader
from importlib.machinery import SourceFileLoader

from maya import mel, cmds

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.impl.maya.properties import MayaConfig


class MayaRigHandler:
    """
    Specialized Maya handler for handling rig logic.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config

    def import_gui_controls(self) -> None:
        """Import gui controls to scene."""
        logging.info(f"Importing gui controls: {self._form.gui_ctrls_path}.")
        self.import_scene(self._form.gui_ctrls_path, self._config.gui_ctrl_holder)
        self._position_gui_controls()
        self.add_raw_control_attributes()
        self.add_animated_map_attributes()

    def import_analog_controls(self) -> None:
        """Import analog controls to scene."""
        logging.info(f"Importing analog controls: {self._form.analog_ctrls_path}.")
        self.import_scene(self._form.analog_ctrls_path, self._config.analog_ctrl_holder)
        self._position_analog_controls()

    def create_rig_logic(self) -> None:
        """Create and connect rig logic node in scene."""
        logging.info("Creating RigLogic node.")
        char_name = self._dna.get_name()
        dna_path = self._dna.path.replace("\\", "/")
        combine = self._form.combine_bs_name
        cmd = self._config.get_rig_logic_cmd(char_name, dna_path, combine)
        logging.info(f"Mel command: {cmd}")
        mel.eval(cmd)

    def add_ctrl_attributes_on_facial_root(self) -> None:
        """Add raw controls on facial root joint. Needed for UE5."""
        logging.info("Adding control attributes on facial root.")
        skip = self._config.skip_raw_attr
        ctrls = self._dna.get_raw_controls()
        for ctrl in ctrls:
            if any(ctrl.attr_name == x for x in skip):
                continue
            self.add_float_attribute(self._config.facial_root_joint_name, ctrl.attr_name)

    def add_anim_map_attributes_on_facial_root(self) -> None:
        """Add animated maps attributes on facial root joint. Needed for UE5."""
        logging.info("Adding animated map attributes on facial root.")
        anim_maps = self._dna.get_animated_maps()
        for am in anim_maps:
            self.add_float_attribute(self._config.facial_root_joint_name, am.attr_name)

    def add_key_frames(self) -> None:
        """Add a key frame on facial root joint. Needed for UE5."""
        logging.info("Adding keyframe on facial root.")
        cmds.currentTime(0)
        cmds.select(self._config.facial_root_joint_name, replace=True)
        cmds.setKeyframe(inTangentType="linear", outTangentType="linear")

    def run_additional_assemble_script(self) -> None:
        """Run additional asseble script once rig is built."""
        logging.info(f"Running additional assemble script: {self._form.aas_path}.")
        script = self.source_module(self._config.aas_module_name, self._form.aas_path)
        script_method = getattr(script, self._config.aas_method)
        script_method(self._config.top_level_group, self._config.rig_group, {})

    def import_scene(self, path: str, group_name: str) -> None:
        cmds.file(path, i=True, groupReference=True, groupName=group_name)

    def add_raw_control_attributes(self) -> None:
        ctrls = self._dna.get_raw_controls()
        for ctrl in ctrls:
            self.add_float_attribute(ctrl.obj_name, ctrl.attr_name)

    def add_animated_map_attributes(self) -> None:
        anim_maps = self._dna.get_animated_maps()
        for am in anim_maps:
            self.add_float_attribute(self._config.animated_map_obj_name, am.attr_name)

    def add_float_attribute(self, obj_name: str, attr_name: str, min_val: float = 0.0, max_val: float = 1.0) -> None:
        cmds.addAttr(
            obj_name,
            longName=attr_name,
            keyable=True,
            attributeType="float",
            minValue=min_val,
            maxValue=max_val,
        )

    def source_module(self, name: str, path: str) -> ModuleType:
        spec = spec_from_loader(name, SourceFileLoader(name, path))
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _position_gui_controls(self) -> None:
        conf = self._config
        grp_name = conf.gui_ctrl_holder
        objs = [grp_name, conf.c_eye_ctrl, conf.l_eye_jnt]
        for obj_name in objs:
            if not cmds.objExists(obj_name):
                logging.warning(f"Unable to find object on scene: {obj_name}.")
                return
        gui_t = cmds.xform(conf.c_eye_ctrl, q=True, ws=True, t=True)
        joint_t = cmds.xform(conf.l_eye_jnt, q=True, ws=True, t=True)
        cmds.xform(grp_name, r=True, t=(0.0, joint_t[1] - gui_t[1], 0.0))

    def _position_analog_controls(self) -> None:
        conf = self._config
        objs = [
            conf.facial_root_joint_name,
            conf.l_eye_jnt,
            conf.l_eye_driver_loc,
            conf.l_eye_up_loc,
            conf.r_eye_jnt,
            conf.r_eye_driver_loc,
            conf.r_eye_up_loc,
            conf.c_eye_driver_loc,
            conf.c_eye_aim_grp,
            conf.l_eye_aim_grp,
            conf.r_eye_aim_grp,
        ]
        for obj_name in objs:
            if not cmds.objExists(obj_name):
                logging.warning(f"Unable to find object on scene: {obj_name}.")
                return

        root_jnt_t = cmds.xform(conf.facial_root_joint_name, q=True, ws=True, t=True)
        l_eye_jnt_t = cmds.xform(conf.l_eye_jnt, q=True, ws=True, t=True)
        l_eye_drv_loc_t = cmds.xform(conf.l_eye_driver_loc, q=True, ws=True, t=True)
        l_eye_up_loc_t = cmds.xform(conf.l_eye_up_loc, q=True, ws=True, t=True)
        r_eye_jnt_t = cmds.xform(conf.r_eye_jnt, q=True, ws=True, t=True)
        r_eye_drv_loc_t = cmds.xform(conf.r_eye_driver_loc, q=True, ws=True, t=True)
        r_eye_up_loc_t = cmds.xform(conf.r_eye_up_loc, q=True, ws=True, t=True)
        l_delta_up_loc_y = l_eye_up_loc_t[1] - l_eye_drv_loc_t[1]
        r_delta_up_loc_y = r_eye_up_loc_t[1] - r_eye_drv_loc_t[1]
        cmds.xform(conf.c_eye_driver_loc, ws=True, t=root_jnt_t)
        cmds.xform(conf.l_eye_driver_loc, ws=True, t=l_eye_jnt_t)
        cmds.xform(conf.r_eye_driver_loc, ws=True, t=r_eye_jnt_t)
        cmds.xform(conf.l_eye_up_loc, ws=True, t=(l_eye_jnt_t[0], l_eye_jnt_t[1] + l_delta_up_loc_y, l_eye_jnt_t[2]))
        cmds.xform(conf.r_eye_up_loc, ws=True, t=(r_eye_jnt_t[0], r_eye_jnt_t[1] + r_delta_up_loc_y, r_eye_jnt_t[2]))

        c_eye_aim_grp = cmds.xform(conf.c_eye_aim_grp, q=True, ws=True, t=True)
        l_eye_aim_grp = cmds.xform(conf.l_eye_aim_grp, q=True, ws=True, t=True)
        r_eye_aim_grp = cmds.xform(conf.r_eye_aim_grp, q=True, ws=True, t=True)
        mid_eye_x = (l_eye_jnt_t[0] + r_eye_jnt_t[0]) / 2.0
        mid_eye_y = (l_eye_jnt_t[1] + r_eye_jnt_t[1]) / 2.0
        cmds.xform(conf.c_eye_aim_grp, ws=True, t=(mid_eye_x, mid_eye_y, c_eye_aim_grp[2]))
        cmds.xform(conf.l_eye_aim_grp, ws=True, t=(l_eye_jnt_t[0], l_eye_jnt_t[1], l_eye_aim_grp[2]))
        cmds.xform(conf.r_eye_aim_grp, ws=True, t=(r_eye_jnt_t[0], r_eye_jnt_t[1], r_eye_aim_grp[2]))
