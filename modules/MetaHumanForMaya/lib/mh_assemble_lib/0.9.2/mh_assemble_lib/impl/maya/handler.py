# Copyright Epic Games, Inc. All Rights Reserved.

import logging
from typing import List

from mh_assemble_lib.model.element import MeshElement
from mh_assemble_lib.control.handler_api import Handler
from mh_assemble_lib.impl.maya.properties import MayaConfig
from mh_assemble_lib.impl.maya.scene.bs_handler import MayaBlendShapeHandler
from mh_assemble_lib.impl.maya.scene.sw_handler import MayaSkinWeightsHandler
from mh_assemble_lib.impl.maya.scene.rig_handler import MayaRigHandler
from mh_assemble_lib.impl.maya.scene.mesh_handler import MayaMeshHandler
from mh_assemble_lib.impl.maya.scene.joint_handler import MayaJointHandler
from mh_assemble_lib.impl.maya.scene.scene_handler import MayaSceneHandler
from mh_assemble_lib.impl.maya.scene.shader_handler import MayaShaderHandler


class MayaHandler(Handler):
    """
    Specialization Handler class for Autodesk Maya context.

    This object instance is created by MayaFactory class.
    Override "init_" and "handle_" methods from parent class.
    """

    def __init__(self):
        super().__init__()
        self.config: MayaConfig = MayaConfig()
        self._meshes: List[MeshElement] = None
        self._scene_handler: MayaSceneHandler = None
        self._joint_handler: MayaJointHandler = None
        self._mesh_handler: MayaMeshHandler = None
        self._bs_handler: MayaBlendShapeHandler = None
        self._sw_handler: MayaSkinWeightsHandler = None
        self._rig_handler: MayaRigHandler = None
        self._shader_handler: MayaShaderHandler = None
        logging.debug("MayaHandler initialized.")

    def init_subhandlers(self) -> None:
        self._scene_handler = MayaSceneHandler(self._dna, self._form, self.config)
        self._joint_handler = MayaJointHandler(self._dna, self._form, self.config)
        self._mesh_handler = MayaMeshHandler(self._dna, self._form, self.config)
        self._bs_handler = MayaBlendShapeHandler(self._dna, self._form, self.config)
        self._sw_handler = MayaSkinWeightsHandler(self._dna, self._form, self.config)
        self._rig_handler = MayaRigHandler(self._dna, self._form, self.config)
        self._shader_handler = MayaShaderHandler(self._dna, self._form, self.config)

    def handle_start(self) -> None:
        char_name = self._dna.get_name()
        logging.debug(f"Maya handle start for character: {char_name}.")
        self._meshes = []
        if self._form.meshes is None:
            self._meshes = self._dna.get_meshes()
        else:
            for mesh_form in self._form.meshes:
                mesh = self._dna.get_mesh(mesh_form.index)
                self._meshes.append(mesh)

    def handle_new_scene(self) -> None:
        self._scene_handler.open_new_scene()

    def handle_units(self) -> None:
        self._scene_handler.set_units()

    def handle_scene_organization(self) -> None:
        self._scene_handler.create_groups(self._meshes)

    def handle_joints(self) -> None:
        self._joint_handler.create_joints()

    def handle_meshes(self) -> None:
        self._mesh_handler.create_meshes(self._meshes)

    def handle_blend_shapes(self) -> None:
        self._bs_handler.create_blend_shapes(self._meshes)

    def handle_skin_weights(self) -> None:
        self._sw_handler.create_skin_weights(self._meshes)

    def handle_gui_controls(self) -> None:
        self._rig_handler.import_gui_controls()

    def handle_analog_controls(self) -> None:
        self._rig_handler.import_analog_controls()

    def handle_logic_node(self) -> None:
        self._rig_handler.create_rig_logic()

    def handle_shader(self) -> None:
        self._shader_handler.create_shaders(self._meshes)

    def handle_lights(self) -> None:
        self._shader_handler.import_lights()

    def handle_ctrl_attributes(self) -> None:
        self._rig_handler.add_ctrl_attributes_on_facial_root()

    def handle_anim_map_attributes(self) -> None:
        self._rig_handler.add_anim_map_attributes_on_facial_root()

    def handle_key_frames(self) -> None:
        self._rig_handler.add_key_frames()

    def handle_additional_assemble_script(self) -> None:
        self._rig_handler.run_additional_assemble_script()

    def handle_end(self) -> None:
        char_name = self._dna.get_name()
        logging.debug(f"Maya handle end for character: {char_name}.")
