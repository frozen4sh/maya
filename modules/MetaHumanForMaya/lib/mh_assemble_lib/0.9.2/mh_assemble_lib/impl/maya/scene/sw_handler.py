# Copyright Epic Games, Inc. All Rights Reserved.
import logging
from typing import List

from maya import cmds

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.model.element import MeshElement, SkinClusterElement
from mh_assemble_lib.impl.maya.properties import MayaConfig


class MayaSkinWeightsHandler:
    """
    Specialized Maya handler for handling skin cluster and skin weights.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config

    def create_skin_weights(self, meshes: List[MeshElement]) -> None:
        """Creates skin cluster and sets skin weights for given mesh on scene."""
        for mesh in meshes:
            logging.info(f"Creating skin weights for mesh: {mesh.name}.")
            sw = self._dna.get_skin_weights(mesh.index)
            self.add_skin_cluster(mesh, sw)
            self.set_skin_weights(mesh, sw)

    def add_skin_cluster(self, mesh: MeshElement, skin_weights: SkinClusterElement) -> None:
        sc_name = self._config.get_skin_cluster_name(mesh.name)
        sw_jnt_names = skin_weights.get_sw_joint_names()
        cmds.select(sw_jnt_names[0], replace=True)
        cmds.select(mesh.name, add=True)
        skin = cmds.skinCluster(
            toSelectedBones=True,
            name=sc_name,
            maximumInfluences=skin_weights.ipv,
            skinMethod=0,
            obeyMaxInfluences=True,
        )
        cmds.skinCluster(skin, edit=True, addInfluence=sw_jnt_names[1:], weight=0)

    def set_skin_weights(self, mesh: MeshElement, skin_weights: SkinClusterElement) -> None:
        logging.debug("Setting skin weights.")
        sw_jnt_indices = skin_weights.get_sw_joint_indices()
        for vtx in range(skin_weights.get_vertex_count()):
            indices = skin_weights.vtx_joint_indices[vtx]
            values = skin_weights.vtx_weight_values[vtx]

            # set all weights to zero
            attr_name = self._config.get_sw_attr_name(mesh.name, vtx, 0)
            cmds.setAttr(attr_name, 0.0)

            # set waights from dna
            for i, jnt_index in enumerate(indices):
                jnt = sw_jnt_indices.index(jnt_index)
                attr_name = self._config.get_sw_attr_name(mesh.name, vtx, jnt)
                attr_val = values[i]
                cmds.setAttr(attr_name, attr_val)
