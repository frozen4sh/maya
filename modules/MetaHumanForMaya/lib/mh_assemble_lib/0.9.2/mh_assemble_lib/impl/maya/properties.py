# Copyright Epic Games, Inc. All Rights Reserved.

from __future__ import annotations

import logging
from enum import Enum

from mh_assemble_lib.model.element import Point3
from mh_assemble_lib.control.properties import Config


class MayaSceneOrient:
    Y_UP_ORIENT_DELTA = Point3(0.0, 0.0, 0.0)
    Z_UP_ORIENT_DELTA = Point3(90.0, 0.0, 0.0)

    class UpAxis(Enum):
        y = "y"
        z = "z"

    @staticmethod
    def get_head_y_up_orient() -> MayaSceneOrient:
        return MayaSceneOrient(MayaSceneOrient.UpAxis.y, MayaSceneOrient.Y_UP_ORIENT_DELTA)

    @staticmethod
    def get_head_z_up_orient() -> MayaSceneOrient:
        return MayaSceneOrient(MayaSceneOrient.UpAxis.z, MayaSceneOrient.Z_UP_ORIENT_DELTA)

    @staticmethod
    def get_body_y_up_orient() -> MayaSceneOrient:
        return MayaSceneOrient(MayaSceneOrient.UpAxis.y, MayaSceneOrient.Y_UP_ORIENT_DELTA)

    @staticmethod
    def get_body_z_up_orient() -> MayaSceneOrient:
        return MayaSceneOrient(MayaSceneOrient.UpAxis.z, MayaSceneOrient.Z_UP_ORIENT_DELTA)

    def __init__(self, up_axis: UpAxis, root_orient_delta: Point3):
        self.up_axis = up_axis
        self.root_orient_delta = root_orient_delta


class MayaConfig(Config):
    """
    Specialization Config class for Autodesk Maya context.
    """

    def __init__(self):
        super().__init__()
        logging.debug("MayaConfig initialized.")

        # scene
        self.scene_orient: MayaSceneOrient = MayaSceneOrient.get_head_y_up_orient()

        # controls
        self.skip_raw_attr = ["qx", "qy", "qz", "qw"]

        # dx11 shaders
        self._lights_scene_relative_path: str = "/maya/lights.ma"
        self._shader_scene_relative_path: str = "/maya/shader.ma"
        self._shader_code_relative_path: str = "/maya/shaders"
        self.map_data_ext: str = "dds"

        self.map_names: list[str] = [
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
            "dx11_diffuseIrradiance",
            "dx11_specularIrradiance",
            "dx11_jitter",
            "dx11_skinLUT",
        ]
        self.shader_attr_mapping: dict[str, str] = {
            "head_cm2_color_head_wm2_browsDown_L": "maskWeight_00",
            "head_wm2_normal_head_wm2_browsDown_L": "maskWeight_01",
            "head_cm2_color_head_wm2_browsDown_R": "maskWeight_02",
            "head_wm2_normal_head_wm2_browsDown_R": "maskWeight_03",
            "head_cm2_color_head_wm2_browsLateral_L": "maskWeight_04",
            "head_wm2_normal_head_wm2_browsLateral_L": "maskWeight_05",
            "head_cm2_color_head_wm2_browsLateral_R": "maskWeight_06",
            "head_wm2_normal_head_wm2_browsLateral_R": "maskWeight_07",
            "head_cm1_color_head_wm1_browsRaiseInner_L": "maskWeight_08",
            "head_wm1_normal_head_wm1_browsRaiseInner_L": "maskWeight_09",
            "head_cm1_color_head_wm1_browsRaiseInner_R": "maskWeight_10",
            "head_wm1_normal_head_wm1_browsRaiseInner_R": "maskWeight_11",
            "head_cm1_color_head_wm1_browsRaiseOuter_L": "maskWeight_12",
            "head_wm1_normal_head_wm1_browsRaiseOuter_L": "maskWeight_13",
            "head_cm1_color_head_wm1_browsRaiseOuter_R": "maskWeight_14",
            "head_wm1_normal_head_wm1_browsRaiseOuter_R": "maskWeight_15",
            "head_cm1_color_head_wm1_blink_L": "maskWeight_16",
            "head_cm1_color_head_wm1_squintInner_L": "maskWeight_17",
            "head_wm1_normal_head_wm1_blink_L": "maskWeight_18",
            "head_wm1_normal_head_wm1_squintInner_L": "maskWeight_19",
            "head_cm1_color_head_wm1_blink_R": "maskWeight_20",
            "head_cm1_color_head_wm1_squintInner_R": "maskWeight_21",
            "head_wm1_normal_head_wm1_blink_R": "maskWeight_22",
            "head_wm1_normal_head_wm1_squintInner_R": "maskWeight_23",
            "head_cm3_color_head_wm3_cheekRaiseInner_L": "maskWeight_24",
            "head_cm3_color_head_wm3_cheekRaiseOuter_L": "maskWeight_25",
            "head_cm3_color_head_wm3_cheekRaiseUpper_L": "maskWeight_26",
            "head_wm3_normal_head_wm3_cheekRaiseInner_L": "maskWeight_27",
            "head_wm3_normal_head_wm3_cheekRaiseOuter_L": "maskWeight_28",
            "head_wm3_normal_head_wm3_cheekRaiseUpper_L": "maskWeight_29",
            "head_cm3_color_head_wm3_cheekRaiseInner_R": "maskWeight_30",
            "head_cm3_color_head_wm3_cheekRaiseOuter_R": "maskWeight_31",
            "head_cm3_color_head_wm3_cheekRaiseUpper_R": "maskWeight_32",
            "head_wm3_normal_head_wm3_cheekRaiseInner_R": "maskWeight_33",
            "head_wm3_normal_head_wm3_cheekRaiseOuter_R": "maskWeight_34",
            "head_wm3_normal_head_wm3_cheekRaiseUpper_R": "maskWeight_35",
            "head_cm2_color_head_wm2_noseWrinkler_L": "maskWeight_36",
            "head_wm2_normal_head_wm2_noseWrinkler_L": "maskWeight_37",
            "head_cm2_color_head_wm2_noseWrinkler_R": "maskWeight_38",
            "head_wm2_normal_head_wm2_noseWrinkler_R": "maskWeight_39",
            "head_cm3_color_head_wm3_smile_L": "maskWeight_40",
            "head_wm3_normal_head_wm3_smile_L": "maskWeight_41",
            "head_cm1_color_head_wm13_lips_UL": "maskWeight_42",
            "head_cm1_color_head_wm13_lips_UR": "maskWeight_43",
            "head_cm1_color_head_wm13_lips_DL": "maskWeight_44",
            "head_cm1_color_head_wm13_lips_DR": "maskWeight_45",
            "head_wm1_normal_head_wm13_lips_UL": "maskWeight_46",
            "head_wm1_normal_head_wm13_lips_UR": "maskWeight_47",
            "head_wm1_normal_head_wm13_lips_DL": "maskWeight_48",
            "head_wm1_normal_head_wm13_lips_DR": "maskWeight_49",
            "head_cm3_color_head_wm3_smile_R": "maskWeight_50",
            "head_wm3_normal_head_wm3_smile_R": "maskWeight_51",
            "head_cm3_color_head_wm13_lips_UL": "maskWeight_52",
            "head_cm3_color_head_wm13_lips_DL": "maskWeight_53",
            "head_wm3_normal_head_wm13_lips_UL": "maskWeight_54",
            "head_wm3_normal_head_wm13_lips_DL": "maskWeight_55",
            "head_cm3_color_head_wm13_lips_UR": "maskWeight_56",
            "head_cm3_color_head_wm13_lips_DR": "maskWeight_57",
            "head_wm3_normal_head_wm13_lips_UR": "maskWeight_58",
            "head_wm3_normal_head_wm13_lips_DR": "maskWeight_59",
            "head_cm2_color_head_wm2_mouthStretch_L": "maskWeight_60",
            "head_wm2_normal_head_wm2_mouthStretch_L": "maskWeight_61",
            "head_cm2_color_head_wm2_mouthStretch_R": "maskWeight_62",
            "head_wm2_normal_head_wm2_mouthStretch_R": "maskWeight_63",
            "head_cm1_color_head_wm1_purse_UL": "maskWeight_64",
            "head_wm1_normal_head_wm1_purse_UL": "maskWeight_65",
            "head_cm1_color_head_wm1_purse_UR": "maskWeight_66",
            "head_wm1_normal_head_wm1_purse_UR": "maskWeight_67",
            "head_cm1_color_head_wm1_purse_DL": "maskWeight_68",
            "head_wm1_normal_head_wm1_purse_DL": "maskWeight_69",
            "head_cm1_color_head_wm1_purse_DR": "maskWeight_70",
            "head_wm1_normal_head_wm1_purse_DR": "maskWeight_71",
            "head_cm1_color_head_wm1_chinRaise_L": "maskWeight_72",
            "head_wm1_normal_head_wm1_chinRaise_L": "maskWeight_73",
            "head_cm1_color_head_wm1_chinRaise_R": "maskWeight_74",
            "head_wm1_normal_head_wm1_chinRaise_R": "maskWeight_75",
            "head_cm1_color_head_wm1_jawOpen": "maskWeight_76",
            "head_wm1_normal_head_wm1_jawOpen": "maskWeight_77",
            "head_cm2_color_head_wm2_neckStretch_L": "maskWeight_78",
            "head_wm2_normal_head_wm2_neckStretch_L": "maskWeight_79",
            "head_cm2_color_head_wm2_neckStretch_R": "maskWeight_80",
            "head_wm2_normal_head_wm2_neckStretch_R": "maskWeight_81",
        }

    def get_lights_scene_path(self, shader_dir: str) -> str:
        return f"{shader_dir}{self._lights_scene_relative_path}"

    def get_shader_scene_path(self, shader_dir: str) -> str:
        return f"{shader_dir}{self._shader_scene_relative_path}"

    def get_shader_code_path(self, shader_dir: str, mesh_name: str) -> str:
        name = mesh_name.split("_")[0]
        return f"{shader_dir}{self._shader_code_relative_path}/dx11_shd_{name}.fx"

    def get_shader_node_name(self, mesh_name: str) -> str:
        name = mesh_name.split("_")[0]
        return f"shader_{name}_shader"

    def get_shading_group_node_name(self, mesh_name: str) -> str:
        name = mesh_name.split("_")[0]
        return f"shader_{name}_shaderSG"

    def get_base_map_file_node_name(self, map_name: str) -> str:
        return f"baseMapFile_{map_name}"

    def get_map_file_node_name(self, map_name: str) -> str:
        return f"mapFile_{map_name}"

    def get_mask_file_node_name(self, mask_name: str) -> str:
        return f"maskFile_{mask_name}"
