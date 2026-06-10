# Copyright Epic Games, Inc. All Rights Reserved.


from typing import List


class Config:
    """
    Base class that holds various application configuration properties.

    This class can be subclassed if needed to adapt configuration for specific context.
    """

    def __init__(self):
        # scene organization
        self.open_new_scene: bool = True
        self.top_level: str = "head"
        self.top_level_group: str = "head_grp"
        self.geometry_group: str = "geometry_grp"
        self.rig_group: str = "headRig_grp"
        self.group_by_lod: bool = True
        self.create_display_layers: bool = True

        # rig elements
        self.control_naming: str = "<objName>.<attrName>"

        self.facial_root_joint_name: str = "FACIAL_C_FacialRoot"
        self.joint_naming: str = "<objName>.<attrName>"

        self.blend_shape_group_prefix: str = "BlendshapeGroup_"
        self.blend_shape_name_postfix: str = "_blendShapes"
        self.blend_shape_naming_0: str = "<objName>_blendShapes.<attrName>"
        self.blend_shape_naming_1: str = "<objName>_blendShapes.<objName>__<attrName>"

        self.skin_cluster_suffix: str = "skinCluster"
        self.skin_weights_print_range: int = 2000

        self.animated_map_obj_name = "FRM_WMmultipliers"
        self.animated_map_naming: str = "FRM_WMmultipliers.<objName>_<attrName>"

        # gui
        self.gui_ctrl_holder = "gui"
        self.analog_ctrl_holder = "analog_gui"

        # rig logic
        self.rig_logic_command: str = "createEmbeddedNodeRL4"
        self.rig_logic_prefix: str = "rl4Embedded_"
        self.rig_logic_suffix: str = "Rig"

        # eyes setup
        self.c_eye_ctrl: str = "CTRL_C_eye"
        self.l_eye_jnt: str = "FACIAL_L_Eye"
        self.r_eye_jnt: str = "FACIAL_R_Eye"
        self.c_eye_driver_loc: str = "LOC_C_eyeDriver"
        self.l_eye_driver_loc: str = "LOC_L_eyeDriver"
        self.r_eye_driver_loc: str = "LOC_R_eyeDriver"
        self.l_eye_up_loc: str = "LOC_L_eyeAimUp"
        self.r_eye_up_loc: str = "LOC_R_eyeAimUp"
        self.c_eye_aim_grp: str = "GRP_C_eyesAim"
        self.l_eye_aim_grp: str = "GRP_L_eyeAim"
        self.r_eye_aim_grp: str = "GRP_R_eyeAim"

        # additional assemble script
        self.aas_module_name: str = "aas"
        self.aas_method: str = "run_after_assemble"

        # shader
        self.maps_relative_path: str = "/maps"
        self.map_file_ext: str = "tga"
        self.masks_relative_path: str = "/masks"
        self.mask_file_ext: str = "tga"

        self.map_names: List[str] = [
            "head_color",
            "head_cm1_color",
            "head_cm2_color",
            "head_cm3_color",
            "head_normal",
            "head_wm1_normal",
            "head_wm2_normal",
            "head_wm3_normal",
            "head_cavity",
            "head_roughness",
            "head_micro_normal",
            "teeth_color",
            "teeth_normal",
            "eyes_color",
            "eyes_normal",
            "eyelashes_color",
        ]
        self.mask_names: List[str] = [
            "head_wm13_lips_DL",
            "head_wm13_lips_DR",
            "head_wm13_lips_UL",
            "head_wm13_lips_UR",
            "head_wm1_blink_L",
            "head_wm1_blink_R",
            "head_wm1_browsRaiseInner_L",
            "head_wm1_browsRaiseInner_R",
            "head_wm1_browsRaiseOuter_L",
            "head_wm1_browsRaiseOuter_R",
            "head_wm1_chinRaise_L",
            "head_wm1_chinRaise_R",
            "head_wm1_jawOpen",
            "head_wm1_purse_DL",
            "head_wm1_purse_DR",
            "head_wm1_purse_UL",
            "head_wm1_purse_UR",
            "head_wm1_squintInner_L",
            "head_wm1_squintInner_R",
            "head_wm2_browsDown_L",
            "head_wm2_browsDown_R",
            "head_wm2_browsLateral_L",
            "head_wm2_browsLateral_R",
            "head_wm2_mouthStretch_L",
            "head_wm2_mouthStretch_R",
            "head_wm2_neckStretch_L",
            "head_wm2_neckStretch_R",
            "head_wm2_noseWrinkler_L",
            "head_wm2_noseWrinkler_R",
            "head_wm3_cheekRaiseInner_L",
            "head_wm3_cheekRaiseInner_R",
            "head_wm3_cheekRaiseOuter_L",
            "head_wm3_cheekRaiseOuter_R",
            "head_wm3_cheekRaiseUpper_L",
            "head_wm3_cheekRaiseUpper_R",
            "head_wm3_smile_L",
            "head_wm3_smile_R",
        ]

    def get_lod_group_name(self, lod: int) -> str:
        return f"{self.top_level}_lod{lod}_grp"

    def get_lod_layer_name(self, lod: int) -> str:
        return f"{self.top_level}_lod{lod}_layer"

    def get_bs_naming(self, combine: bool) -> str:
        if combine:
            return self.blend_shape_naming_1
        return self.blend_shape_naming_0

    def get_bs_group_name(self, mesh_name: str) -> str:
        return f"{self.blend_shape_group_prefix}{mesh_name}"

    def get_bs_node_name(self, mesh_name: str) -> str:
        return f"{mesh_name}{self.blend_shape_name_postfix}"

    def get_bs_channel_name(self, mesh_name: str, bs_name: str, combine: bool) -> str:
        if combine:
            return f"{mesh_name}__{bs_name}"
        return bs_name

    def get_skin_cluster_name(self, mesh_name: str) -> str:
        return f"{mesh_name}_{self.skin_cluster_suffix}"

    def get_sw_attr_name(self, mesh_name: str, vtx: int, jnt: int) -> str:
        sc = self.get_skin_cluster_name(mesh_name)
        return f"{sc}.wl[{str(vtx)}].w[{str(jnt)}]"

    def get_rig_logic_node_name(self, char_name: str) -> str:
        if char_name:
            return f"{self.rig_logic_prefix}{char_name}"
        return f"{self.rig_logic_prefix}{self.rig_logic_suffix}"

    def get_rig_logic_cmd(self, char_name: str, dna_path: str, combine: bool) -> str:
        cmd = f"{self.rig_logic_command}"
        cmd += f' -n "{self.get_rig_logic_node_name(char_name)}"'
        cmd += f' -dfp "{dna_path}"'
        cmd += f' -cn "{self.control_naming}"'
        cmd += f' -jn "{self.joint_naming}"'
        cmd += f' -bsn "{self.get_bs_naming(combine)}"'
        cmd += f' -amn "{self.animated_map_naming}";'
        return cmd

    def get_map_file_path(self, shader_dir: str, map_name: str, ext: str) -> str:
        return f"{shader_dir}{self.maps_relative_path}/{map_name}_map.{ext}"

    def get_mask_file_path(self, shader_dir: str, mask_name: str, ext: str) -> str:
        return f"{shader_dir}{self.masks_relative_path}/{mask_name}_msk.{ext}"
