# Copyright Epic Games, Inc. All Rights Reserved.

import logging
from typing import List

from maya import cmds

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.model.element import MeshElement
from mh_assemble_lib.impl.maya.properties import MayaConfig


class MayaSceneHandler:
    """
    Specialized Maya handler for handling Maya scene parameters.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config

    def open_new_scene(self) -> None:
        """Open new Maya scene."""
        if self._config.open_new_scene:
            logging.debug("Open new scene.")
            cmds.file(new=True, force=True)
            self._set_up_axis()

    def set_units(self) -> None:
        """Set scene units."""
        logging.debug("Set units.")
        linear_unit = self._dna.get_translation_unit()
        angle_unit = self._dna.get_rotation_unit()
        cmds.currentUnit(linear=linear_unit.name, angle=angle_unit.name)

    def create_groups(self, meshes: List[MeshElement]) -> None:
        """Create scene organization, groups, layers, etc."""
        logging.debug("Create groups and layers.")
        conf = self._config
        if conf.group_by_lod:
            cmds.group(world=True, empty=True, name=conf.top_level_group)
            cmds.group(parent=conf.top_level_group, empty=True, name=conf.geometry_group)
            cmds.group(parent=conf.top_level_group, empty=True, name=conf.rig_group)
        sel_mesh_ids = [m.index for m in meshes]
        for lod in range(self._dna.get_lod_count()):
            lod_mesh_ids = self._dna.get_mesh_indices_for_lod(lod)
            if set(sel_mesh_ids) & set(lod_mesh_ids):
                grp_name = conf.get_lod_group_name(lod)
                ly_name = conf.get_lod_layer_name(lod)
                if conf.group_by_lod:
                    cmds.group(parent=conf.geometry_group, empty=True, name=grp_name)
                    cmds.select(grp_name, replace=True)
                if conf.create_display_layers:
                    cmds.createDisplayLayer(name=ly_name, noRecurse=True)

    def _set_up_axis(self) -> None:
        """Set scene up axis, Y or Z."""
        logging.debug("Set up axis.")
        cmds.upAxis(axis=self._config.scene_orient.up_axis.value)
