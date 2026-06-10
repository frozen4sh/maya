# Copyright Epic Games, Inc. All Rights Reserved.
import os
from dataclasses import dataclass

import dna
from mh_assemble_lib.model.dnalib import DNAReader, Layer

import mh_character_assembler.core.consts as consts


@dataclass
class Options:
    import_head: bool = True
    import_body: bool = True
    import_textures: bool = False
    combine_skeletons: bool = False


class Config:
    def __init__(self, config):
        self.current = os.path.dirname(os.path.abspath(__file__))
        self.options = Options()
        self.version = dna.VersionInfo.getVersionString()
        self.head_dna_path = self.prepare_path(config["headDnaPath"])
        self.dna_path_dir = self.resolve_dna_path_dir(self.head_dna_path)
        self.character_name = self.resolve_character_name(self.head_dna_path)
        self.workspace_dir = self.resolve_workspace_path(self.head_dna_path)
        self.body_dna_path = self.prepare_path(config["bodyDnaPath"])
        self.dna_version = self.resolve_dna_version(self.head_dna_path)
        self.platform = self.resolve_platform()
        """
        Each body has its own body mesh name. This information is needed in later steps of character assembly when
        we are grouping body meshes into their corresponding LOD groups
        """
        self.body_mesh_name = "body"
        self.shaders_dir_path = f"{self.current}\\assets\\shared\\shaders"
        self.masks_dir_path = f"{self.current}\\assets\\shared\\masks"
        self.eyes_dir_path = f"{self.current}\\assets\\shared\\eyes"
        self.head_maps_path = f"{self.current}\\assets\\shared\\maps"

        self.scene_orientation_string_value = "z"
        self.scene_orientation = self.resolve_scene_orientation()

        """
        Path to head common maps (specular, diffuse, jitter,...). Assets found here are common for all characters and
        are part of plugin
        """
        self.maps_dir_path = config["mapsDirPath"]
        self.db_version_path = os.path.join("assets", self.dna_version)

        """
        Head GUI controls
        """
        self.gui_path = os.path.join(self.current, self.db_version_path, self.resolve_platform(), "head_gui.ma")

        """
        Eye controls
        """
        self.ac_path = os.path.join(self.current, self.db_version_path, self.resolve_platform(), "head_ac.ma")
        self.shader_scene_path = os.path.join(
            "assets",
            self.current,
            self.db_version_path,
            self.resolve_platform(),
            "head_shader.ma",
        )
        self.body_shader_scene_path = os.path.join(
            "assets",
            self.current,
            self.db_version_path,
            self.resolve_platform(),
            "body_shader.ma",
        )
        self.light_scene_path = os.path.join(
            self.current, self.db_version_path, self.resolve_platform(), "dh_lights.ma"
        )

    def prepare_path(self, val):
        return val.replace("\\", "/")

    def resolve_dna_path_dir(self, dna_file_path):
        resolved_path = os.path.dirname(dna_file_path).replace("\\", "/")
        return resolved_path.replace("\\", "/")

    def resolve_workspace_path(self, dna_file_path):
        return os.path.abspath(self.resolve_dna_path_dir(dna_file_path))

    def resolve_character_name(self, dna_file_path):
        file_name = dna_file_path.split("/")[-1]
        return file_name.replace(".dna", "")

    def resolve_scene_orientation(self):
        # get string value From MH DNAs
        if self.scene_orientation_string_value == "from mh dna":
            head_orient = self.get_orient_from_dna_file(self.head_dna_path) if self.options.import_head else None
            body_orient = self.get_orient_from_dna_file(self.body_dna_path) if self.options.import_body else None

            if self.options.import_head and self.options.import_body:
                if head_orient != body_orient:
                    raise Exception("Head and body orientations do not match!")
                else:
                    self.scene_orientation_string_value = head_orient
            elif self.options.import_head:
                self.scene_orientation_string_value = head_orient
            elif self.options.import_body:
                self.scene_orientation_string_value = body_orient

        orientation = self.scene_orientation_string_value.lower()
        if orientation == "z":
            return consts.ORIENT_Z
        elif orientation == "y":
            return consts.ORIENT_Y
        else:
            return consts.ORIENT_Z

    def get_orient_from_dna_file(self, dna_file_path):
        orientation = "y"
        dna_file = DNAReader.read(dna_file_path, Layer.all)
        dna_file._reader.getCoordinateSystem()
        coordinate_system = dna_file._reader.getCoordinateSystem()

        if dna.Direction_up == coordinate_system.yAxis:
            orientation = "y"
        elif dna.Direction_up == coordinate_system.zAxis:
            orientation = "z"

        return orientation

    def resolve_platform(self):
        import platform

        system = platform.system()

        if system not in ["Windows", "Linux"]:
            system = "Windows"

        return system

    def resolve_dna_version(self, dna_path):
        supported_versions = ["MH.6"]
        input_dna = dna.FileStream(
            str(dna_path),
            dna.FileStream.AccessMode_Read,
            dna.FileStream.OpenMode_Binary,
        )
        input_reader = dna.BinaryStreamReader(input_dna)
        input_reader.read()
        version = input_reader.getDBName()

        if version not in supported_versions:
            raise Exception("Unsupported DNA version")

        return version

    def __str__(self):
        return f"""
            Current: {self.current}
            DNA path: {self.head_dna_path}
            DNA Version: {self.dna_version}
            DNA Version Data Path: {self.db_version_path}
            Workspace path: {self.workspace_dir}
            Body Scene Path: {self.body_dna_path}
            Body Mesh Name: {self.body_mesh_name}
            Head Shaders Dir Path: {self.shaders_dir_path}
            Head Specific Maps Dir Path: {self.maps_dir_path}
            Head Common Maps Dir Path: {self.head_maps_path}
            Masks dir path: {self.masks_dir_path}
            Eye controls: {self.ac_path}
            Scene Orientation: {self.scene_orientation}
            Options: {self.options}
            Version: {self.version}
        """
