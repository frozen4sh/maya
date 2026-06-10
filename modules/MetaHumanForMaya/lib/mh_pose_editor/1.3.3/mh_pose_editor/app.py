# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import sys
import inspect
import contextlib
from typing import List
from pathlib import Path

# External
from maya import cmds
from qtpy import QtCore, QtWidgets
from maya.api import OpenMaya as om
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Internal
from mh_pose_editor import api
from mh_pose_editor.view import main_window
from mh_pose_editor.model import utils, rbf_node, base_extension, legacy_upgrade
from mh_pose_editor.model.exceptions import PoseEditorIOError
from mh_pose_editor.extensions.dna_io.model.validations.riglogic import model_check

module = sys.modules[__name__]
module.window = None  # type: ignore


class MayaPoseEditor(MayaQWidgetDockableMixin, main_window.MHPoseEditor):
    ...


class PoseEditorApp:
    def __init__(self, parent=None):
        self._view = MayaPoseEditor(parent=parent)
        self._api = api.PoseEditor()
        # Connect up all the ui events
        # Solver Events
        self._view.rbf.event_create_solver.connect(self._create_rbf_solver)
        self._view.rbf.event_delete_solver.connect(self._delete_rbf_solver)
        self._view.rbf.event_edit_solver.connect(self._edit_solver)
        self._view.rbf.event_mirror_solver.connect(self._mirror_rbf_solver)
        self._view.rbf.event_refresh_solvers.connect(self.load_view)
        self._view.rbf.event_set_current_solver.connect(self._set_current_solver)
        # Driver Events
        self._view.rbf_settings.event_add_drivers.connect(self._add_drivers)
        self._view.rbf_settings.event_remove_drivers.connect(self._remove_drivers)
        self._view.event_export_drivers.connect(self._export_dna)
        self._view.event_import_drivers.connect(self._import_dna)
        # Driven Events
        self._view.rbf_settings.event_add_driven.connect(self._add_driven_joints)
        self._view.rbf_settings.event_remove_driven.connect(self._remove_driven)
        # Pose Events
        self._view.rbf_settings.event_add_pose.connect(self._create_pose)
        self._view.rbf_settings.event_delete_pose.connect(self._delete_pose)
        self._view.rbf_settings.event_go_to_pose.connect(self._go_to_pose)
        self._view.rbf_settings.event_mirror_pose.connect(self._mirror_pose)
        self._view.rbf_settings.event_rename_pose.connect(self._rename_pose)
        self._view.rbf_settings.event_update_pose.connect(self._update_pose)
        self._view.rbf_settings.event_mute_pose.connect(self._mute_pose)
        # Utility Events
        self._view.rbf.event_select.connect(utils.set_selection)
        self._view.event_convert_scene.connect(self._convert_scene)
        self._view.rbf_settings.event_select.connect(utils.set_selection)
        self._current_editing_solver = None

        self._load_extensions()
        self.load_view()
        self._view.show(dockable=True)

    @property
    def view(self):
        return self._view

    def update_solver_settings(self, solver: rbf_node.RBFNode) -> None:
        kwargs = {
            "solver": solver,
            # We want to store a reference to the MObject in case the name of the  node is changed and the
            # user doesn't refresh the UI
            "drivers": {
                driver: om.MGlobal.getSelectionListByName(driver).getDependNode(0) for driver in solver.drivers()
            },
            "driven": {
                driven: om.MGlobal.getSelectionListByName(driven).getDependNode(0) for driven in solver.driven_joints()
            },
            "poses": solver.poses(),
        }
        self._view.rbf_settings.load_solver_settings(**kwargs)

    def _create_rbf_solver(self, name: str) -> None:
        solver = self._api.create_rbf_solver(name)
        self._view.rbf.add_rbf_solver(solver, select=True)
        self._edit_solver(solver, True)

    def _delete_rbf_solver(self, solver: rbf_node.RBFNode) -> None:
        self._api.delete_rbf_solver(solver)
        self._view.rbf.delete_solver(solver)

    def _edit_solver(self, solver: rbf_node.RBFNode, edit: bool) -> None:
        if edit:
            existing_edits = [
                existing_solver for existing_solver in self._api.rbf_solvers if existing_solver.get_solver_edit_status()
            ]
            if existing_edits:
                for existing_solver in existing_edits:
                    self._api.edit_solver(existing_solver, False)
                    self._view.rbf.edit_solver(existing_solver, False)
                return

        self._api.edit_solver(solver, edit)
        self._view.rbf.edit_solver(solver, edit)

    def _mirror_rbf_solver(
        self,
        solver: rbf_node.RBFNode,
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
        pose_use_regex: bool = False,
    ) -> None:
        self._api.mirror_rbf_solver(
            solver=solver,
            solver_search=solver_search,
            solver_replace=solver_replace,
            joint_name_search=joint_name_search,
            joint_name_replace=joint_name_replace,
            mirror_rotation_axis=mirror_rotation_axis,
            mirror_translation_axis=mirror_translation_axis,
            pose_name_search=pose_name_search,
            pose_name_replace=pose_name_replace,
            solver_use_regex=solver_use_regex,
            joint_use_regex=joint_use_regex,
            pose_use_regex=pose_use_regex,
        )
        self.load_view()

    def _set_current_solver(self, solver: rbf_node.RBFNode) -> None:
        self._api.current_solver = solver
        self.update_solver_settings(solver)

    def _add_drivers(self, solver: rbf_node.RBFNode) -> None:
        self._api.add_drivers(solver, drivers=cmds.ls(selection=True, type="joint"))
        self.update_solver_settings(solver)

    def _remove_drivers(self, solver: rbf_node.RBFNode, drivers: List[str]) -> None:
        self._api.remove_drivers(solver, drivers)
        self.update_solver_settings(solver)

    def _add_driven_joints(self, solver: rbf_node.RBFNode, edit: bool) -> None:
        self._api.add_driven_joints(solver, cmds.ls(selection=True, type="joint"), edit)
        self.update_solver_settings(solver)

    def _remove_driven(self, solver: rbf_node.RBFNode, joint_names: List[str]) -> None:
        self._api.remove_driven(solver, joint_names)
        self.update_solver_settings(solver)

    def _create_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        self._api.create_pose(solver, pose_name)
        self.update_solver_settings(solver)

    def _delete_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        self._api.delete_pose(solver, pose_name)
        self.update_solver_settings(solver)

    def _go_to_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        self._api.go_to_pose(solver, pose_name)

    def _mirror_pose(
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
        pose_use_regex: bool = False,
    ) -> None:
        self._api.mirror_pose(
            solver=solver,
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
            pose_use_regex=pose_use_regex,
        )
        self.load_view()

    def _rename_pose(self, solver: rbf_node.RBFNode, pose_name: str, new_pose_name: str) -> None:
        self._api.rename_pose(solver, pose_name, new_pose_name)
        self.update_solver_settings(solver)

    def _update_pose(self, solver: rbf_node.RBFNode, pose_name: str) -> None:
        self._api.update_pose(solver, pose_name)
        self.update_solver_settings(solver)

    def _mute_pose(self, solver: rbf_node.RBFNode, pose_name: str, mute: bool = True) -> None:
        self._api.mute_pose(solver, pose_name, mute)
        self.update_solver_settings(solver)

    def _export_dna(
        self,
        export_path: str,
        solvers: List[rbf_node.RBFNode],
        export_geometry: bool,
        export_selected_geometry: bool,
        export_rbf: bool,
        export_swing_twist: bool,
    ):
        selection = cmds.ls(selection=True)
        model = self._api.serialize(
            solvers=solvers,
            export_geometry=export_geometry,
            export_selected_geometry=export_selected_geometry,
            export_rbf=export_rbf,
            export_swing_twist=export_swing_twist,
        )
        check = model_check.DNAModelValidator(model)
        errors, warnings = check.check_model()
        if errors:
            raise PoseEditorIOError("Unable to export DNA model, data is not compatible with RigLogic")

        cmds.select(selection, replace=True)

        self._api.serialize_to_file(
            file_path=Path(export_path),
            solvers=solvers,
            export_geometry=export_geometry,
            export_selected_geometry=export_selected_geometry,
            export_rbf=export_rbf,
            export_swing_twist=export_swing_twist,
        )

    def _import_dna(
        self,
        import_path: str,
        import_skeleton: bool,
        import_geometry: bool,
        unpack_riglogic: bool,
        import_rbf: bool,
        import_swing_twist: bool,
        up_axis: str = "y",
        import_prefix: str = "body",
    ) -> None:
        self._api.deserialize_from_file(
            file_path=Path(import_path),
            import_skeleton=import_skeleton,
            import_geometry=import_geometry,
            unpack_riglogic=unpack_riglogic,
            import_rbf=import_rbf,
            import_swing_twist=import_swing_twist,
            import_prefix=import_prefix,
            up_axis=up_axis,
        )

        self.load_view()

    def _convert_scene(self, dna_export_path: Path, generate_default_swing_twist_setup: bool):
        legacy_upgrade.upgrade_scene(dna_export_path, generate_default_swing_twist_setup)

    def load_view(self) -> None:
        # If we have a ui, clear it before we load fresh data
        self._view.clear()
        # Bool to keep track if we have a solver that has edits to it
        existing_edit = None
        # Iterate through all the solvers in the scene
        for solver in self._api.rbf_solvers:
            # Get the solvers edit status
            edit = self._api.get_solver_edit_status(solver)
            # If we have an existing edit and this solver has also been edited
            if existing_edit is not None and edit:
                # Finish editing this solver
                self._api.edit_solver(edit=False, solver=solver)
                # Update the edit status accordingly
                edit = False
            # Otherwise if no existing edit and we have an edit
            elif edit:
                # Store the existing edit
                existing_edit = solver
            # Add the solver to the view with its edit status
            self._view.rbf.add_rbf_solver(solver, edit=edit, select=edit)
        self._load_extensions()
        self._view.load_extensions(self._extensions)

    def _load_extensions(self) -> None:
        """
        Loads any core and custom extensions found in the sys.modules
        """
        # Find all the available extensions
        found_extensions = []
        # Iterate through all the modules currently loaded
        for module in list(sys.modules.values()):
            try:
                # Find all the classes in the module that inherit from BaseAction
                found_extensions.extend(
                    [
                        obj
                        for name, obj in inspect.getmembers(module, inspect.isclass)
                        if issubclass(obj, base_extension.PoseEditorExtension)
                        and obj != base_extension.PoseEditorExtension
                        and obj not in found_extensions
                    ]
                )
            except ImportError:
                continue

        # Create the extensions
        self._extensions = [extension(api=self._api, app=self) for extension in found_extensions]


def on_destroyed():
    module.window = None  # type: ignore


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        yield app
    else:
        yield app
    app.exec_()


def show(parent=None):
    with application():
        # create if it doesn't exist
        refresh = True
        if module.window is None:
            module.window = PoseEditorApp(parent=parent)  # type: ignore
            module.window.view.destroyed.connect(on_destroyed)
            refresh = False

        # If the window is minimized, raise it
        if module.window.view.windowState() & QtCore.Qt.WindowMinimized:
            module.window.view.setWindowState(QtCore.Qt.WindowActive)

        # show and make active
        module.window.view.show(dockable=True)
        module.window.view.activateWindow()

        if refresh:
            module.window.load_view()

        return module.window
