# Copyright Epic Games, Inc. All Rights Reserved.

import os
import contextlib
from math import ceil, floor
from functools import partial
from collections import Counter

from qtpy import QtWidgets
from frt_api import ProgressEnd, ProgressStart, ProgressUpdate

from . import lib, roles
from .utils import ui, dcc, general
from .resource import Resources
from .widgets.common import NamedSlider
from .widgets.settings import Settings

logger = general.get_logger()


def end_progress_on_error(function):
    def wrapper_with_args(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            ProgressEnd.emit()
            raise e

    return wrapper_with_args


class Controller(metaclass=general.SingletonMeta):
    DNA_CALIB_NODE_NAME = "MetaHumanDNACalib"
    PREVIEW_RIG_LOGIC_NODE_NAME = "PreviewRigLogic"

    def __init__(self):
        self.callbacks = []
        self.ctrls_moved = []
        self.editing_expression = False
        self.window = None
        self.copied_joints = None
        self.main_expression_slider_widgets = []
        self.ml_joints_matching_handler_single_expression = None
        self.ml_joints_matching_handler_all_expressions = None
        self.preview_meshes = {}
        self.phase_elements = []
        self.current_phase = None

    def set_window(self, window):
        self.window = window

    def initialize_ml_joints_matching_handler(self, rig, rotation):
        self.ml_joints_matching_handler_single_expression = lib.initialize_ml_joints_matching_handler(rig, rotation)
        self.ml_joints_matching_handler_all_expressions = lib.initialize_ml_joints_matching_handler(rig, rotation)

    @end_progress_on_error
    def fill_export_combo_box(self, combo_box, export_btn, rig):
        combo_box.clear()
        body_type_metadata = lib.get_body_type_metadata(rig)
        body_type_item_index = None

        for _, _, body_file_names in os.walk(Resources().body_scenes_folder_path):
            item_index = 0
            for body_file_name in sorted(body_file_names):
                if body_file_name.endswith((".ma", ".dna")):
                    body_type = body_file_name.split(".")[0]
                    combo_box.addItem(body_file_name)
                    if body_type == body_type_metadata:
                        body_type_item_index = item_index
                    item_index += 1
            break

        export_btn.setDisabled(False)
        combo_box.addItem("Select body file...")

        if body_type_item_index is not None:
            combo_box.setCurrentIndex(body_type_item_index)
            logger.info(f"Body file selection set to {body_type_metadata}.")
        else:
            if combo_box.count() > 1:
                logger.warning(
                    "Correct body type metadata not present in the MetaHuman DNA file, body type selection will not be updated automatically."
                )

    def clear_copied_joints(self):
        self.copied_joints = None

    @end_progress_on_error
    def from_tree_select_in_scene(self, view):
        dcc.clear_selection()
        if all([item.data(0, roles.ITEM_LOADED) for item in view.selectedItems()]):
            objects = []
            for i in view.selectedItems():
                long_name = i.data(0, roles.ITEM_NAME)
                try:
                    object_uuid = dcc.get_object_uuid(long_name)
                except RuntimeError as e:
                    logger.warning(e)
                    continue
                objects.append(object_uuid)
            dcc.select_object(objects)

    @end_progress_on_error
    def update_views(self, views):
        for view in views:
            root = view.invisibleRootItem()
            for item in iter_items(root):
                text = item.text(0)
                if dcc.check_scene_for_object_by_name(text):
                    item.setDisabled(False)
                    item.setData(0, roles.ITEM_SELECTABLE, True)
                    object_loaded = True
                else:
                    item.setDisabled(True)
                    item.setData(0, roles.ITEM_SELECTABLE, False)
                    object_loaded = False
                item.setData(0, roles.ITEM_LOADED, object_loaded)
                if text.startswith("lod"):
                    item.setDisabled(False)
                    item.setData(0, roles.ITEM_SELECTABLE, True)

    @end_progress_on_error
    def update_rig_views(self, views):
        for view in views:
            root = view.invisibleRootItem()
            for item in iter_items(root):
                item.setData(0, roles.ITEM_LOADED, True)

    @end_progress_on_error
    def get_info_from_plug(self, plug):
        attribute_name = plug.name().split(".")[-1]
        object_name = plug.name().split(".")[0]
        return object_name, attribute_name

    @end_progress_on_error
    def get_view_from_object_name(self, object_name):
        if self.window.ui["stack"]["body"].currentIndex() == 1:
            geo_view = self.window.ui["widget"]["neutral_geo_view"]
            jnt_view = self.window.ui["widget"]["neutral_jnt_view"]
        else:
            geo_view = self.window.ui["widget"]["skin_geo_view"]
            jnt_view = self.window.ui["widget"]["skin_jnt_view"]

        if "lod" in object_name:
            return geo_view
        else:
            return jnt_view

    @end_progress_on_error
    def visibility_callback(self, msg, plug, *args, **kwargs):
        object_name, attribute_name = self.get_info_from_plug(plug)
        if attribute_name == "visibility":
            view = self.get_view_from_object_name(object_name)

            root = view.invisibleRootItem()
            for item in iter_items(root):
                if item.text(0) == object_name:
                    item.setData(0, roles.ITEM_VISIBLE, plug.asBool())

    @end_progress_on_error
    def transfer_vtx(self, geo_view):
        scene_selected = dcc.get_selected_from_scene()
        view_selected = geo_view.selectedIndexes()
        if len(view_selected) != 1 or len(scene_selected) != 2:
            logger.warning("Please select one mesh in geometry view and one from scene")
            return
        # view_selected_mesh
        vsm = view_selected[0]
        main_mesh = f"{'|'+vsm.parent().data() if vsm.parent().data() is not None else ''}|{vsm.data()}"
        new_mesh = [i for i in scene_selected if i != main_mesh][0]
        try:
            dcc.transfer_vertex_positions(main_mesh, new_mesh)
            logger.info("Vertex position transferred")
        except RuntimeError as ex:
            dcc.clear_selection()
            logger.warning(ex)

    @end_progress_on_error
    def mirror_skin(self, rig, rig_mesh_name):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        is_mesh, mesh_node, vtx_ids = validation_result
        dcc.mirror_skin(
            rig,
            rig_mesh_name,
            mesh_node,
            vtx_ids,
            self.window.ui["button"]["choose_direction_skin"].property("direction"),
        )

    def analyze_skin_mirroring(self, rig, rig_mesh_name):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        _, mesh_node, _ = validation_result
        dcc.analyze_skin_mirroring(rig, rig_mesh_name, mesh_node)

    def toggle_vertex_shading(self):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        is_mesh, mesh_node, vtx_ids = validation_result
        dcc.toggle_vertex_shading(mesh_node)

    @end_progress_on_error
    def mirror_mesh(self, rig, rig_mesh_name):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        is_mesh, mesh_node, vtx_ids = validation_result
        dcc.mirror_mesh(
            rig, rig_mesh_name, mesh_node, vtx_ids, self.window.ui["button"]["choose_direction"].property("direction")
        )

    @end_progress_on_error
    def flip_mesh(self, rig, rig_mesh_name):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        is_mesh, mesh_node, vtx_ids = validation_result
        dcc.flip_mesh(
            rig, rig_mesh_name, mesh_node, vtx_ids, self.window.ui["button"]["choose_direction"].property("direction")
        )

    @end_progress_on_error
    def neutralize_mesh(self, rig, rig_mesh_name):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        is_mesh, mesh_node, vtx_ids = validation_result
        dcc.neutralize_mesh(rig, rig_mesh_name, is_mesh, mesh_node, vtx_ids)

    @end_progress_on_error
    def reset_mesh_to_dna(self, rig, rig_mesh_name):
        validation_result = dcc.validate_mesh_vertex_selection()
        if not validation_result:
            return
        is_mesh, mesh_node, vtx_ids = validation_result
        dcc.reset_mesh_to_dna(
            rig,
            rig_mesh_name,
            is_mesh,
            mesh_node,
            vtx_ids,
            self.editing_expression,
            self.current_phase,
        )

    @end_progress_on_error
    def mirror_joints(self, rig, direction):
        validation_result = dcc.validate_joint_selection("edit_grp")
        if not validation_result:
            return
        selection_valid, user_selection = validation_result
        if selection_valid:
            dcc.mirror_joints(rig, direction)
            dcc.select_objects_by_name(user_selection)

    @end_progress_on_error
    def flip_joints(self, rig, direction):
        validation_result = dcc.validate_joint_selection("edit_grp")
        if not validation_result:
            return
        selection_valid, user_selection = validation_result
        if selection_valid:
            dcc.flip_joints(rig, direction)
            dcc.select_objects_by_name(user_selection)

    @end_progress_on_error
    def neutralize_joints(self, rig):
        rig_expression = rig.rig_definition.get_expression_by_name(self.editing_expression)
        validation_result = None
        if rig_expression.no_phases() == 1:
            validation_result = dcc.validate_joint_selection("edit_grp")
        elif self.current_phase is not None:
            validation_result = dcc.validate_joint_selection("phase_grp")
        if not validation_result:
            return
        selection_valid, user_selection = validation_result
        if selection_valid:
            dcc.neutralize_joints(rig)
            dcc.select_objects_by_name(user_selection)

    @end_progress_on_error
    def reset_joints_to_dna_expression(self, rig, expression_name):
        rig_expression = rig.rig_definition.get_expression_by_name(self.editing_expression)
        validation_result = None
        if rig_expression.no_phases() == 1:
            validation_result = dcc.validate_joint_selection("edit_grp")
        elif self.current_phase is not None:
            validation_result = dcc.validate_joint_selection("phase_grp")
        if not validation_result:
            return
        selection_valid, user_selection = validation_result
        if selection_valid:
            dcc.reset_joints_to_dna_expression(rig, expression_name, self.current_phase)
            dcc.select_objects_by_name(user_selection)

    @end_progress_on_error
    def copy_joints(self, rig):
        rig_expression = rig.rig_definition.get_expression_by_name(self.editing_expression)
        if rig_expression.no_phases() == 1:
            self.copied_joints = dcc.get_joints_from_scene(rig, "edit_grp")
        else:
            self.copied_joints = dcc.get_joints_from_scene(rig, "phase_grp")

    @end_progress_on_error
    def copy_joints_from_graph(self, rig, expression_name):
        rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
        if rig_expression.no_phases() == 1:
            self.copied_joints = dcc.get_expression_joints_from_node(rig, self.DNA_CALIB_NODE_NAME, expression_name)
        else:
            raise RuntimeWarning(
                "Selected expression has multiple phases, joints can only be while editing the expression."
            )

    @end_progress_on_error
    def paste_joints(self, rig):
        if not self.copied_joints:
            logger.warning("No copied joints.")
            return
        rig_expression = rig.rig_definition.get_expression_by_name(self.editing_expression)
        validation_result = None
        if rig_expression.no_phases() == 1:
            validation_result = dcc.validate_joint_selection("edit_grp")
        elif self.current_phase is not None:
            validation_result = dcc.validate_joint_selection("phase_grp")
        if not validation_result:
            return
        selection_valid, user_selection = validation_result
        if selection_valid:
            if rig_expression.no_phases() == 1:
                dcc.set_joints_to_scene(self.copied_joints, user_selection, target_group_name="edit_grp")
            else:
                dcc.set_joints_to_scene(self.copied_joints, user_selection, target_group_name="phase_grp")

    @end_progress_on_error
    def match_joints_in_scene(
        self, rig, expression_name, mutable_joints, expression_joints, target_shapes, phase_number=1
    ):
        if not self.ml_joints_matching_handler_single_expression.model_loaded:
            ProgressStart.emit(max_value=1)
            ProgressUpdate.emit(status="Loading model.")
            self.ml_joints_matching_handler_single_expression.load_model(
                Resources().ml_joints_matching_model_description_path,
                1,
            )
            ProgressEnd.emit()

        ProgressStart.emit(max_value=2)

        ProgressUpdate.emit(status=f"Matching joints for {self.editing_expression}.")
        result = self.ml_joints_matching_handler_single_expression.match_joints(
            [expression_name],
            [phase_number],
            {(expression_name, phase_number): expression_joints},
            {(expression_name, phase_number): target_shapes},
            update_rig=False,
            joint_locking={expression_name: set(mutable_joints)},
        )

        skinning_joints = set()
        for i in rig.dna_reader.getMeshIndicesForLOD(0):
            skinning_joints.update(rig.get_maya_skin_weights(rig.dna_reader.getMeshName(i)).joints)
        for mesh in rig.rig_definition.meshes:
            if mesh.name not in rig.rig_definition.get_dna_mesh_names():
                skinning_joints.update(rig.get_maya_skin_weights(mesh.name).joints)

        return result, skinning_joints

    @end_progress_on_error
    def run_ml_joints_matching_in_scene_for_head_turns(self, rig, mutable_joints, phase_number=1):
        if not self.ml_joints_matching_handler_single_expression.model_loaded:
            ProgressStart.emit(max_value=1)
            ProgressUpdate.emit(status="Loading model.")
            self.ml_joints_matching_handler_single_expression.load_model(
                Resources().ml_joints_matching_model_description_path,
                1,
            )
            ProgressEnd.emit()
        ProgressStart.emit(max_value=2)

        current_global_slider_value = self.window.ui["widget"]["global_slider"].value()
        current_main_expression_slider_values = [slider.value() for slider in self.main_expression_slider_widgets]
        self.window.ui["widget"]["global_slider"].setValue(self.window.ui["widget"]["global_slider"].maximum())

        target_shapes, expression_joints = lib.get_head_turn_matching_data(
            rig, self.editing_expression, self.window.config["neck_joints"], "preview_grp"
        )

        self.window.ui["widget"]["global_slider"].setValue(current_global_slider_value)
        for value, slider in zip(current_main_expression_slider_values, self.main_expression_slider_widgets):
            slider.setValue(value)

        ProgressUpdate.emit(status=f"Matching joints for {self.editing_expression}.")
        result, skinning_joints = self.match_joints_in_scene(
            rig,
            self.editing_expression,
            mutable_joints,
            expression_joints,
            target_shapes,
        )

        ProgressUpdate.emit(status="Updating edit joints in the scene.")
        dcc.apply_ml_joints_matching_to_scene_for_head_turns(
            rig, result[(self.editing_expression, phase_number)], skinning_joints
        )
        ProgressEnd.emit()

    @end_progress_on_error
    def _run_ml_joints_matching_in_scene(self, rig, mutable_joints, phase_number=1):
        ProgressStart.emit(max_value=2)
        if self.current_phase:
            group_name = "phase_grp"
            target_shapes = dcc.get_phase_sculpts_mesh_vertex_positions(
                rig, self.editing_expression, self.current_phase
            )
        else:
            group_name = "edit_grp"
            target_shapes = dcc.get_sculpt_mesh_vertex_positions(rig)
        expression_joints = lib.get_expression_joints_from_scene(rig, group_name)

        ProgressUpdate.emit(status=f"Matching joints for {self.editing_expression}.")
        result, skinning_joints = self.match_joints_in_scene(
            rig,
            self.editing_expression,
            mutable_joints,
            expression_joints,
            target_shapes,
        )
        ProgressUpdate.emit(status="Updating edit joints in the scene.")
        dcc.apply_ml_joints_matching_to_scene(
            rig, result[(self.editing_expression, phase_number)], skinning_joints, group_name
        )
        ProgressEnd.emit()

    @end_progress_on_error
    def run_ml_joints_matching_in_scene(
        self, rig, expression_joints_mapping, custom_expressions_mapping, custom_data, user_defined_joints
    ):
        if not os.path.isfile(Resources().ml_joints_matching_model_description_path):
            raise FileNotFoundError("Missing ML joints matching model description file.")

        rig_expression = rig.rig_definition.get_expression_by_name(self.editing_expression)
        if rig_expression.no_phases() > 1 and self.current_phase is None:
            return

        custom_expressions = set([expression for expression in custom_expressions_mapping])
        mutable_joints = set(expression_joints_mapping[self.editing_expression]).difference(user_defined_joints)
        if self.editing_expression in custom_expressions:
            if custom_expressions_mapping[self.editing_expression] == "head_turns":
                self.run_ml_joints_matching_in_scene_for_head_turns(rig, mutable_joints)
            elif custom_expressions_mapping[self.editing_expression] == "stickies":
                self._run_ml_joints_matching_in_scene(rig, custom_data["stickies"])
            else:
                logger.warning(
                    f"Expression {self.editing_expression} is custom and ML joints matching doesn't support it."
                )
        else:
            self._run_ml_joints_matching_in_scene(rig, mutable_joints)

    @end_progress_on_error
    def run_ml_joints_matching_on_rig(
        self,
        rig,
        expression_joints_mapping,
        user_defined_joints,
        head_turns_data,
        custom_expressions_mapping,
        custom_data,
        batch_size=100,
    ):
        if not os.path.isfile(Resources().ml_joints_matching_model_description_path):
            raise FileNotFoundError("Missing ML joints matching model description file.")

        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status="Removing neck rotations.")
        zero_neck_joints_animations = {}
        for expression_name, neck_joints_animation in head_turns_data["neck_joints_animation"].items():
            zero_neck_joints_animations[expression_name] = {
                joint_name: [0.0, 0.0, 0.0] for joint_name in neck_joints_animation
            }
        lib.add_neck_rotations(rig, head_turns_data["main_expressions"], zero_neck_joints_animations)
        ProgressEnd.emit()

        psd_defs_requiring_fix, single_expressions_to_match = lib.get_expressions_to_fix_data(rig)
        fixed_expressions = set()
        for psd_defs in psd_defs_requiring_fix.values():
            for psd_def_name in psd_defs:
                psd_def = rig.rig_definition.get_psd_def_by_name(psd_def_name)
                fixed_expressions.add(psd_def.target_pose.name)

        ProgressStart.emit(
            max_value=len(single_expressions_to_match)
            + len(fixed_expressions)
            + 1
            + (not self.ml_joints_matching_handler_all_expressions.model_loaded)
        )

        if not self.ml_joints_matching_handler_single_expression.model_loaded:
            ProgressUpdate.emit(status="Loading the single expression model.")
            self.ml_joints_matching_handler_single_expression.load_model(
                Resources().ml_joints_matching_model_description_path,
                1,
            )

        for i, expression_name in enumerate(single_expressions_to_match):
            ProgressUpdate.emit(status=f"Matching single expression {i + 1} of {len(single_expressions_to_match)}.")
            rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
            for phase_number in rig.rig_definition.get_expression_by_name(expression_name).get_phase_numbers():
                single_expression_shapes = {(expression_name, phase_number): {}}
                for mie in rig_expression.meshes_in_expression:
                    if mie.is_blends():
                        sculpt = rig.get_sculpt_mesh_vertex_positions(mie.mesh.name, rig_expression.name, phase_number)
                        single_expression_shapes[(rig_expression.name, phase_number)][mie.mesh.name] = sculpt
                self.ml_joints_matching_handler_single_expression.match_joints(
                    [expression_name],
                    [phase_number],
                    {(expression_name, phase_number): rig.get_expression_joints(expression_name, phase_number)},
                    single_expression_shapes,
                    update_rig=True,
                    joint_locking={
                        expression_name: set(expression_joints_mapping[expression_name]).difference(user_defined_joints)
                    },
                )

        ProgressUpdate.emit(status="Calculating expressions after first pass matching.")
        lib.calculate_expressions(rig)

        custom_expressions = set([expression for expression in custom_expressions_mapping])
        for i, expression_name in enumerate(fixed_expressions):
            ProgressUpdate.emit(status=f"Matching fixed single expressions {i + 1} of {len(fixed_expressions)}.")
            mutable_joints = {
                expression_name: set(expression_joints_mapping[expression_name]).difference(user_defined_joints)
            }
            if expression_name in custom_expressions:
                if custom_expressions_mapping[expression_name] == "stickies":
                    mutable_joints = {expression_name: custom_data["stickies"]}
            rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
            for phase_number in rig_expression.get_phase_numbers():
                single_expression_shapes = {(expression_name, phase_number): {}}
                for mie in rig_expression.meshes_in_expression:
                    if mie.is_blends():
                        sculpt = rig.get_sculpt_mesh_vertex_positions(mie.mesh.name, rig_expression.name, phase_number)
                        single_expression_shapes[(rig_expression.name, phase_number)][mie.mesh.name] = sculpt
                self.ml_joints_matching_handler_single_expression.match_joints(
                    [expression_name],
                    [phase_number],
                    {(expression_name, phase_number): rig.get_expression_joints(expression_name, phase_number)},
                    single_expression_shapes,
                    update_rig=True,
                    joint_locking=mutable_joints,
                )

        matched_expressions = fixed_expressions.union(set(single_expressions_to_match))

        ProgressEnd.emit()

        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status="Data preparation.")

        target_shapes = {}
        expression_names = []
        expression_phases = []
        for exp in expression_joints_mapping:
            if exp not in matched_expressions:
                rig_expression = rig.rig_definition.get_expression_by_name(exp)
                if rig_expression.type in [1, 4]:
                    for phase_number in rig_expression.get_phase_numbers():
                        name_and_phase_added = False
                        for mie in rig_expression.meshes_in_expression:
                            if mie.is_blends():
                                if not name_and_phase_added:
                                    expression_names.append(rig_expression.name)
                                    expression_phases.append(phase_number)
                                    name_and_phase_added = True
                                sculpt = rig.get_sculpt_mesh_vertex_positions(
                                    mie.mesh.name, rig_expression.name, phase_number
                                )
                                if (rig_expression.name, phase_number) in target_shapes:
                                    target_shapes[(rig_expression.name, phase_number)][mie.mesh.name] = sculpt
                                else:
                                    target_shapes[(rig_expression.name, phase_number)] = {mie.mesh.name: sculpt}

        expression_joints = {
            (expression_name, phase_number): rig.get_expression_joints(expression_name, phase_number)
            for expression_name in expression_names
            if expression_name not in matched_expressions
            for phase_number in rig.rig_definition.get_expression_by_name(expression_name).get_phase_numbers()
        }
        joint_locking = {
            expression_name: set(expression_joints_mapping[expression_name]).difference(user_defined_joints)
            for expression_name in expression_names
        }
        ProgressEnd.emit()

        if len(expression_names) < batch_size:
            batch_size = len(expression_names)

        number_of_steps = round(len(expression_names) / batch_size) + (
            not self.ml_joints_matching_handler_all_expressions.model_loaded
        )
        ProgressStart.emit(max_value=number_of_steps + 1)

        if not self.ml_joints_matching_handler_all_expressions.model_loaded:
            ProgressUpdate.emit(status="Loading all expressions model.")
            self.ml_joints_matching_handler_all_expressions.load_model(
                Resources().ml_joints_matching_model_description_path,
                batch_size,
            )

        for i in range(len(expression_names) // batch_size):
            ProgressUpdate.emit(status=f"Matching batch {i} of {round(len(expression_names) / batch_size)}.")
            batch_expression_names = expression_names[i * batch_size : (i + 1) * batch_size]
            batch_expression_phases = expression_phases[i * batch_size : (i + 1) * batch_size]
            self.ml_joints_matching_handler_all_expressions.match_joints(
                batch_expression_names,
                batch_expression_phases,
                expression_joints,
                target_shapes,
                update_rig=True,
                joint_locking=joint_locking,
            )

        if len(expression_names) % batch_size:
            ProgressUpdate.emit(
                status=f"Matching batch {round(len(expression_names) / batch_size)} of {round(len(expression_names) / batch_size)}."
            )
            self.ml_joints_matching_handler_all_expressions.match_joints(
                expression_names[-batch_size:],
                expression_phases[-batch_size:],
                expression_joints,
                target_shapes,
                update_rig=True,
                joint_locking=joint_locking,
            )
        ProgressEnd.emit()

        lib.ordered_calculation(rig, [rig_exp.name for rig_exp in rig.rig_definition.expressions])

        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status="Resetting neck rotations.")
        lib.add_neck_rotations(rig, head_turns_data["main_expressions"], head_turns_data["neck_joints_animation"])
        ProgressEnd.emit()

    @end_progress_on_error
    def neutral_assemble(self, rig, selected_lods, up_axis="y"):
        self.callbacks = lib.assemble_neutral_editing_scene(
            rig, selected_lods, self.callbacks, self.visibility_callback, up_axis
        )

    @end_progress_on_error
    def rig_assemble(
        self,
        rig,
        dna_file_path,
        cbs_pruning_threshold,
        joint_pruning_threshold,
        head_main_exp,
        neck_joints,
        neck_joints_values,
        up_axis,
        rotation,
        left_arm_joint_name,
        eye_aim_control_name,
        right_eye_control_name,
        gui_object_name,
    ):
        self.callbacks = lib.assemble_rig_editing_scene(
            rig,
            dna_file_path,
            self.callbacks,
            self.ctrl_click_callback,
            Controller.DNA_CALIB_NODE_NAME,
            cbs_pruning_threshold,
            joint_pruning_threshold,
            head_main_exp,
            neck_joints,
            neck_joints_values,
            left_arm_joint_name,
            eye_aim_control_name,
            right_eye_control_name,
            gui_object_name,
            up_axis,
            rotation,
        )

    @end_progress_on_error
    def skin_assemble(
        self,
        rig,
        dna_file_path,
        selected_lods,
        up_axis,
        rotation,
        left_arm_joint_name,
        eye_aim_control_name,
        right_eye_control_name,
        gui_object_name,
    ):
        self.callbacks = lib.assemble_skin_editing_scene(
            rig,
            dna_file_path,
            selected_lods,
            self.callbacks,
            self.visibility_callback,
            left_arm_joint_name,
            eye_aim_control_name,
            right_eye_control_name,
            gui_object_name,
            up_axis,
            rotation,
        )

    @end_progress_on_error
    def node_exists(self):
        return not dcc.check_scene_for_object_by_name(Controller.DNA_CALIB_NODE_NAME)

    @end_progress_on_error
    def move_to_editing(self):
        dcc.move_perspective_camera_to_objects(
            [f"|edit_grp|{dcc.get_root_joint_name(self.window.rig)}"],
            self.window.config["shape_preview_data"]["orientation"],
        )

    @end_progress_on_error
    def move_to_preview(self, expression_name):
        if expression_name not in self.preview_meshes:
            logger.warning("No preview mesh available.")
            return
        dcc.move_perspective_camera_to_objects(
            self.preview_meshes[expression_name],
            self.window.config["shape_preview_data"]["orientation"],
        )

    @end_progress_on_error
    def double_click_editing(self, node):
        if self.node_exists():
            logger.warning("The rig editing scene needs to be assembled before editing can be started.")
            return

        if self.editing_expression:
            self.stop_editing(self.window.rig, self.window.ui["widget"]["graph"].currentWidget())
        else:
            node.activate()
            self.start_editing(
                self.window.rig,
                self.window.ui["widget"]["graph"].currentWidget(),
                self.window.expression_joints_mapping,
                self.window.config["split_expressions"],
            )
        self.editing_gui_update()

    def editing_gui_update(self):
        window_ui = self.window.ui
        start_icon = "edit_expr_start.svg"
        end_icon = "edit_expr_end.svg"

        toolbar = window_ui["widget"]["toolbar"]
        btn = toolbar.get_button("ToggleEditing")
        graph = window_ui["widget"]["graph"]
        if self.editing_expression:
            self.window.rig_editing_active = True
            window_ui["button"]["back"].setEnabled(False)
            window_ui["button"]["bookmark"].setEnabled(False)
            window_ui["button"]["preview"].setVisible(True)
            window_ui["button"]["preview_unlocked"].setVisible(True)
            window_ui["button"]["delete_preview"].setVisible(True)
            window_ui["widget"]["node_filter"].setEnabled(False)
            window_ui["widget"]["expression_controls_section"].setVisible(True)
            window_ui["widget"]["rig_geo_section"].setVisible(True)
            window_ui["widget"]["rig_jnt_section"].setVisible(True)
            window_ui["widget"]["rig_toolbar"].setVisible(True)
            window_ui["widget"]["jm_preset_list"].setEnabled(False)
            window_ui["button"]["run_jm"].setEnabled(False)
            window_ui["button"]["run_ml_jm"].setEnabled(False)
            window_ui["widget"]["bookmark_menu"].setEnabled(False)
            for v in toolbar.buttons.values():
                v.setEnabled(False)
            btn.setProperty("active", True)
            btn.setEnabled(True)
            ui.set_icon(btn, end_icon)
            btn.style().unpolish(btn)
            for i in range(0, graph.count()):
                if i != graph.currentIndex():
                    graph.setTabEnabled(i, False)
            graph.setTabsClosable(False)
            self.window.initialize_views(self.editing_expression)
            window_ui["widget"]["global_slider"].setValue(10000)
            dcc.toggle_face_board(False)
            window_ui["menu"]["file"].setEnabled(False)
        else:
            self.window.rig_editing_active = False
            window_ui["button"]["back"].setEnabled(True)
            window_ui["button"]["bookmark"].setEnabled(True)
            window_ui["button"]["preview"].setVisible(False)
            window_ui["button"]["preview_unlocked"].setVisible(False)
            window_ui["button"]["delete_preview"].setVisible(False)
            window_ui["widget"]["node_filter"].setEnabled(True)
            window_ui["widget"]["expression_controls_section"].setVisible(False)
            window_ui["widget"]["rig_geo_section"].setVisible(False)
            window_ui["widget"]["rig_jnt_section"].setVisible(False)
            window_ui["widget"]["rig_toolbar"].setVisible(False)
            window_ui["widget"]["jm_preset_list"].setEnabled(True)
            window_ui["button"]["run_jm"].setEnabled(window_ui["widget"]["jm_preset_list"].count())
            window_ui["button"]["run_ml_jm"].setEnabled(
                os.path.isfile(Resources().ml_joints_matching_model_description_path)
            )
            window_ui["widget"]["bookmark_menu"].setEnabled(True)
            for v in toolbar.buttons.values():
                v.setEnabled(True)
            btn.setProperty("active", False)
            ui.set_icon(btn, start_icon)
            btn.style().unpolish(btn)
            for i in range(0, graph.count()):
                graph.setTabEnabled(i, True)
            graph.setTabsClosable(True)
            graph.tabBar().setTabButton(0, QtWidgets.QTabBar.RightSide, None)
            dcc.toggle_face_board(True)
            window_ui["menu"]["file"].setEnabled(True)

        graph.currentWidget().update_status_text()

    @end_progress_on_error
    def delete_preview_meshes(self):
        dcc.delete_objects("downstream_grp")
        for preview_meshes in self.preview_meshes.values():
            dcc.delete_objects(preview_meshes)
        self.preview_meshes = {}

    @end_progress_on_error
    def stop_editing(self, rig, node_view):
        if self.editing_expression:
            # reset modeling state and send locked expressions to plugin
            node_view.scene().reset_modeling_state()
            nodes = []
            for node in node_view.scene().get_all_modeling_nodes():
                if not node.is_disabled() and not node.lock_btn.is_locked():
                    nodes.append(node)
            dcc.run_before_propagate_changes(rig)

            rig_expression = rig.rig_definition.get_expression_by_name(self.editing_expression)
            dcc.send_locked_expressions(nodes, Controller.DNA_CALIB_NODE_NAME)
            self.editing_expression = False
            dcc.propagate_changes(rig, Controller.DNA_CALIB_NODE_NAME, self.current_phase)
            # ----
            if rig_expression.no_phases() > 1:
                dcc.cleanup_phase_elements(self.phase_elements)
                self.current_phase = None
            else:
                removed_items = self.window.ui["widget"]["expression_controls_section"].clear_content()
                self.window.ui["widget"]["expression_controls_section"].addWidget(removed_items[0].widget())
                for widget in self.main_expression_slider_widgets:
                    widget.deleteLater()

                self.main_expression_slider_widgets = []
                self.window.ui["widget"]["global_slider"].valueChanged.disconnect(
                    self.all_expression_slider_value_changed
                )
            dcc.refresh()
            dcc.clean_preview_elements(rig, Controller.PREVIEW_RIG_LOGIC_NODE_NAME)
            dcc.clear_selection()

            self.delete_preview_meshes()

    @end_progress_on_error
    def start_editing(self, rig, node_view, expression_joints_mapping, split_expressions):
        if node_view.scene().get_active_node():
            editing_expression = node_view.scene().get_active_node()
            self.editing_expression = editing_expression.name
            # ----
            input_names, expressions, psd_matrix = lib.get_main_expressions(rig, editing_expression.name)
            ProgressStart.emit(max_value=2)
            ProgressUpdate.emit(status="Preparing preview elements.")
            rig_expression = rig.rig_definition.get_expression_by_name(editing_expression.name)
            if rig_expression.no_phases() > 1:
                self.window.ui["widget"]["expression_controls_section"].set_title(
                    f"{editing_expression.name}, {rig_expression.no_phases()} Phases"
                )
                self.window.ui["widget"]["global_slider"].valueChanged.disconnect()
                self.window.ui["widget"]["global_slider"].valueChanged.connect(
                    self.phase_expression_slider_value_changed
                )
                self.window.ui["widget"]["global_slider"].set_slider_label("Phase")
                self.phase_elements = dcc.phase_expression_preview_setup(
                    rig, editing_expression.name, Controller.DNA_CALIB_NODE_NAME
                )
                phase_count = rig_expression.no_phases()
                dcc.set_single_phase_sculpt_visibility(
                    self.editing_expression, lib.get_sculpt_mesh_names(self.window.rig), phase_count, None
                )
                self.window.ui["widget"]["global_slider"].set_phase_buttons_visible(True)
                dcc.start_editing_phase(
                    rig, editing_expression.name, Controller.DNA_CALIB_NODE_NAME, expression_joints_mapping
                )
            else:
                self.window.ui["widget"]["expression_controls_section"].set_title(editing_expression.name)
                self.window.ui["widget"]["global_slider"].valueChanged.disconnect()
                self.window.ui["widget"]["global_slider"].valueChanged.connect(self.window.slider_value_changed)
                self.add_main_expression_sliders(
                    lib.get_main_expression_controls(rig, editing_expression.name, split_expressions), split_expressions
                )
                if self.main_expression_slider_widgets:
                    self.window.ui["widget"]["global_slider"].set_slider_label("Global")
                else:
                    self.window.ui["widget"]["global_slider"].set_slider_label("Influence")
                dcc.start_editing(
                    rig, editing_expression.name, Controller.DNA_CALIB_NODE_NAME, expression_joints_mapping
                )
                # create modeling state and send unlocked expressions to plugin
                node_view.scene().modeling_state()
                nodes = []
                if not Settings().get_setting("advanced_propagation"):
                    nodes = node_view.scene().get_all_modeling_nodes()
                else:
                    for node in node_view.scene().get_all_modeling_nodes():
                        if not node.lock_btn.is_locked() and not node.is_disabled():
                            nodes.append(node)
                dcc.send_unlocked_expressions(nodes, Controller.DNA_CALIB_NODE_NAME)
                if psd_matrix:
                    node_data = lib.get_preview_psd_data(rig, input_names, expressions, psd_matrix, split_expressions)
                    dcc.target_expression_preview_setup(
                        rig,
                        editing_expression.name,
                        expressions,
                        split_expressions,
                        node_data,
                        Controller.DNA_CALIB_NODE_NAME,
                        Controller.PREVIEW_RIG_LOGIC_NODE_NAME,
                    )
                else:
                    dcc.main_expression_preview_setup(
                        rig,
                        Controller.DNA_CALIB_NODE_NAME,
                        Controller.PREVIEW_RIG_LOGIC_NODE_NAME,
                        editing_expression.name,
                    )
            ProgressUpdate.emit(status="Preview setup complete.")
            dcc.clear_selection()

            for slider in self.main_expression_slider_widgets:
                slider.setValue(slider.maximum())

            dcc.run_after_edit_assemble(rig)

            ProgressEnd.emit()

    def main_expression_slider_value_changed(self, slider, main_expression_name, split_expressions, value):
        value = float(value) / 10000
        all_slider_values = [float(slider.value()) / slider.maximum() for slider in self.main_expression_slider_widgets]
        maximum_slider_values = [1.0 for _ in self.main_expression_slider_widgets]
        if main_expression_name in split_expressions:
            for expression in split_expressions[main_expression_name]:
                dcc.update_preview(
                    value,
                    expression_name=expression,
                    maximum_value=slider.maximum() / 10000,
                    all_slider_values=all_slider_values,
                    maximum_slider_values=maximum_slider_values,
                )
        else:
            dcc.update_preview(
                value,
                expression_name=main_expression_name,
                maximum_value=slider.maximum() / 10000,
                all_slider_values=all_slider_values,
                maximum_slider_values=maximum_slider_values,
            )

    def all_expression_slider_value_changed(self, value):
        for slider in self.main_expression_slider_widgets:
            slider.setValue(int(value / self.window.ui["widget"]["global_slider"].maximum() * slider.maximum()))

    def phase_expression_slider_value_changed(self, value):
        if self.current_phase is not None:
            dcc.update_phase_joints(self.window.rig, self.editing_expression, self.current_phase)
            rig_expression = self.window.rig.rig_definition.get_expression_by_name(self.editing_expression)
            phase_count = rig_expression.no_phases()
            dcc.set_single_phase_sculpt_visibility(
                self.editing_expression, lib.get_sculpt_mesh_names(self.window.rig), phase_count, None
            )
        self.current_phase = None
        dcc.cmds_set_attr("phase_sculpt_layer.displayType", 2)
        dcc.cmds_set_attr("phase_joints_layer.displayType", 2)
        dcc.cmds_set_attr("preview_grp.visibility", 1)
        dcc.cmds_set_attr("phase_grp.visibility", 0)
        dcc.cmds_set_attr("phase_ctrl.expression", value / self.window.ui["widget"]["global_slider"].maximum())

    def previous_phase_button_clicked(self):
        if self.current_phase is not None:
            dcc.update_phase_joints(self.window.rig, self.editing_expression, self.current_phase)
        rig_expression = self.window.rig.rig_definition.get_expression_by_name(self.editing_expression)
        phase_count = rig_expression.no_phases()
        current_value = ceil(
            self.window.ui["widget"]["global_slider"].value()
            / (self.window.ui["widget"]["global_slider"].maximum() / phase_count)
        )
        self.current_phase = max(0, current_value - 1)
        new_value = self.window.ui["widget"]["global_slider"].maximum() / phase_count * (current_value - 1)
        self.window.ui["widget"]["global_slider"].controls["slider"].blockSignals(True)
        self.window.ui["widget"]["global_slider"].setValue(new_value)
        dcc.cmds_set_attr(
            "phase_ctrl.expression", max(0.0, new_value / self.window.ui["widget"]["global_slider"].maximum())
        )
        self.window.ui["widget"]["global_slider"].controls["slider"].blockSignals(False)
        if max(0.0, new_value / self.window.ui["widget"]["global_slider"].maximum()):
            dcc.cmds_set_attr("phase_sculpt_layer.displayType", 0)
            dcc.cmds_set_attr("phase_joints_layer.displayType", 0)
            dcc.cmds_set_attr("preview_grp.visibility", 0)
            dcc.cmds_set_attr("phase_grp.visibility", 1)
        else:
            dcc.cmds_set_attr("phase_sculpt_layer.displayType", 2)
            dcc.cmds_set_attr("phase_joints_layer.displayType", 2)
            dcc.cmds_set_attr("preview_grp.visibility", 1)
            dcc.cmds_set_attr("phase_grp.visibility", 0)
        dcc.set_single_phase_sculpt_visibility(
            self.editing_expression, lib.get_sculpt_mesh_names(self.window.rig), phase_count, self.current_phase
        )

    def next_phase_button_clicked(self):
        if self.current_phase is not None:
            dcc.update_phase_joints(self.window.rig, self.editing_expression, self.current_phase)
        rig_expression = self.window.rig.rig_definition.get_expression_by_name(self.editing_expression)
        phase_count = rig_expression.no_phases()
        current_value = floor(
            self.window.ui["widget"]["global_slider"].value()
            / round(self.window.ui["widget"]["global_slider"].maximum() / phase_count)
        )
        self.current_phase = min(phase_count, current_value + 1)
        new_value = self.window.ui["widget"]["global_slider"].maximum() / phase_count * (current_value + 1)
        self.window.ui["widget"]["global_slider"].controls["slider"].blockSignals(True)
        self.window.ui["widget"]["global_slider"].setValue(new_value)
        dcc.cmds_set_attr(
            "phase_ctrl.expression", min(1.0, new_value / self.window.ui["widget"]["global_slider"].maximum())
        )
        self.window.ui["widget"]["global_slider"].controls["slider"].blockSignals(False)
        dcc.cmds_set_attr("phase_sculpt_layer.displayType", 0)
        dcc.cmds_set_attr("phase_joints_layer.displayType", 0)
        dcc.cmds_set_attr("preview_grp.visibility", 0)
        dcc.cmds_set_attr("phase_grp.visibility", 1)
        dcc.set_single_phase_sculpt_visibility(
            self.editing_expression, lib.get_sculpt_mesh_names(self.window.rig), phase_count, self.current_phase
        )

    def add_main_expression_sliders(self, main_expressions, split_expressions):
        for main_expression_name, max_value in main_expressions.items():
            slider = NamedSlider(main_expression_name, max_value=int(10000 * max_value))
            self.window.ui["widget"]["expression_controls_section"].addWidget(slider)

            slider.valueChanged.connect(
                partial(
                    self.main_expression_slider_value_changed,
                    slider,
                    main_expression_name,
                    split_expressions,
                )
            )
            self.main_expression_slider_widgets.append(slider)
        self.window.ui["widget"]["global_slider"].valueChanged.connect(self.all_expression_slider_value_changed)
        self.window.ui["widget"]["global_slider"].set_phase_buttons_visible(False)

    @end_progress_on_error
    def save_dna_from_node(self, dna_file_path=None):
        if not dna_file_path:
            dna_file_path = lib.TEMP_DNA_FILE_PATH
        dcc.save_dna_from_node(Controller.DNA_CALIB_NODE_NAME, dna_file_path)
        return dna_file_path

    @end_progress_on_error
    def send_locked_expression(self, expression_name):
        dcc.lock_expression(Controller.DNA_CALIB_NODE_NAME, expression_name)

    @end_progress_on_error
    def send_unlocked_expression(self, expression_name):
        dcc.unlock_expression(Controller.DNA_CALIB_NODE_NAME, expression_name)

    @end_progress_on_error
    def delete_file(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)

    @end_progress_on_error
    def save_rig_dna(self, rig, rotation_vector, dna_file_path=None):
        dna_file_path = (
            dna_file_path or QtWidgets.QFileDialog.getSaveFileName(self.window, "Save MetaHuman DNA", "", "*.dna")[0]
        )

        ProgressStart.emit(max_value=2)
        ProgressUpdate.emit(status="Saving file...")
        if dna_file_path:
            lib.save_dna(rig, dna_file_path, rotation_vector)

        ProgressUpdate.emit(status="Done")
        ProgressEnd.emit()
        return dna_file_path

    @end_progress_on_error
    def calculate_lower_lods(self, rig, source_lod):
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status="Calculating lower LODs..")
        lib.calculate_lower_lods(rig, source_lod)
        ProgressEnd.emit()

    @end_progress_on_error
    def update_scene_lower_lods(self, rig, meshes_to_update):
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status="Updating lower LODs meshes in scene...")
        dcc.update_scene_lower_lods(rig, meshes_to_update)
        ProgressEnd.emit()

    @end_progress_on_error
    def update_skin(self, rig, view, rotation, dna_file_path=None):
        dna_file_path = (
            dna_file_path or QtWidgets.QFileDialog.getSaveFileName(self.window, "Save MetaHuman DNA", "", "*.dna")[0]
        )

        if dna_file_path:
            ProgressStart.emit(max_value=3)

            ProgressUpdate.emit(status="Processing MetaHuman DNA file")

            meshes = []
            root = view.invisibleRootItem()
            for item in iter_items(root):
                if item.childCount():
                    continue
                if not item.isDisabled():
                    with contextlib.suppress(AttributeError):
                        meshes.append(f"{item.parent().text(0)}|{item.text(0)}")

            if meshes:
                ProgressUpdate.emit(status="Updating skin")
                lib.update_skin(rig, meshes)

                ProgressUpdate.emit(status="Saving MetaHuman DNA")
                lib.save_dna(rig, dna_file_path, rotation)
                ProgressEnd.emit()
                return dna_file_path
            else:
                logger.warning("Scene not assembled, MetaHuman DNA file not saved.")
                ProgressEnd.emit()
        return None

    @end_progress_on_error
    def load_animation(self, path=None, anim_type=None):
        dcc.clear_all_ctrl_anim_curves(anim_type)
        dcc.load_animation(path)

        if anim_type == "gui":
            aas = general.source_module("aas", Resources().aas_file_path)
            aas.connect_expressions()

    @end_progress_on_error
    def preview_expressions(self, rig, expressions_to_preview, preview_head_offset, orientation, anchor_node):
        self.delete_preview_meshes()
        psd_definitions_to_fix, _ = lib.get_expressions_to_fix_data(rig, dirty_expressions=[self.editing_expression])
        expressions_to_fix = []
        for psd_names in psd_definitions_to_fix.values():
            for psd_name in psd_names:
                psd = rig.rig_definition.get_psd_def_by_name(psd_name)
                if psd.target_pose.name in expressions_to_preview:
                    expressions_to_fix.append(psd.target_pose.name)
        skipped_preview_expressions = []
        for expression_name in expressions_to_fix:
            if expression_name in expressions_to_preview:
                expressions_to_preview.remove(expression_name)
                skipped_preview_expressions.append(expression_name)
        self.preview_meshes = dcc.preview_expressions(
            rig,
            expressions_to_preview,
            lib.get_sculpt_mesh_names(rig),
            Controller.DNA_CALIB_NODE_NAME,
            preview_head_offset,
            orientation,
            anchor_node,
            self.window.global_up_axis_rotation,
        )
        for expression_name in skipped_preview_expressions:
            logger.warning(
                f"Expression {expression_name} cannot be previewed. Editing {self.editing_expression} requires a recalculation before previewing"
            )

    @end_progress_on_error
    def preview_downstream_expressions(self, rig, preview_head_offset, orientation, anchor_node):
        expressions_to_preview = []
        for node in self.window.ui["widget"]["graph"].currentWidget().scene().get_all_modeling_nodes():
            if node.isSelected() and not node._active:
                expressions_to_preview.append(node.name)
        if expressions_to_preview:
            self.preview_expressions(rig, expressions_to_preview, preview_head_offset, orientation, anchor_node)

    @end_progress_on_error
    def preview_unlocked_downstream_expressions(self, rig, preview_head_offset, orientation, anchor_node):
        expressions_to_preview = []
        for node in self.window.ui["widget"]["graph"].currentWidget().scene().get_all_modeling_nodes():
            if not node._locked and not node._active:
                expressions_to_preview.append(node.name)
        if expressions_to_preview:
            self.preview_expressions(rig, expressions_to_preview, preview_head_offset, orientation, anchor_node)

    @end_progress_on_error
    def update_preview(self, value):
        skip = self.window.ui["widget"]["expression_controls_section"].widget_count() > 1
        dcc.update_preview(value, skip=skip)

    @end_progress_on_error
    def optimize_rig(self, rig, jm_files):
        lib.optimize_rig(rig, jm_files)

    @end_progress_on_error
    def export(
        self,
        rig,
        body_scene_file_path,
        export_folder_path,
        load_dna_file_path,
        neck_joints,
        general_up_axis,
        general_up_axis_rotation,
        up_axis,
        export_up_axis_rotation,
        up_axis_body_scene_orient,
        material_names,
    ):
        character_name, _ = os.path.splitext(os.path.basename(load_dna_file_path))
        if general_up_axis == up_axis:
            up_axis_dna_rotation = [0.0, 0.0, 0.0]
        else:
            up_axis_dna_rotation = [v1 - v2 for v1, v2 in zip(export_up_axis_rotation, general_up_axis_rotation)]

        lib.export(
            rig,
            body_scene_file_path,
            export_folder_path,
            character_name,
            neck_joints,
            up_axis,
            up_axis_dna_rotation,
            export_up_axis_rotation,
            up_axis_body_scene_orient,
            material_names,
        )

    @end_progress_on_error
    def preview_selection(self, expression, preview):
        gui_visible = dcc.gui_visible()
        if preview:
            rig_expression = self.window.rig.rig_definition.get_expression_by_name(expression.name)
            if len(rig_expression.get_phase_numbers()) != 1:
                logger.warning(
                    f"Expression {expression.name} has multiple phases. It's preview can be viewed from the context menu."
                )
                return
            self.reset_controls()
            for c in self.ctrls_moved:
                dcc.cmds_set_attr(c, 0)

            self.ctrls_moved = []
            head_ctrls = self.window.config["head_turns_data"]["neck_joints_animation"]
            rtg = self.window.raw_to_gui
            ctrls = rtg["expressions_to_raw"].get(expression.name, {})

            for head_turn_expression, value in head_ctrls.items():
                if expression.name == head_turn_expression:
                    for jnt, val in value.items():
                        jnt = dcc.get_joints_from_head_grp(jnt)
                        dcc.cmds_set_attr(f"{jnt}.rx", val[0])
                        dcc.cmds_set_attr(f"{jnt}.ry", val[1])
                        dcc.cmds_set_attr(f"{jnt}.rz", val[2])
                        self.ctrls_moved.extend([f"{jnt}.rx", f"{jnt}.ry", f"{jnt}.rz"])

            for c, multiplier in ctrls.items():
                if gui_visible:
                    try:
                        raw_index = rtg["gtroi"].index(rtg["raw_ctrl_names"].index(c))
                    except ValueError:
                        continue
                    gui_ctrl_name = rtg["gui_ctrl_names"][rtg["gtrii"][raw_index]]
                    gui_ctrl_value = (multiplier - rtg["raw_cut_values"][raw_index]) / rtg["raw_slope_values"][
                        raw_index
                    ]
                    dcc.cmds_set_attr(gui_ctrl_name, gui_ctrl_value)
                    self.ctrls_moved.append(gui_ctrl_name)
                else:
                    dcc.cmds_set_attr(c, multiplier)
                    self.ctrls_moved.append(c)

    @end_progress_on_error
    def reset_controls(self):
        for ctrl in [
            *self.window.raw_to_gui["raw_ctrl_names"],
            *self.window.raw_to_gui["gui_ctrl_names"],
            *self.ctrls_moved,
        ]:
            dcc.cmds_set_attr(ctrl, 0)

    def update_control_preview(self, state):
        for index in range(self.window.ui["widget"]["graph"].count()):
            graph_view = self.window.ui["widget"]["graph"].widget(index)
            graph_view.update_control_preview_state(state)

    def update_expression_preview(self, state):
        for index in range(self.window.ui["widget"]["graph"].count()):
            graph_view = self.window.ui["widget"]["graph"].widget(index)
            graph_view.update_expression_preview_state(state)

    def update_highlight_selected(self, state):
        for index in range(self.window.ui["widget"]["graph"].count()):
            graph_view = self.window.ui["widget"]["graph"].widget(index)
            graph_view.update_highlight_last_selected_state(state)

    @end_progress_on_error
    def ctrl_click_callback(self, *args, **kwargs):
        selected = dcc.check_if_gui_ctrl_is_selected(self.window.raw_to_gui["gui_ctrl_names"])

        preview = self.window.ui["widget"]["graph"].currentWidget().control_preview_action.isChecked()

        if len(selected) == 0 or not preview:
            return

        expressions = []
        raw_ctrls = []
        raw_to_gui = self.window.raw_to_gui
        for ctrl in selected:
            if ctrl in self.window.config["additional_gui_controls"]:
                for additional_ctrl in self.window.config["additional_gui_controls"][ctrl]:
                    if additional_ctrl not in selected:
                        selected.append(additional_ctrl)

        for ctrl in selected:
            gui_index = raw_to_gui["gui_ctrl_names"].index(ctrl)

            # Get the corresponding index for the raw_ctrl_names
            raw_index = [index for (index, item) in enumerate(raw_to_gui["gtrii"]) if item == gui_index]

            # Find the control name using raw_index
            for index in raw_index:
                ctrl_name_index = raw_to_gui["gtroi"][index]
                raw_ctrls.append(raw_to_gui["raw_ctrl_names"][ctrl_name_index])

        for expression, ctrls in raw_to_gui["expressions_to_raw"].items():
            for raw in ctrls:
                if raw in raw_ctrls:
                    expressions.append(expression)

        exp_count = Counter(expressions)
        min_count = min(exp_count.values())
        max_count = max(exp_count.values())
        norm_expressions = {}
        if max_count == min_count:
            default_normalized_value = 1.0  # You can change this to 1.0 or any other value you prefer.
            for name in exp_count:
                norm_expressions[name] = default_normalized_value
        else:
            for name, count in exp_count.items():
                normalized_count = 0.1 + 0.5 * (count - min_count) / (max_count - min_count)
                norm_expressions[name] = normalized_count ** (1 / max_count)

        exp_keys = list(norm_expressions.keys())
        graph = self.window.ui["widget"]["graph"].currentWidget()
        for node in graph.scene().nodes:
            if node.name in exp_keys:
                node.set_analyzed(general.linear_interpolate_color(norm_expressions[node.name]))
            else:
                node.set_analyzed((0, 0, 0, 0))

    def update_phase_controls(self, expression_name, phase):
        controls = lib.get_phase_expression_control_activation(self.window.rig, expression_name, phase)
        gui_visible = dcc.gui_visible()
        rtg = self.window.raw_to_gui
        self.reset_controls()
        for control, multiplier in controls:
            if gui_visible:
                try:
                    raw_index = rtg["gtroi"].index(rtg["raw_ctrl_names"].index(control))
                except ValueError:
                    continue
                gui_ctrl_name = rtg["gui_ctrl_names"][rtg["gtrii"][raw_index]]
                gui_ctrl_value = (multiplier - rtg["raw_cut_values"][raw_index]) / rtg["raw_slope_values"][raw_index]
                dcc.cmds_set_attr(gui_ctrl_name, gui_ctrl_value)
                self.ctrls_moved.append(gui_ctrl_name)

    def get_phase_count(self, expression_name):
        return self.window.rig.rig_definition.get_expression_by_name(expression_name).no_phases()

    def propagate_lock_to_views(self, node):
        current_tab_index = self.window.ui["widget"]["graph"].currentIndex()
        for i in range(0, self.window.ui["widget"]["graph"].count()):
            if i == current_tab_index:
                continue
            tab_node = self.window.ui["widget"]["graph"].widget(i).scene().get_node_by_name(node.name)
            if tab_node:
                tab_node.lock_btn.set_locked(node.lock_btn.is_locked())
                tab_node.update_children_disabled_state(skip=True)


# Helpers
# --------------------------------------------
def iter_items(root):
    def recurse(parent):
        for i in range(parent.childCount()):
            child = parent.child(i)
            yield child
            if child.childCount() > 0:
                yield from recurse(child)

    if root is not None:
        yield from recurse(root)
