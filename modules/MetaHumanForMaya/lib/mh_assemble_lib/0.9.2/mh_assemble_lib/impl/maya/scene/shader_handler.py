# Copyright Epic Games, Inc. All Rights Reserved.
import os
import logging
from typing import List

from maya import mel, cmds

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.model.element import MeshElement
from mh_assemble_lib.impl.maya.properties import MayaConfig


class MayaShaderHandler:
    """
    Specialized Maya handler for handling shaders, textures and lights.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config
        self._shader_names: List[str] = []

    def import_lights(self) -> None:
        """Import lights to scene."""
        lights_path = self._config.get_lights_scene_path(self._form.shader_dir)
        logging.info(f"Importing lights: {lights_path}.")
        self.import_scene(lights_path)

    def create_shaders(self, meshes: List[MeshElement]) -> None:
        """
        Setup map and mask file paths, shader code paths and connects shader animated maps multipliers.

        All nodes are impoted from shader scene.
        """
        # import shader setup scene
        shader_path = self._config.get_shader_scene_path(self._form.shader_dir)
        logging.info(f"Importing shaders: {shader_path}.")
        self.import_scene(shader_path)
        self.setup_maps()
        self.setup_masks()
        self.setup_shaders(meshes)

    def import_scene(self, path: str) -> None:
        if not os.path.exists(path):
            logging.warning(f"Unable to import scene from file: {path}.")
            return
        cmds.file(path, i=True)

    def setup_maps(self) -> None:
        for map_name in self._config.map_names:
            node_name = self._get_map_file_node_name(map_name)
            file_path = self._get_map_file_path(map_name)
            self._set_file_node_path(node_name, file_path)

    def setup_masks(self) -> None:
        for mask_name in self._config.mask_names:
            node_name = self._get_mask_file_node_name(mask_name)
            file_path = self._get_mask_file_path(mask_name)
            self._set_file_node_path(node_name, file_path)

    def setup_shaders(self, meshes: List[MeshElement]) -> None:
        for mesh in meshes:
            self._setup_shader(mesh.name)
            self._apply_shader(mesh.name)

    def _get_map_file_node_name(self, map_name: str) -> str:
        node_name = self._config.get_base_map_file_node_name(map_name)
        if cmds.objExists(node_name):
            return node_name
        node_name = self._config.get_map_file_node_name(map_name)
        if cmds.objExists(node_name):
            return node_name
        logging.warning(f"Unable to find node for map: {map_name}")
        return None

    def _get_map_file_path(self, map_name: str) -> str:
        file_path = self._config.get_map_file_path(self._form.shader_dir, map_name, self._config.map_file_ext)
        if os.path.exists(file_path):
            return file_path
        file_path = self._config.get_map_file_path(self._form.shader_dir, map_name, self._config.map_data_ext)
        if os.path.exists(file_path):
            return file_path
        logging.warning(f"Unable to find file for map: {map_name}")
        return None

    def _get_mask_file_node_name(self, mask_name: str) -> str:
        node_name = self._config.get_mask_file_node_name(mask_name)
        if cmds.objExists(node_name):
            return node_name
        logging.warning(f"Unable to find node for mask: {mask_name}")
        return None

    def _get_mask_file_path(self, mask_name: str) -> str:
        file_path = self._config.get_mask_file_path(self._form.shader_dir, mask_name, self._config.mask_file_ext)
        if os.path.exists(file_path):
            return file_path
        logging.warning(f"Unable to find file for mask: {mask_name}")
        return None

    def _set_file_node_path(self, node_name: str, file_path: str) -> None:
        if node_name and file_path:
            cmds.setAttr(f"{node_name}.fileTextureName", file_path, type="string")

    def _setup_shader(self, mesh_name: str) -> None:
        shd_node_name = self._config.get_shader_node_name(mesh_name)
        shd_code_path = self._config.get_shader_code_path(self._form.shader_dir, mesh_name)
        if cmds.objExists(shd_node_name) and shd_node_name not in self._shader_names:
            if os.path.exists(shd_code_path):
                self._setup_dx11_shader(mesh_name)
            self._shader_names.append(shd_node_name)

    def _setup_dx11_shader(self, mesh_name: str) -> None:
        shd_node_name = self._config.get_shader_node_name(mesh_name)
        logging.info(f"Setting up dx11 shader node: {shd_node_name}.")
        # set shader code
        shd_code_path = self._config.get_shader_code_path(self._form.shader_dir, mesh_name)
        cmds.setAttr(f"{shd_node_name}.shader", shd_code_path, type="string")
        # add channel multipliers
        if cmds.objExists(self._config.animated_map_obj_name):
            mapping = self._config.shader_attr_mapping
            for anim_map in self._dna.get_animated_maps():
                attr_name = mapping.get(anim_map.attr_name, "")
                src_name = f"{self._config.animated_map_obj_name}.{anim_map.attr_name}"
                dest_name = f"{shd_node_name}.{attr_name}"
                if cmds.objExists(src_name) and cmds.objExists(dest_name):
                    cmds.connectAttr(src_name, dest_name)

    def _apply_shader(self, mesh_name: str) -> None:
        shd_node_name = self._config.get_shading_group_node_name(mesh_name)
        if not cmds.objExists(shd_node_name):
            logging.warning(f"Invalid shading group node: {shd_node_name}.")
            return
        cmds.select(mesh_name)
        mel.eval(f"sets -e -forceElement {shd_node_name}")
