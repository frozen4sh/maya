# Copyright Epic Games, Inc. All Rights Reserved.
import logging

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA


class Handler:
    """
    MetaHuman Viever API.

    Base class that handles MetaHuman creation in different contexts.
    This class needs to be sublassed for each context, i.e. environment that is run in.
    Handler has a state, so "set_form()" and "set_dna()" methods need to be called before other methods.
    When sublclassed, all methods starting with "init_" or "handle_" need to be overriden.
    Methods that start with "build_" do not need to be overriden, but they can if needed.
    "build_" methods implement logic when and if "handle_" methods are called.
    """

    def __init__(self):
        self._form: ProcessForm = None
        self._dna: DNA = None

    # PUBLIC API METHODS
    def set_form(self, form: ProcessForm) -> None:
        self._form = form

    def set_dna(self, dna: DNA) -> None:
        self._dna = dna

    def set_state(self, dna: DNA, form: ProcessForm) -> None:
        """
        Initialize API handler state.

        This method should be called before any other API function.
        """
        logging.info("API call: set_state.")
        self.set_dna(dna)
        self.set_form(form)
        self.init_subhandlers()

    def build_mh(self) -> None:
        """Top level API method that builds whole MetaHuman based on input DNA and form."""
        logging.info("API call: build_mh")
        self.handle_start()
        self._build_scene()
        self._build_rig_elements()
        self._build_rig_logic()
        self._build_shaders()
        self._build_optimization()
        self.handle_end()

    def build_scene(self) -> None:
        """Prepare scene for MH build."""
        logging.info("API call: build_scene")
        self._build_scene()

    def build_rig_elements(self) -> None:
        """Build rig elements such as joints, meshes, skin cluster and blend shapes."""
        logging.info("API call: build_rig_elements")
        self._build_rig_elements()

    def build_rig_logic(self) -> None:
        """Import MH interface controls and build RigLogic node."""
        logging.info("API call: build_rig_logic")
        self._build_rig_logic()

    def build_shaders(self) -> None:
        """Build mesh shaders with corresponding textures."""
        logging.info("API call: build_shaders")
        self._build_shaders()

    def build_optimization(self) -> None:
        """Finishing touchecs on scene after MH is built. Call additiona scripts."""
        logging.info("API call: build_optimization")
        self._build_optimization()

    # Private methods
    def _build_scene(self) -> None:
        self._form.set_progress("Preparing scene.", 20)
        self.handle_new_scene()
        self.handle_units()
        self.handle_scene_organization()

    def _build_rig_elements(self) -> None:
        if self._form.add_joints:
            self._form.set_progress("Building joints.", 30)
            self.handle_joints()
        self._form.set_progress("Building meshes.", 40)
        self.handle_meshes()
        if self._form.add_blend_shapes:
            self._form.set_progress("Building blend shapes.", 50)
            self.handle_blend_shapes()
        if self._form.add_skin_cluster:
            self._form.set_progress("Building skin weights.", 70)
            self.handle_skin_weights()

    def _build_rig_logic(self) -> None:
        self._form.set_progress("Building Rig Logic.", 80)
        if self._form.gui_ctrls_path is not None:
            self.handle_gui_controls()
        if self._form.analog_ctrls_path is not None:
            self.handle_analog_controls()
        if self._form.add_rig_logic:
            self.handle_logic_node()

    def _build_shaders(self) -> None:
        self._form.set_progress("Building shaders.", 90)
        if self._form.shader_dir is not None:
            self.handle_lights()
            self.handle_shader()

    def _build_optimization(self) -> None:
        self._form.set_progress("Optimizing scene.", 95)
        if self._form.add_ctrl_attr and self._form.add_joints:
            self.handle_ctrl_attributes()
        if self._form.add_anim_map_attr and self._form.add_joints:
            self.handle_anim_map_attributes()
        if self._form.add_key_frames and self._form.add_joints:
            self.handle_key_frames()
        if self._form.aas_path is not None:
            self.handle_additional_assemble_script()

    # PUBLIC API METHODS designed for overriding in different context
    def init_subhandlers(self) -> None:
        """Initialize specialized helper handlers."""
        pass

    def handle_start(self) -> None:
        """This mehod is called before MH build starts."""
        pass

    def handle_new_scene(self) -> None:
        """Create new scene."""
        pass

    def handle_units(self) -> None:
        """Set approriate scene units."""
        pass

    def handle_scene_organization(self) -> None:
        """Build scene organization, such as groups, layers, etc."""
        pass

    def handle_joints(self) -> None:
        """Add joints to scene."""
        pass

    def handle_meshes(self) -> None:
        """Add meshes to scene."""
        pass

    def handle_blend_shapes(self) -> None:
        """Add blend shapes to scene."""
        pass

    def handle_skin_weights(self) -> None:
        """Add skin weights to scene."""
        pass

    def handle_gui_controls(self) -> None:
        """Import gui controls to scene."""
        pass

    def handle_analog_controls(self) -> None:
        """Import analog controls to scene."""
        pass

    def handle_logic_node(self) -> None:
        """Create and connect RigLogic node."""
        pass

    def handle_lights(self) -> None:
        """Import lights to scene."""
        pass

    def handle_shader(self) -> None:
        """Create mesh shaders with corresponding textures."""
        pass

    def handle_ctrl_attributes(self) -> None:
        """Create control attributes on facial root joint."""
        pass

    def handle_anim_map_attributes(self) -> None:
        """Create animated maps attributes on facial root joint."""
        pass

    def handle_key_frames(self) -> None:
        """Create keyframe on facial root joint."""
        pass

    def handle_additional_assemble_script(self) -> None:
        """Runs additional assemble script after MH build process is finished."""
        pass

    def handle_end(self) -> None:
        """This mehod is called after MH build ends."""
        pass
