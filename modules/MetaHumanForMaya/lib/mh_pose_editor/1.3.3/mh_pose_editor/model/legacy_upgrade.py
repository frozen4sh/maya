# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import re
import copy
import json
from typing import Any, Dict, List
from pathlib import Path

# External
from maya import cmds
from maya.api import OpenMaya as om

# Internal
from mh_pose_editor import api
from mh_pose_editor.log import LOG
from mh_pose_editor.model import utils
from mh_pose_editor.model.serializers import dna_serializer_2_5
from mh_pose_editor.extensions.dna_io.model import dna_model, dna_writer


def get_hierarchy(joint: str, existing_hierarchy: List[str]) -> None:
    for child_joint in cmds.listRelatives(joint, children=True, type="joint") or []:
        existing_hierarchy.append(child_joint)
        get_hierarchy(child_joint, existing_hierarchy)


class SceneConverter:
    """
    {
      "transform_mapping": {
        "root_drv": "root"
      },
      "search": "(?P<transform>[a-zA-Z0-9_]+)(?P<suffix>_drv)",
      "replace": "{transform}",
      "map_hierarchy": true,
        // string or regex can be specified for simple/complex mapping
      "mapping_mode": "regex"
    }
    """

    def __init__(self, conversion_data: Dict[str, Any]) -> None:
        self._conversion_data = conversion_data
        self._transform_mapping: Dict[str, str] = {}
        self.generate_mapping()

    @property
    def conversion_data(self) -> Dict[str, Any]:
        return copy.deepcopy(self._conversion_data)

    @property
    def transform_mapping(self) -> Dict[str, str]:
        return copy.deepcopy(self._transform_mapping)

    def generate_mapping(self):
        if self._conversion_data.get("map_hierarchy", False):
            transform_mapping = self._conversion_data.get("transform_mapping", {})
            source = list(transform_mapping.keys())
            target = list(transform_mapping.values())

            new_source = []
            for joint in source:
                new_source.append(joint)
                get_hierarchy(joint, new_source)

            new_target = []
            for joint in target:
                new_target.append(joint)
                get_hierarchy(joint, new_target)

            self._conversion_data["mapped_hierarchies"] = [new_source, new_target]

        self._transform_mapping = self._generate_mapping()

    def _generate_mapping(self) -> Dict[str, Any]:
        mapping_mode = self._conversion_data.get("mapping_mode", "replace")
        search = self._conversion_data.get("search")
        replace = self._conversion_data.get("replace")

        mapping_data: Dict[str, str] = {}
        if self._conversion_data.get("map_hierarchy", False):
            mapped_hierarchies = self._conversion_data.get("mapped_hierarchies", [])
            if not mapped_hierarchies or len(mapped_hierarchies) != 2:
                LOG.warning(
                    "Unable to generate conversion mapping using `map_hierarchy`."
                    f" Expected 2 hierarchies, found {len(mapped_hierarchies)}"
                )
                return mapping_data

            if mapping_mode == "regex" and search and replace:
                out_hierarchy = mapped_hierarchies[1]
                for joint in mapped_hierarchies[0]:
                    match = re.match(pattern=search, string=joint)
                    if match:
                        out_joint = replace.format(**match.groupdict())
                        if out_joint in out_hierarchy:
                            mapping_data[joint] = out_joint

            elif mapping_mode == "replace" and search and replace:
                out_hierarchy = mapped_hierarchies[1]
                for joint in mapped_hierarchies[0]:
                    out_joint = joint.replace(search, replace)
                    if out_joint in out_hierarchy:
                        mapping_data[joint] = out_joint

        else:
            for in_transform, out_transform in self._conversion_data.get("transform_mapping", {}).items():
                data = (in_transform, out_transform)
                mapping_data[data[0]] = data[1]

        return mapping_data


def upgrade_scene(dna_path: Path, generate_default_swing_twist: bool) -> bool:
    """
    Upgrade a legacy metahuman scene to be compatible with PoseEditor. This process will remove the driver skeleton
    and replace the swing/twist maya node setup with the SwingTwistEvaluator plugin
    """
    converter_path = Path(__file__).parents[1] / "resources" / "converters" / "metahuman.json"
    with open(converter_path) as f:
        converter = SceneConverter(json.loads(f.read()))

    # To successfully convert a legacy MetaHuman scene to a DNA compatible scene, the driver skeleton must be removed.
    # To do this, it uses the data from within the metahuman.json file to map the joints from the driver skeleton to
    # the driven skeleton and recalculates the matrix for each pose + joint to generate a new serialized solver cache
    # that can be passed to the serialization framework.
    cached_solver_data = []
    pose_editor_api = api.PoseEditor()
    solvers = pose_editor_api.rbf_solvers
    for solver in solvers:
        pose_index = 0

        # List to store the default position of the driver matrices
        default_pose_driver_matrices = []
        default_pose_driven_matrices = []
        solver_data = solver.data(enum_values=False)
        solver_data["drivers"] = []
        for driver in solver.drivers():
            new_driver = converter.transform_mapping.get(driver)
            if new_driver:
                solver_data["drivers"].append(new_driver)

        solver_data["driven_transforms"] = []
        for driven in solver.driven_joints():
            new_driven = converter.transform_mapping.get(driven)
            if new_driven:
                solver_data["driven_transforms"].append(new_driven)

        for pose in solver.poses():
            solver.go_to_pose(pose)
            solver_data["poses"][pose]["drivers"] = []
            solver_data["poses"][pose]["driven"] = {}
            driver_index = 0
            for driver in solver.drivers():
                new_driver = converter.transform_mapping.get(driver)
                if not new_driver:
                    continue

                if pose_index == 0:
                    default_pose_driver_matrices.append(
                        om.MMatrix(utils.get_local_matrix_without_joint_orient(new_driver))
                    )
                default_matrix = default_pose_driver_matrices[driver_index]
                new_matrix = om.MMatrix(utils.get_local_matrix_without_joint_orient(new_driver))
                # Store the delta
                solver_data["poses"][pose]["drivers"].append(list(new_matrix * default_matrix.inverse()))
                driver_index += 1

            driven_index = 0
            for driven in solver.driven_joints():
                new_driven = converter.transform_mapping.get(driven)
                if not new_driven:
                    continue

                if pose_index == 0:
                    default_pose_driven_matrices.append(
                        om.MMatrix(utils.get_local_matrix_without_joint_orient(new_driven))
                    )

                default_matrix = default_pose_driven_matrices[driven_index]
                new_matrix = om.MMatrix(utils.get_local_matrix_without_joint_orient(new_driven))
                # Store the delta
                solver_data["poses"][pose]["driven"][new_driven] = list(new_matrix * default_matrix.inverse())
                driven_index += 1

            pose_index += 1
        solver.go_to_pose("default")
        cached_solver_data.append(solver_data)

    model = dna_serializer_2_5.Serializer.serialize(
        solvers=[],
        export_selected=False,
        export_geometry=True,
        export_rbf=True,
        export_swing_twist=True,
        solver_data_cache=cached_solver_data,
    )
    # Swing twists are not present in a legacy scene with the new nodes, so must be optionally added back in.
    # If the joints for the swing or twist don't exist anymore, they will be skipped.
    if generate_default_swing_twist:
        legacy_twists: Dict[str, Dict[str, Any]] = {
            "foot_l": {"outputs": ["calf_twist_02_l", "calf_twist_01_l"], "weights": [0.5, 0.0]},
            "foot_r": {"outputs": ["calf_twist_02_r", "calf_twist_01_r"], "weights": [0.5, 0.0]},
            "hand_l": {"outputs": ["lowerarm_twist_02_l", "lowerarm_twist_01_l"], "weights": [0.8, 0.2]},
            "hand_r": {"outputs": ["lowerarm_twist_02_r", "lowerarm_twist_01_r"], "weights": [0.8, 0.2]},
            "thigh_l": {"outputs": ["thigh_twist_01_l", "thigh_twist_02_l"], "weights": [0.0, 0.5]},
            "thigh_r": {"outputs": ["thigh_twist_01_r", "thigh_twist_02_r"], "weights": [0.0, 0.5]},
            "upperarm_l": {"outputs": ["upperarm_twist_01_l", "upperarm_twist_02_l"], "weights": [0.2, 0.8]},
            "upperarm_r": {"outputs": ["upperarm_twist_01_r", "upperarm_twist_02_r"], "weights": [0.2, 0.8]},
        }
        legacy_swings: Dict[str, Dict[str, Any]] = {
            "calf_l": {"outputs": ["calf_correctiveRoot_l"], "weights": [0.5]},
            "calf_r": {"outputs": ["calf_correctiveRoot_r"], "weights": [0.5]},
            "lowerarm_l": {"outputs": ["lowerarm_correctiveRoot_l"], "weights": [0.5]},
            "lowerarm_r": {"outputs": ["lowerarm_correctiveRoot_r"], "weights": [0.5]},
            "thigh_l": {"outputs": ["thigh_correctiveRoot_l"], "weights": [0.5]},
            "thigh_r": {"outputs": ["thigh_correctiveRoot_r"], "weights": [0.5]},
            "upperarm_l": {"outputs": ["upperarm_correctiveRoot_l"], "weights": [0.5]},
            "upperarm_r": {"outputs": ["upperarm_correctiveRoot_r"], "weights": [0.5]},
        }
        twists = []
        swings = []

        for twist_input, twist_data in legacy_twists.items():
            valid_outputs = all([cmds.ls(out, type="joint") for out in twist_data["outputs"]])
            if cmds.ls(twist_input, type="joint") and valid_outputs:
                twists.append(
                    dna_model.Setup(
                        [
                            model.definition.raw_control_names.index(control)
                            for control in [
                                f"{twist_input}.qx",
                                f"{twist_input}.qy",
                                f"{twist_input}.qz",
                                f"{twist_input}.qw",
                            ]
                        ],
                        [model.definition.joint_names.index(joint) for joint in twist_data["outputs"]],
                        twist_data["weights"],
                    )
                )

        for swing_input, swing_data in legacy_swings.items():
            valid_outputs = all([cmds.ls(out, type="joint") for out in swing_data["outputs"]])
            if cmds.ls(swing_input, type="joint") and valid_outputs:
                swings.append(
                    dna_model.Setup(
                        [
                            model.definition.raw_control_names.index(control)
                            for control in [
                                f"{swing_input}.qx",
                                f"{swing_input}.qy",
                                f"{swing_input}.qz",
                                f"{swing_input}.qw",
                            ]
                        ],
                        [model.definition.joint_names.index(joint) for joint in swing_data["outputs"]],
                        swing_data["weights"],
                    )
                )

        model.twist_swing = dna_model.TwistSwing(twist=twists, swing=swings)
    # Write the new model to a dna file
    writer = dna_writer.MHDNAWriter(dna_path.as_posix())
    writer.write(model)

    # Clear the scene
    cmds.file(new=True, force=True)
    # Load the dna file
    pose_editor_api.deserialize_from_file(
        dna_path,
        import_skeleton=True,
        import_geometry=True,
        unpack_riglogic=True,
        import_rbf=True,
        import_swing_twist=True,
        import_prefix="body",
        up_axis=cmds.upAxis(query=True, axis=True),
    )
    return True
