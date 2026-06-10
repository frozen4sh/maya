# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import List, Tuple
from collections import Counter

# Internal
from mh_pose_editor.extensions.dna_io.model.dna_model import MHDNAModel


class DNAModelValidator:
    def __init__(self, model: MHDNAModel) -> None:
        self._model: MHDNAModel = model
        self._errors: List[str] = []
        self._warnings: List[str] = []

    def check_model(self) -> Tuple[List[str], List[str]]:
        self._check_lods()
        self._check_meshes()
        self._check_solvers()
        self._check_controls()
        self._check_joints()
        return self._errors, self._warnings

    def _check_lods(self) -> None:
        """
        Check all LODs mentions in model and verify to have the same size everywhere.
        """
        lod_count = self._model.descriptor.lod_count
        # Check definition
        lod_count_joint = len(self._model.definition.lod_joint_mapping.lods)
        lod_count_bs = len(self._model.definition.lod_blend_shape_mapping.lods)
        lod_count_am = len(self._model.definition.lod_animated_maps_mapping.lods)
        lod_count_mesh = len(self._model.definition.lod_mesh_mapping.lods)

        if lod_count != lod_count_joint:
            self._errors.append(
                f"Incorrect number of LODs defined for joints - expected {lod_count} got:{lod_count_joint}"
            )
        if len(self._model.definition.mesh_names) != 0 and lod_count != lod_count_mesh:
            self._errors.append(
                f"Incorrect number of LODs defined for meshes - expected:{lod_count} got:{lod_count_mesh}"
            )
        if len(self._model.definition.blend_shape_channel_names) > 0 and lod_count != lod_count_bs:
            self._errors.append(
                f"Incorrect number of LODs defined for blend shapes - expected {lod_count} got:{lod_count_bs}"
            )
        if len(self._model.definition.animated_map_names) > 0 and lod_count != lod_count_am:
            self._errors.append(
                f"Incorrect number of LODs defined for animated maps - expected {lod_count} got:{lod_count_am}"
            )
        if self._model.rbf_behavior:
            lod_count_solver = len(self._model.rbf_behavior.lod_solver_mapping.lods)
            if lod_count != lod_count_solver:
                self._errors.append(
                    f"Incorrect number of LODs defined for solvers - expected {lod_count} got:{lod_count_solver}"
                )

        # Check joint groups
        for i, jnt_group in enumerate(self._model.behavior.joint_groups):
            if lod_count != len(jnt_group.lods):
                self._errors.append(
                    f"Incorrect number of LODs defined for joint group {i} - expected {lod_count} got:{len(jnt_group.lods)}"
                )

    def _check_controls(self) -> None:
        # Check for duplicates
        counts = Counter(self._model.definition.raw_control_names)
        duplicates = [item for item, count in counts.items() if count > 1]
        if duplicates:
            self._errors.append(f"Duplicate raw control name(s) found [{duplicates}]")

        # Check for name
        for name in self._model.definition.raw_control_names:
            if (
                not name.endswith(".qx")
                and not name.endswith(".qy")
                and not name.endswith(".qz")
                and not name.endswith(".qw")
            ):
                self._errors.append(f"Raw control name '{name}' must end with .qx/qy/qz/qw")
        # Check twist/swing
        if self._model.twist_swing:
            control_count = len(self._model.definition.raw_control_names)
            joint_count = len(self._model.definition.joint_names)
            for i, twist in enumerate(self._model.twist_swing.twist):
                for input_index in twist.input_indices:
                    if input_index < 0 or input_index >= control_count:
                        self._errors.append(
                            f"Wrong twist input index {input_index} found in '{i}' setup. "
                            f"Index should be in range (0-{control_count - 1})"
                        )
                for joint_index in twist.output_indices:
                    if joint_index < 0 or joint_index >= joint_count:
                        self._errors.append(
                            f"Wrong twist output joint index {joint_index} found in '{i}' setup."
                            f" Joint index should be in range (0-{joint_count - 1})"
                        )
                for value in twist.weights:
                    if value < 0 or value > 1:
                        self._errors.append(
                            f"Wrong twist value {value} found in '{i}' setup. Value should be in range (0-1)"
                        )

            for i, swing in enumerate(self._model.twist_swing.swing):
                for input_index in swing.input_indices:
                    if input_index < 0 or input_index >= control_count:
                        self._errors.append(
                            f"Wrong swing input index {input_index} found in '{i}' setup. "
                            f"Index should be in range (0-{control_count - 1})"
                        )
                for joint_index in swing.output_indices:
                    if joint_index < 0 or joint_index >= joint_count:
                        self._errors.append(
                            f"Wrong swing output joint index {joint_index} found in '{i}' setup. "
                            f"Joint index should be in range (0-{joint_count - 1})"
                        )
                for value in swing.weights:
                    if value < 0 or value > 1:
                        self._errors.append(
                            f"Wrong swing value {value} found in '{i}' setup. Value should be in range (0-1)"
                        )

    def _check_meshes(self) -> None:
        """
        Check meshes mentions in model and verify to have the same size everywhere.
        Additionally, mesh name must be unique.
        """
        # Check for duplicates
        counts = Counter(self._model.definition.mesh_names)
        duplicates = [item for item, count in counts.items() if count > 1]
        if duplicates:
            self._errors.append(f"Duplicate mesh names found [{duplicates}]")

        # Check for indices
        mesh_count = len(self._model.definition.mesh_names)
        if self._model.geometry:
            if len(self._model.geometry.meshes) != mesh_count:
                self._errors.append(
                    f"Wrong number of meshes found in geometry layer - expected:{mesh_count} got:{len(self._model.geometry.meshes)}"
                )

            # Check geometry
            if len(self._model.geometry.meshes) > 0:
                for i in range(mesh_count):
                    mesh_name = self._model.definition.mesh_names[i]
                    pos_count = len(self._model.geometry.meshes[i].positions)
                    tex_coor_count = len(self._model.geometry.meshes[i].texture_coordinates)
                    nor_count = len(self._model.geometry.meshes[i].normals)

                    layouts_count = len(self._model.geometry.meshes[i].layouts)
                    index_mismatch = 0

                    for layout in self._model.geometry.meshes[i].layouts:
                        if layout[0] != layout[2]:
                            index_mismatch += 1
                        for index, value in enumerate(layout):
                            if (index == 0) and (value < 0 or value >= pos_count):
                                self._errors.append(
                                    f"Wrong position index {value} found for mesh {mesh_name}. Index should be in range (0-{pos_count - 1})"
                                )
                            if (index == 1) and (value < 0 or value >= tex_coor_count):
                                self._errors.append(
                                    f"Wrong texture coordinate index {value} found for mesh {mesh_name}. "
                                    f"Index should be in range (0-{tex_coor_count - 1})"
                                )
                            if (index == 2) and (value < 0 or value >= nor_count):
                                self._errors.append(
                                    f"Wrong normal index {value} found for mesh {mesh_name}. "
                                    f"Index should be in range (0-{nor_count - 1})"
                                )

                    if index_mismatch > 0:
                        self._warnings.append(
                            f"For mesh '{mesh_name}' found mismatch in position and normal layout indices."
                        )

                    invalid = [
                        (face_idx, f)
                        for face_idx, face in enumerate(self._model.geometry.meshes[i].faces)
                        for f in face
                        if f < 0 or f >= layouts_count
                    ]
                    if invalid:
                        for face_idx, idx in invalid:
                            self._errors.append(
                                f"Wrong layout index {idx} in face {face_idx} found for mesh {mesh_name}. "
                                f"Index should be in range (0-{layouts_count - 1})"
                            )

    def _check_solvers(self) -> None:
        """
        Check solvers in model and verify to have the same size everywhere.
        Additionally, solver name must be unique.
        """

        if self._model.rbf_behavior:
            # Check for duplicates
            solver_names = [s.name for s in self._model.rbf_behavior.solvers]
            counts = Counter(solver_names)
            duplicates = [item for item, count in counts.items() if count > 1]
            if duplicates:
                self._errors.append(f"Duplicate solver name(s) found [{duplicates}]")

            solver_count = len(solver_names)
            # Check if in lod mapping values are correct
            for solver_indices in self._model.rbf_behavior.lod_solver_mapping.indices:
                for index in solver_indices:
                    if index < 0 or index >= solver_count:
                        self._errors.append(
                            f"Wrong solver index {index} found in lod solver mapping. Index should be in range (0-{solver_count - 1})"
                        )

            pose_count = len(self._model.rbf_behavior.poses)
            control_count = len(self._model.definition.raw_control_names)
            for i, solver in enumerate(self._model.rbf_behavior.solvers):
                # Check if raw control values have correct number
                if len(solver.raw_control_values) != len(solver.raw_control_indices) * len(solver.pose_indices):
                    self._errors.append(
                        f"Wrong number of control values for solver {solver.name}. Expected number is "
                        f"{len(solver.raw_control_indices) * len(solver.pose_indices)}, found {len(solver.raw_control_values)}"
                    )
                # Check pose indices
                for pose_index in self._model.rbf_behavior.solvers[i].pose_indices:
                    if pose_index < 0 or pose_index >= pose_count:
                        self._errors.append(
                            f"Wrong pose index {pose_index} found for solver {solver.name}. Index should be in range (0-{pose_count - 1})"
                        )
                for control_index in self._model.rbf_behavior.solvers[i].raw_control_indices:
                    if control_index < 0 or control_index >= control_count:
                        self._errors.append(
                            f"Wrong control index {control_index} found for solver {solver.name}. Index should be in "
                            f"range (0-{control_count - 1})"
                        )

            if self._model.rbf_extension:
                full_control_count = self._get_control_count()
                for i, pose in enumerate(self._model.rbf_extension.poses):
                    for pose_output_index in pose.output_control_indices:
                        if pose_output_index < 0 or pose_output_index >= full_control_count:
                            self._errors.append(
                                f"Wrong control output index {pose_output_index} found for pose "
                                f"{self._model.rbf_extension.pose_control_names[i]}. Index should be in range (0-{full_control_count - 1})"
                            )

    def _get_control_count(self) -> int:
        control_count = len(self._model.definition.raw_control_names) + self._model.behavior.controls.psd_count
        if self._model.rbf_extension is not None and self._model.rbf_extension.pose_control_names:
            control_count += len(self._model.rbf_extension.pose_control_names)
        return control_count

    def _check_joints(self) -> None:
        """
        Check joints in model and verify to have the same size everywhere.
        Additionally, joint name must be unique.
        """
        # Check for duplicates
        counts = Counter(self._model.definition.joint_names)
        duplicates = [item for item, count in counts.items() if count > 1]
        if duplicates:
            self._errors.append(f"Duplicate joint names found [{duplicates}]")

        lod_joint_indices = self._model.definition.lod_joint_mapping.indices
        # Check joints in LODs - joint in lower LOD
        for i in range(len(lod_joint_indices) - 1, 0, -1):
            current = lod_joint_indices[i]
            previous = lod_joint_indices[i - 1]
            wrong_values = [self._model.definition.joint_names[value] for value in current if value not in previous]
            if wrong_values:
                self._errors.append(
                    f"For lower LODs found joints not present in higher LODs. For lod {i} wrong "
                    f"joints are [{wrong_values}]"
                )
        # Check joints in LODs - joint hierarchy
        for i, lod_indices in enumerate(lod_joint_indices):
            wrong_values = [
                self._model.definition.joint_names[self._model.definition.joint_hierarchy[value]]
                for value in lod_indices
                if self._model.definition.joint_hierarchy[value] not in lod_indices
            ]
            if wrong_values:
                self._errors.append(f"Joint hierarchy error in lod {i}. Missing joints are {set(wrong_values)}")

        joint_count = len(self._model.definition.joint_names)
        control_count = self._get_control_count()

        # Check skinning
        if self._model.geometry:
            for i, mesh in enumerate(self._model.geometry.meshes):
                mesh_name = self._model.definition.mesh_names[i]
                skin_weights_count = len(mesh.skin_weights)
                # influences = set()
                for vtx, sw in enumerate(mesh.skin_weights):
                    num_of_influence = len(sw.joint_indices)
                    # influences.add(num_of_influence)
                    if num_of_influence > mesh.maximum_influence_per_vertex:
                        self._warnings.append(
                            f"For mesh {mesh_name} found more influence per vertex than allowed. It should be {mesh.maximum_influence_per_vertex}, but for vertex {vtx} there are {num_of_influence})"
                        )
                    for jnt in sw.joint_indices:
                        if jnt < 0 or jnt >= joint_count:
                            self._errors.append(
                                f"Wrong joint index {jnt} found in skinning section for the mesh "
                                f"{mesh_name}. Index should be in range (0-{joint_count - 1})"
                            )
                if skin_weights_count != len(mesh.positions):
                    self._errors.append(
                        f"Wrong number of skin weights found for mesh {mesh_name}. Expected: {len(mesh.positions)} got:  {skin_weights_count}"
                    )
                # print(f"Influences for {mesh_name} is {influences}")

        # Check joint groups
        for i, group in enumerate(self._model.behavior.joint_groups):
            for joint_index in group.joint_indices:
                if joint_index < 0 or joint_index >= joint_count:
                    self._errors.append(
                        f"Wrong joint index {joint_index} found in joint group section '{i}'. "
                        f"Index should be in range (0-{joint_count - 1})"
                    )
            for input_index in group.input_indices:
                if input_index < 0 or input_index >= control_count:
                    self._errors.append(
                        f"Wrong input index {input_index} found in joint group section '{i}'. "
                        f"Index should be in range (0-{control_count - 1})"
                    )
            if (len(group.input_indices) * len(group.output_indices)) != len(group.values):
                self._errors.append(
                    f"Wrong number of values in joint group '{i}'. Expected: "
                    f"{len(group.input_indices) * len(group.output_indices)} got: {len(group.values)}"
                )
            for lod in group.lods:
                if lod > len(group.output_indices):
                    self._errors.append(
                        f"Wrong number of output indices in lod in joint group '{i}'. Max value could be: "
                        f"{len(group.output_indices)} got: {lod}"
                    )
