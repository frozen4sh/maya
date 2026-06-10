# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import Any, Dict, List
from pathlib import Path

# Internal
from mh_pose_editor.extensions.dna_io.model.dna_model import (
    Solver,
    JointGroup,
    MHDNAModel,
)
from mh_pose_editor.extensions.dna_io.model.dna_reader import MHDNAReader


class MHDNAModelValidator:
    @staticmethod
    def validate_model(model) -> List[str]:
        current_file = Path(__file__).resolve()
        root_dir = current_file.parents[5]
        resource_file = root_dir / "resources" / "reference" / "mhb1.dna"
        reader = MHDNAReader(resource_file.as_posix())
        reference_model = reader.read()

        errors: List[str] = []
        errors += MHDNAModelValidator.validate_descriptor(reference_model, model)
        errors += MHDNAModelValidator.validate_definition(reference_model, model)
        errors += MHDNAModelValidator.validate_behavior(reference_model, model)
        errors += MHDNAModelValidator.validate_rbf_behavior(reference_model, model)
        errors += MHDNAModelValidator.validate_twist_swing(reference_model, model)
        errors += MHDNAModelValidator.validate_geometry(reference_model, model)

        return errors

    @staticmethod
    def compare_list_content(name, expected, actual, errors):
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)

        if missing:
            errors.append(f"For '{name}' missing data: {sorted(missing)}")
        if extra:
            errors.append(f"For '{name}' extra data: {sorted(extra)}")

    @staticmethod
    def get_raw_control_name(reference: MHDNAModel, index_list: List[int]) -> List[str]:
        control_names = reference.definition.raw_control_names + ["psd"] * reference.behavior.controls.psd_count
        if reference.rbf_extension is not None and reference.rbf_extension.pose_control_names:
            control_names += reference.rbf_extension.pose_control_names
        result = []
        for index in index_list:
            result.append(control_names[index])
        return result

    @staticmethod
    def get_joint_names(reference: MHDNAModel, index_list: List[int]) -> List[str]:
        return [reference.definition.joint_names[index] for index in index_list]

    @staticmethod
    def get_pose_names(reference: MHDNAModel, index_list: List[int]) -> List[str]:
        if reference.rbf_behavior:
            return [reference.rbf_behavior.poses[index].name for index in index_list]
        return []

    @staticmethod
    def get_solver_names_for_pose(reference: MHDNAModel, index: int) -> List[str]:
        result_solvers = []
        if reference.rbf_behavior:
            for solver in reference.rbf_behavior.solvers:
                if index in solver.pose_indices:
                    result_solvers.append(solver.name)
        return result_solvers

    @staticmethod
    def validate_definition(reference: MHDNAModel, test: MHDNAModel) -> List[str]:
        errors: List[str] = []

        def check_equal(field_name: str) -> None:
            ref_val = getattr(reference.definition, field_name)
            test_val = getattr(test.definition, field_name)
            if ref_val != test_val:
                errors.append(f"Mismatch in '{field_name}' - expected: {ref_val} got: {test_val}")

        def compare_unordered_list(field_name: str) -> None:
            ref_val = getattr(reference.definition, field_name)
            test_val = getattr(test.definition, field_name)
            MHDNAModelValidator.compare_list_content(field_name, ref_val, test_val, errors)

        def compare_joints_in_lods() -> None:
            # It is OK to have subset of the whole list of joints
            ref_mapping = reference.definition.lod_joint_mapping
            test_mapping = test.definition.lod_joint_mapping
            # Check lods list
            if ref_mapping.lods != test_mapping.lods:
                errors.append(
                    f"Mismatch in 'lod_joint_mapping' - expected to have LODs defined as: {ref_mapping.lods} got: {test_mapping.lods}"
                )

            # Check values list
            for i, (ref_values, test_values) in enumerate(zip(ref_mapping.indices, test_mapping.indices)):
                ref_set = set(ref_values)
                test_set = set(test_values)
                extra = test_set - ref_set
                if extra:
                    errors.append(
                        f"Mismatch in 'lod_joint_mapping' - extra joint(s) found {MHDNAModelValidator.get_joint_names(reference, sorted(list(extra)))} for LOD {i}"
                    )

        fields_to_check = [
            "lod_mesh_mapping",
            "lod_blend_shape_mapping",
            "lod_animated_maps_mapping",
            "gui_control_names",
            "raw_control_names",
            "joint_names",
            "mesh_names",
            "joint_hierarchy",
            "blend_shape_channel_names",
            "animated_map_names",
            "mesh_blend_shape_channel_mapping",
        ]

        for field in fields_to_check:
            if field.endswith("_names"):
                compare_unordered_list(field)
            else:
                check_equal(field)
        # Special case in lod_joint_mapping - to confirm with core tech team
        compare_joints_in_lods()

        return errors

    @staticmethod
    def validate_descriptor(reference: MHDNAModel, test: MHDNAModel) -> List[str]:
        errors: List[str] = []

        def check_equal(field_name: str) -> None:
            ref_val = getattr(reference.descriptor, field_name)
            test_val = getattr(test.descriptor, field_name)
            if ref_val != test_val:
                errors.append(f"Mismatch in '{field_name}' - expected: {ref_val} got: {test_val}")

        fields_to_check = [
            "translation_unit",
            "rotation_unit",
            "lod_count",
            "max_lod",
            "db_name",
        ]

        for field in fields_to_check:
            check_equal(field)

        # Check coordinate system
        if (
            reference.descriptor.coordinate_system.coor_sys.xAxis != test.descriptor.coordinate_system.coor_sys.xAxis
            or reference.descriptor.coordinate_system.coor_sys.yAxis != test.descriptor.coordinate_system.coor_sys.yAxis
            or reference.descriptor.coordinate_system.coor_sys.zAxis != test.descriptor.coordinate_system.coor_sys.zAxis
        ):
            errors.append(
                f"Mismatch in coordinate system - expected: {reference.descriptor.coordinate_system} "
                f"got: {test.descriptor.coordinate_system}"
            )

        return errors

    @staticmethod
    def validate_behavior(reference: MHDNAModel, test: MHDNAModel) -> List[str]:
        errors: List[str] = []

        ref_groups: List[JointGroup] = reference.behavior.joint_groups
        test_groups: List[JointGroup] = test.behavior.joint_groups

        if len(ref_groups) != len(test_groups):
            errors.append(f"Joint groups count mismatch - expected:{len(ref_groups)} got:{len(test_groups)}")
            return errors

        for i, (rg, tg) in enumerate(zip(ref_groups, test_groups)):
            solver_name = str(i)
            if reference.rbf_behavior:
                solver_name = reference.rbf_behavior.solvers[i].name

            if rg.lods != tg.lods:
                errors.append(
                    f"For joint group (solver) {solver_name} expected LOD values are: {rg.lods} got: {tg.lods}"
                )

            if sorted(rg.input_indices) != sorted(tg.input_indices):
                errors.append(
                    f"For joint group (solver) {solver_name} expected input controls are: {MHDNAModelValidator.get_raw_control_name(reference, sorted(rg.input_indices))} got: {MHDNAModelValidator.get_raw_control_name(reference, sorted(tg.input_indices))}"
                )

            if sorted(rg.joint_indices) != sorted(tg.joint_indices):
                errors.append(
                    f"For joint group (solver) {solver_name} expected joints are: {MHDNAModelValidator.get_joint_names(reference, sorted(rg.joint_indices))} got: {MHDNAModelValidator.get_joint_names(reference, sorted(tg.joint_indices))}"
                )

        return errors

    @staticmethod
    def validate_twist_swing(reference: MHDNAModel, test: MHDNAModel) -> List[str]:
        errors: List[str] = []

        ref_twist_swing = reference.twist_swing
        test_twist_swing = test.twist_swing

        if ref_twist_swing is None and test_twist_swing is None:
            return errors

        if test_twist_swing is None:
            errors.append("Missing twist and swing data")
            return errors

        def entry_signature(e):
            return tuple(sorted(e.input_indices)), tuple(sorted(e.output_indices))

        def compare_entries(name, ref_list, test_list):
            ref_keys = {entry_signature(e) for e in ref_list}
            test_keys = {entry_signature(e) for e in test_list}

            missing = ref_keys - test_keys
            extra = test_keys - ref_keys

            for input_idx, output_idx in sorted(missing):
                errors.append(
                    f"{name} missing data:\n  driver joint attributes {MHDNAModelValidator.get_raw_control_name(reference, list(input_idx))}\n  driven joint(s) {MHDNAModelValidator.get_joint_names(reference, list(output_idx))}"
                )

            for input_idx, output_idx in sorted(extra):
                errors.append(
                    f"{name} found extra data:\n  driver joint attributes {MHDNAModelValidator.get_raw_control_name(reference, list(input_idx))}\n  driven joint(s) {MHDNAModelValidator.get_joint_names(reference, list(output_idx))}"
                )

        if ref_twist_swing and test_twist_swing:
            compare_entries("Twist", ref_twist_swing.twist, test_twist_swing.twist)
            compare_entries("Swing", ref_twist_swing.swing, test_twist_swing.swing)

        return errors

    @staticmethod
    def validate_geometry(reference: MHDNAModel, test: MHDNAModel) -> List[str]:
        errors: List[str] = []

        ref_geometry = reference.geometry
        test_geometry = test.geometry

        if ref_geometry is None and test_geometry is None:
            return errors

        if test_geometry is None:
            errors.append("Missing geometry data")
            return errors

        if ref_geometry and test_geometry:
            if len(ref_geometry.meshes) != len(test_geometry.meshes):
                errors.append(
                    f"Mesh count mismatch - expected:{len(ref_geometry.meshes)} got:{len(test_geometry.meshes)}"
                )
                return errors

            for i, (m1, m2) in enumerate(zip(ref_geometry.meshes, test_geometry.meshes)):
                # Compare influences
                if m1.maximum_influence_per_vertex < m2.maximum_influence_per_vertex:
                    errors.append(
                        f"For mesh '{test.definition.mesh_names[i]}' number of influence per vertex is higher than "
                        f"expected:{m1.maximum_influence_per_vertex} got:{m2.maximum_influence_per_vertex}"
                    )
                # Validate layout fields
                for layout_index, (layout1, layout2) in enumerate(zip(m1.layouts, m2.layouts)):
                    MHDNAModelValidator.compare_list_content(
                        f"mesh '{test.definition.mesh_names[i]}' layout {layout_index}", layout1, layout2, errors
                    )
                # Compare faces
                if len(m1.faces) != len(m2.faces):
                    errors.append(
                        f"For mesh '{test.definition.mesh_names[i]}' face count mismatch - expected:{len(m1.faces)} got:{len(m2.faces)}"
                    )
                else:
                    for j, (f1, f2) in enumerate(zip(m1.faces, m2.faces)):
                        if f1 != f2:
                            errors.append(
                                f" For mesh '{test.definition.mesh_names[i]}' face {j} mismatch - expected:{f1} got:{f2}"
                            )

        return errors

    @staticmethod
    def validate_rbf_behavior(reference: MHDNAModel, test: MHDNAModel) -> List[str]:
        errors: List[str] = []

        if reference.rbf_behavior is None and test.rbf_behavior is None:
            return errors

        if test.rbf_behavior is None:
            errors.append("Missing RBF data")
            return errors

        for lod_index, (ref_indices, test_indices) in enumerate(
            zip(reference.rbf_behavior.lod_solver_mapping.indices, test.rbf_behavior.lod_solver_mapping.indices)  # type: ignore
        ):
            if ref_indices != test_indices:
                errors.append(f" Expected solvers at LOD {lod_index} are {ref_indices}:\n" f" Found:    {test_indices}")

        def solver_as_dict(solver: Solver) -> Dict[str, Any]:
            return {
                "name": solver.name,
                "raw_control_indices": solver.raw_control_indices,
                "pose_indices": solver.pose_indices,
            }

        def validate_rbf_solvers() -> None:
            def solver_list_to_dict(solvers):
                return {s.name: solver_as_dict(s) for s in solvers}

            if reference.rbf_behavior and test.rbf_behavior:
                ref_dict = solver_list_to_dict(reference.rbf_behavior.solvers)
                test_dict = solver_list_to_dict(test.rbf_behavior.solvers)

                ref_names = set(ref_dict.keys())
                test_names = set(test_dict.keys())

                missing = ref_names - test_names
                extra = test_names - ref_names
                common = ref_names & test_names

                if missing:
                    errors.append(f"Missing solvers: {sorted(missing)}")
                if extra:
                    errors.append(f"Extra solvers found: {sorted(extra)}")

                for name in common:
                    ref_solver = ref_dict[name]
                    test_solver = test_dict[name]
                    for key in ref_solver:
                        if ref_solver[key] != test_solver[key]:
                            if key == "raw_control_indices":
                                errors.append(
                                    f" For solver '{name}' driver data mismatch:\n"
                                    f"  expected: {MHDNAModelValidator.get_raw_control_name(reference, ref_solver[key])}\n"
                                    f"  found:    {MHDNAModelValidator.get_raw_control_name(test, test_solver[key])}"
                                )
                            elif key == "pose_indices":
                                errors.append(
                                    f" For solver '{name}' pose data mismatch:\n"
                                    f"  expected: {MHDNAModelValidator.get_pose_names(reference, ref_solver[key])}\n"
                                    f"  found:    {MHDNAModelValidator.get_pose_names(test, test_solver[key])}"
                                )

        if reference.rbf_behavior and test.rbf_behavior:
            validate_rbf_solvers()
            ref_pose_map = {p.name: (p, i) for i, p in enumerate(reference.rbf_behavior.poses)}
            test_pose_map = {p.name: (p, i) for i, p in enumerate(test.rbf_behavior.poses)}

            ref_names = set(ref_pose_map.keys())
            test_names = set(test_pose_map.keys())

            missing = ref_names - test_names
            extra = test_names - ref_names

            for name in missing:
                index = ref_pose_map[name][1]
                errors.append(
                    f"Missing pose '{name}' in solver(s) '{MHDNAModelValidator.get_solver_names_for_pose(reference, index)}'"
                )

            for name in extra:
                index = test_pose_map[name][1]
                errors.append(
                    f"Extra pose '{name}' in solver(s) '{MHDNAModelValidator.get_solver_names_for_pose(test, index)}'"
                )

        return errors
