# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import List, Type, Optional
from pathlib import Path
from maya import mel

# External
from mh_assemble_lib.control.form import MeshForm, ProcessForm
from mh_assemble_lib.model.dnalib import Layer, DNAReader
from mh_assemble_lib.impl.maya.handler import MayaHandler
from mh_assemble_lib.impl.maya.properties import MayaSceneOrient

# Internal

# Core extensions and actions are imported before the UERBFAPI is defined so that when an instance of the api is created
# the extensions and actions will automatically be loaded. The same must be done for any custom actions/extensions.
from mh_pose_editor import extensions
from mh_pose_editor.extensions.dna_io.model import dna_model, dna_writer, dna_reader, utils as dna_utils
from mh_pose_editor.log import LOG
from mh_pose_editor.model import (
    rbf_node,
    utils,
    context,
    settings,
    exceptions,
    serializers,
    base_extension,
    plugin_manager,
)
from mh_pose_editor.model.rbf_node import RBFNode

plugin_manager.PluginManager.load_plugin()
extensions.load()


class PoseEditor:
    """
    Main entry point for interacting with the UERBFSolverNode and UEPoseBlenderNode

    >>> from mh_pose_editor import api
    >>> rbf_api = api.PoseEditor(view=False)
    >>> rbf_api.create_rbf_solver(solver_name="ExampleSolver", drivers=['leg_l'])
    """

    VERSION = "1.0.0"

    def __init__(self, file_path: Optional[Path] = None) -> None:
        super().__init__()
        # Instantiate a settings manager to restore settings from previous sessions
        self._settings_manager = settings.SettingsManager()

        # Empty var to store the current solver for convenience so that you don't have to pass the solver through
        # every time you call a function
        self._current_solver: Optional[RBFNode] = None
        # Empty list to store any core and custom actions used to extend the functionality of PoseEditor
        self._extensions: List[base_extension.PoseEditorExtension] = []

        # Load the contents of the current scene
        LOG.info("Loading Pose Editor...")
        # If a file path is specified, deserialize and load it
        if file_path:
            self.deserialize_from_file(file_path=file_path)

    @property
    def extensions(self) -> List[base_extension.PoseEditorExtension]:
        """
        :return: list of pose editor extensions currently loaded
        :rtype: list[pose_editor.model.base_extension.PoseEditorExtension]
        """
        return self._extensions

    @property
    def current_solver(self) -> Optional[rbf_node.RBFNode]:
        """
        :return: reference to the current solver
        :rtype: rbf_node.RBFNode or None
        """
        return self._current_solver

    @current_solver.setter
    def current_solver(self, solver: rbf_node.RBFNode) -> None:
        # If the specified solver is not an RBFNode class, raise exception
        if not isinstance(solver, rbf_node.RBFNode):
            raise exceptions.InvalidSolverError(f"Solver is not a valid {rbf_node.RBFNode} node")
        # Set the current solver
        self._current_solver = solver
        solvers = self.rbf_solvers
        for action in self._extensions:
            action.on_context_changed(context.PoseEditorContext(current_solver=solver, solvers=solvers))

    @property
    def rbf_solvers(self) -> List[rbf_node.RBFNode]:
        """
        :return: list of rbf solvers in the scene
        :rtype: list
        """
        return rbf_node.RBFNode.find_all()

    # ================================================ Solvers ======================================================= #

    def create_rbf_solver(self, solver_name: str, drivers: Optional[List[str]] = None) -> rbf_node.RBFNode:
        """
        Create an rbf solver node with the given name and the specified driver transforms

        :param solver_name: name of the solver node
        :type solver_name: str
        :param drivers: list of driver transform node names
        :type drivers: list
        :return: RBFNode ref
        :rtype: rbf_node.RBFNode
        """
        # If no drivers are specified, grab the current selection
        drivers = drivers or utils.get_selection(_type="transform")
        LOG.debug(f"Creating RBF solver '{solver_name}' with drivers: {drivers}")
        # Create the solver
        solver = rbf_node.RBFNode.create(solver_name)
        # If drivers have been specified, add them
        if drivers:
            self.add_drivers(drivers=drivers, solver=solver)
        # Set the current solver
        self.current_solver = solver
        # Return the new solver
        return solver

    def delete_rbf_solver(self, solver: rbf_node.RBFNode) -> None:
        """
        Delete the specified solver

        :param solver:  solver reference
        :type solver: rbf_node.RBFNode
        """
        # Delete the solver
        solver.delete()

        # If the current solver is this solver, set current to None
        if self._current_solver == solver:
            self._current_solver = None

    def edit_solver(self, solver: rbf_node.RBFNode, edit: bool = True) -> Optional[context.EditSolverContextManager]:
        """
        Edit or finish editing the specified solver. Enables pose creation/driven node changes via the ui

        :param edit:  set edit mode on or off
        :type edit: bool
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Edit the solver
        solver.edit_solver(edit=edit)
        LOG.debug(f"Setting edit status: {edit} for solver: {solver}")
        self.current_solver = solver
        # Return a context manager if edit is True so that users have the option to automatically finish editing
        # instead of running edit_solver twice.
        if edit:
            return context.EditSolverContextManager(self, self.current_solver)

        return None

    def mirror_rbf_solver(
            self,
            solver: rbf_node.RBFNode,
            solver_search: str,
            solver_replace: str,
            joint_name_search: str,
            joint_name_replace: str,
            mirror_rotation_axis: str = "x",
            mirror_translation_axis: str = "x",
            pose_name_search: str = "",
            pose_name_replace: str = "",
            solver_use_regex: bool = False,
            joint_use_regex: bool = False,
            pose_use_regex: bool = False
    ) -> rbf_node.RBFNode:
        """
        Mirror the current solver

        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        :param solver_search: solver substring to search for
        :param solver_replace: solver substring to replace with
        :param joint_name_search: joint name substring to search for
        :param joint_name_replace: joint name substring to replace with
        :param mirror_rotation_axis:
        :param mirror_translation_axis:
        :param pose_name_search: Optional pose name substring to search for
        :param pose_name_replace: Optional pose name substring to replace with
        :return: mirrored solver reference
        :rtype: rbf_node.RBFNode
        """

        mirrored_solver = solver.mirror(
            mirror_rotation_axis=mirror_rotation_axis,
            mirror_translation_axis=mirror_translation_axis,
            solver_search=solver_search,
            solver_replace=solver_replace,
            joint_name_search=joint_name_search,
            joint_name_replace=joint_name_replace,
            pose_name_search=pose_name_search,
            pose_name_replace=pose_name_replace,
            solver_use_regex=solver_use_regex,
            joint_use_regex=joint_use_regex,
            pose_use_regex=pose_use_regex
        )

        # Set the current solver to the new solver
        self.current_solver = mirrored_solver
        # Return the new solver
        return mirrored_solver

    def get_rbf_solver_by_name(self, solver_name: str) -> Optional[rbf_node.RBFNode]:
        """
        Searches the scene for an rbf solver with the given name. Case-insensitive

        :param solver_name: Solver node name
        :type solver_name: str
        :return: found node or None
        :rtype: rbf_node.RBFNode or None
        """
        for solver in rbf_node.RBFNode.find_all():
            if str(solver).lower() == solver_name.lower():
                return solver

        return None

    # ================================================ Drivers ======================================================= #

    def add_drivers(self, solver: rbf_node.RBFNode, drivers: List[str]) -> None:
        """
        Add the specified drivers to the specified solver

        :param drivers: list of transform nodes
        :type drivers: list
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # If we already have more than one pose, we can't add a new driver (would require manually updating every pose)
        if solver.num_poses() > 1:
            raise exceptions.InvalidPoseIndex("Too many poses have been created, unable to add a new driver.")
        # Check if we have a default pose
        if solver.has_pose(pose_name="default"):
            # Delete the current rest pose if found
            solver.delete_pose(pose_name="default")
        # Add new drivers
        solver.add_driver(joint_names=drivers)
        # Create the new rest pose with all the drivers
        solver.add_pose_from_current(pose_name="default")
        # Set the current solver
        self.current_solver = solver

    def remove_drivers(self, solver: rbf_node.RBFNode, drivers: List[str]) -> None:
        """
        Remove the specified drivers from the specified solver

        :param drivers: list of driver transform nodes
        :type drivers: list
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Remove the drivers from the solver
        solver.remove_drivers(drivers)
        # Have to re-wrap solver due to a bug with targets array indexing
        self.current_solver = rbf_node.RBFNode(str(solver))

    # ================================================ Driven ======================================================== #

    def add_driven_joints(self, solver: rbf_node.RBFNode, joint_names: List[str], edit: bool = False) -> None:
        """
        Add driven joints to the specified solver

        :param joint_names: list of transform nodes
        :type joint_names: list
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        :param edit: should this transform not be connected to the pose blender output upon creation
        :type edit: bool
        """
        solver.add_driven_joints(joint_names, edit=edit)
        # Update the current solver
        self.current_solver = solver

    def remove_driven(self, solver: rbf_node.RBFNode, joint_names: List[str]):
        """
        Remove driven transforms from the specified solver

        :param joint_names: list of transform nodes
        :type joint_names: list
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        solver.remove_driven_joints(joint_names)
        # Update the current solver
        self.current_solver = solver

    # ================================================= Poses ======================================================== #

    def create_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        """
        Create a new pose for the specified solver

        :param pose_name: name of the new pose
        :type pose_name: str
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Create a new pose from the current position
        solver.add_pose_from_current(pose_name=pose_name)
        # Set the current solver
        self.current_solver = solver

    def delete_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        """
        Remove a pose from the given solver

        :param pose_name: name of the pose to remove
        :type pose_name: str
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Delete the pose
        solver.delete_pose(pose_name)
        # Set the current solver
        self.current_solver = solver

    def go_to_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        """
        Move the driver/driven transforms to the given pose

        :param pose_name: name of the pose
        :type pose_name: str
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Go to the pose
        if solver.has_pose(pose_name=pose_name):
            solver.go_to_pose(pose_name=pose_name)

    def mirror_pose(
            self,
            solver: rbf_node.RBFNode,
            pose_name: str,
            solver_search: str,
            solver_replace: str,
            joint_name_search: str,
            joint_name_replace: str,
            pose_name_search: str,
            pose_name_replace: str,
            mirror_rotation_axis: str = "x",
            mirror_translation_axis: str = "x",
            solver_use_regex: bool = False,
            joint_use_regex: bool = False,
            pose_use_regex: bool = False
    ) -> None:
        """
        Mirror a pose to the mirror of the current solver.
        :param solver: solver reference
        :param pose_name: name of the pose
        :param mirror_rotation_axis:
        :param mirror_translation_axis:
        :param solver_search: solver substring to search for
        :param solver_replace: solver substring to replace with
        :param joint_name_search: joint name substring to search for
        :param joint_name_replace: joint name substring to replace with
        """

        # Mirror the pose
        solver.mirror_pose(
            pose_name=pose_name,
            mirror_rotation_axis=mirror_rotation_axis,
            mirror_translation_axis=mirror_translation_axis,
            solver_search=solver_search,
            solver_replace=solver_replace,
            joint_name_search=joint_name_search,
            joint_name_replace=joint_name_replace,
            pose_name_search=pose_name_search,
            pose_name_replace=pose_name_replace,
            solver_use_regex=solver_use_regex,
            joint_use_regex=joint_use_regex,
            pose_use_regex=pose_use_regex
        )
        # Set the current solver
        self.current_solver = solver

    def mute_pose(self, solver: rbf_node.RBFNode, pose_name: str, mute: bool = True) -> None:
        """
        Mute or unmute the specified pose, removing all influences of the pose from the solver.
        NOTE: This will affect the solver radius if automatic radius is enabled.

        :param pose_name: name of the pose
        :type pose_name: str
        :param mute: mute or unmute the pose
        :type mute: bool
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Mute or unmute the pose
        solver.mute_pose(pose_name=pose_name, mute=mute)
        # Set the current solver
        self.current_solver = solver

    def rename_pose(self, solver: rbf_node.RBFNode, pose_name: str, new_pose_name: str) -> None:
        """
        Rename a pose on the given solver

        :param pose_name: name of the pose
        :type pose_name: str
        :param new_pose_name: new name of the pose
        :type new_pose_name: str
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Get the current pose index
        pose_index = solver.pose_index(pose_name=pose_name)
        # Rename the pose at the given index
        solver.rename_pose(pose_index=pose_index, pose_name=new_pose_name)
        # Update the current solver
        self.current_solver = solver

    def update_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        """
        Update the pose for the given solver

        :param pose_name: name of the pose to update
        :type pose_name: str
        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        """
        # Update the pose with the current driver/driven positions
        solver.add_pose_from_current(pose_name, update=True)
        LOG.info(f"Updated {pose_name}")

        self.current_solver = solver

    # ================================================== IO ========================================================== #

    def deserialize_from_file(
            self,
            file_path: Path,
            solver_names: Optional[List[str]] = None,
            import_skeleton: bool = True,
            import_geometry: bool = True,
            unpack_riglogic: bool = True,
            import_rbf: bool = True,
            import_swing_twist: bool = True,
            import_prefix: str = "body",
            up_axis: str = "y",
            **kwargs
    ) -> dna_model.MHDNAModel:
        """
        Deserialize solvers from a specific file.

        :param file_path: json file to load
        :param solver_names: optional list of solver names to load
        :param import_geometry: import geometry and skeleton from the DNA file
        :param unpack_riglogic
        :param import_rbf:
        :param import_swing_twist
        :param import_prefix
        """
        # Check the path exists
        if not file_path.exists():
            raise exceptions.PoseEditorIOError(
                f"Unable to deserialize from {file_path.as_posix()}, path does not exist"
            )
        if solver_names is None:
            solver_names = []

        file_path, is_temp_file = dna_utils.orient_dna(Path(file_path), up_axis)

        reader = dna_reader.MHDNAReader(file_path.as_posix())
        model = reader.read()

        dna = DNAReader.read(file_path.as_posix(), Layer.all)

        if import_skeleton or import_geometry:
            handler = MayaHandler()
            handler.config.open_new_scene = False
            handler.config.top_level = import_prefix
            handler.config.top_level_group = f"{import_prefix}_grp"
            handler.config.geometry_group = f"{import_prefix}_geometry_grp"
            handler.config.rig_group = f"{import_prefix}_rig_grp"
            handler.config.rig_logic_suffix = f"{import_prefix}"
            handler.config.scene_orient = MayaSceneOrient.get_body_y_up_orient()
            if model.descriptor.coordinate_system.coor_sys == dna_model.CoorSystem.create_maya_zup_coordinate_system():
                handler.config.scene_orient = MayaSceneOrient.get_body_z_up_orient()

            form = ProcessForm()
            form.add_joints = import_skeleton
            form.add_skin_cluster = import_skeleton and import_geometry
            form.add_blend_shapes = False
            form.add_ctrl_attr = False
            form.add_anim_map_attr = False
            form.add_rig_logic = False

            form.meshes = []
            if import_geometry:
                for mesh_id in range(dna.get_mesh_count()):
                    mesh_name = dna.get_mesh_name(mesh_id)
                    form.meshes.append(MeshForm(mesh_id, mesh_name))

            handler.set_state(dna, form)
            handler.build_mh()

            if import_geometry:
                for mesh in form.meshes:
                    utils.recalculate_vtx_normals(mesh.name)

            # Create RL node in scene
            if not unpack_riglogic:
                mel_command = (
                    f'createEmbeddedNodeRL4 -n "body_rl4Embedded" -dfp "{file_path.as_posix()}" '
                    f'-ijn "<objName>.<attrName>" -jn "<objName>.<attrName>";'
                )
                mel.eval(mel_command)

        self.deserialize(model=model, solver_names=solver_names, unpack_rbf=import_rbf,
                         unpack_swing_twist=import_swing_twist, **kwargs)

        LOG.info(f"Successfully loaded {file_path.as_posix()}")

        if is_temp_file and file_path.exists():
            file_path.unlink()

        return model

    def serialize_to_file(
            self, file_path: Path, solvers: Optional[List[rbf_node.RBFNode]] = None, **kwargs
    ) -> Optional[dna_model.MHDNAModel]:
        """
        Serialize the specified solvers to a file

        :param file_path: json file to serialize
        :type file_path: str
        :param solvers: list of rbf_node.RBFNode to serialize
        :type solvers: list
        """
        # Check that the directory exists before writing to it
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.suffix != ".dna":
            LOG.error("Invalid file type specified, expected .dna")
            return None

        solvers = solvers or self.rbf_solvers
        model = self.serialize(solvers=solvers, **kwargs)
        writer = dna_writer.MHDNAWriter(file_path.as_posix())
        writer.write(model)
        LOG.info(f"Successfully exported {len(solvers)} solver(s) to {file_path.as_posix()}")
        return model

    def deserialize(self, model: dna_model.MHDNAModel, solver_names: Optional[List[str]] = None, **kwargs) -> None:
        """
        Deserialize and load the solvers from the data specified

        :param model: metahuman dna model
        :param solver_names: list of solver names to load from the data
        """
        for serializer in serializers.SERIALIZERS:
            if serializer.can_process(model=model):
                serializer.deserialize(model=model, solver_names=solver_names, **kwargs)
                break

    def serialize(self, solvers: List[rbf_node.RBFNode], **kwargs) -> dna_model.MHDNAModel:
        """
        Serialize the specified solvers

        :param solvers: list of rbf_node.RBFNode to serialize
        :return: serialized solver data
        """
        # Always serialize with the latest solver
        serializer = serializers.SERIALIZERS[-1]
        return serializer.serialize(solvers=solvers, **kwargs)

    # =============================================== Utilities ====================================================== #

    def get_context(self) -> context.PoseEditorContext:
        """
        Get the current solver context

        :return: pose editor context containing the current solver and all rbf solvers
        :rtype: context.PoseEditorContext
        """
        return context.PoseEditorContext(current_solver=self.current_solver, solvers=self.rbf_solvers)

    def get_extension_by_type(
            self, class_ref: Type[base_extension.PoseEditorExtension]
    ) -> Optional[base_extension.PoseEditorExtension]:
        """
        Get a reference to one of the loaded extensions from a class type

        :param class_ref: reference to an extension class
        :type class_ref: base_extension.PoseEditorExtension
        :return: reference to a loaded extension if one is loaded
        :rtype: base_extension.PoseEditorExtension instance or None
        """
        for extension in self._extensions:
            if isinstance(extension, class_ref):
                return extension

        return None

    def get_solver_edit_status(self, solver: rbf_node.RBFNode) -> bool:
        """
        Check if the current solver is in 'Edit' mode

        :param solver: solver reference
        :type solver: rbf_node.RBFNode
        :return: True = in edit mode, False = not in edit mode
        :rtype: bool
        """
        return solver.get_solver_edit_status()
