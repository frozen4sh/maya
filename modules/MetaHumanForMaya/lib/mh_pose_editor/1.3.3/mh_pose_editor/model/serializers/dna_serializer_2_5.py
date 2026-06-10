# Copyright Epic Games, Inc. All Rights Reserved.


# Built-in
import copy
from typing import Any, Set, Dict, List, Tuple, Optional, cast
from dataclasses import field, dataclass

# External
from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import utils, rbf_node
from mh_pose_editor.model.serializers import base_serializer
from mh_pose_editor.model.swing_twist import create_swing_twist_evaluator
from mh_pose_editor.extensions.dna_io.model import dna_model


@dataclass
class LodGroup:
    """
    Simple container to map geometry, joints and rbf solvers to a specific lod level
    """

    geometry: List[str] = field(default_factory=list)
    joints: List[str] = field(default_factory=list)
    solvers: List[rbf_node.RBFNode] = field(default_factory=list)


def get_hierarchy(joint: str, existing_hierarchy: List[str]) -> None:
    """
    Get the full hierarchy from a specific joint, recursive.
    """
    for child_joint in cmds.listRelatives(joint, children=True, type="joint") or []:
        existing_hierarchy.append(child_joint)
        get_hierarchy(child_joint, existing_hierarchy)


def get_root_joint(joint: str) -> str:
    """
    Get the top most joint from any given joint.
    """
    parent = cmds.listRelatives(joint, parent=True, type="joint")
    if parent:
        return get_root_joint(parent[0])

    return joint


def get_dna_parent_hierarchy(joint_name: str, dna_model_ref: dna_model.MHDNAModel) -> List[str]:
    """
    Get the full joint chain for a specific joint from the dna model.
    """
    # Create a mapping from the joint name to the index in the joint hierarchy
    joint_hierarchy = {
        dna_model_ref.definition.joint_names[index]: i
        for index, i in enumerate(dna_model_ref.definition.joint_hierarchy)
    }

    found_hierarchy = []

    def _nested_get_parent_hierarchy(name: str) -> None:
        """
        Recursive function to find the parent joints from the map.
        """
        parent_joint_index = joint_hierarchy[name]
        parent_joint = dna_model_ref.definition.joint_names[parent_joint_index]
        found_hierarchy.append(parent_joint)
        if parent_joint == name:
            return

        _nested_get_parent_hierarchy(parent_joint)

    _nested_get_parent_hierarchy(joint_name)

    return list(found_hierarchy)


def get_skin_cluster(mesh_name: str) -> Optional[oma.MFnSkinCluster]:
    """
    Attempt to get the MFnSkinCluster from a mesh
    """
    # Get the deformers
    mesh_shape = cmds.listRelatives(mesh_name, shapes=True)[0]
    deformers = cmds.listHistory(mesh_shape, pruneDagObjects=True)

    # Get the skin clusters
    skin_clusters = cmds.ls(deformers, type="skinCluster")

    if not skin_clusters:
        return None

    # Convert to OpenMaya representation
    sel = om.MSelectionList()
    sel.add(skin_clusters[0])
    skin_cluster_mobject = sel.getDependNode(0)

    return oma.MFnSkinCluster(skin_cluster_mobject)


def extract_solver_data(model: dna_model.MHDNAModel) -> Dict[str, Any]:
    """
    Extract the RBF Solver data portion from a MHDNAModel in a format compatible with the RBFNode deserialization.
    """
    serialized_solver_data: Dict[str, Any] = {}

    # If the rbf behavior layer is empty, exit early
    if not model.rbf_behavior:
        return serialized_solver_data

    # Neutral joints in the DNA represent the relative translation of each joint and the joint orient values.
    # Rotations are expected to be 0 for a skeleton in the bind pose.
    neutral_joint_transforms: Dict[str, Dict[str, Tuple[float, float, float]]] = {
        joint_name: {
            "translate": (
                model.definition.neutral_joint_translations["xs"][joint_index],
                model.definition.neutral_joint_translations["ys"][joint_index],
                model.definition.neutral_joint_translations["zs"][joint_index],
            ),
            "rotate": (
                model.definition.neutral_joint_rotations["xs"][joint_index],
                model.definition.neutral_joint_rotations["ys"][joint_index],
                model.definition.neutral_joint_rotations["zs"][joint_index],
            ),
        }
        for joint_index, joint_name in enumerate(model.definition.joint_names)
    }

    # Iterate over the solvers in the model
    for index, solver in enumerate(model.rbf_behavior.solvers):
        # The driven channels, values and pose indices for RBF data are stored in the joint groups. This extraction
        # process assumes no other data has been stored in the joint groups.
        joint_group = model.behavior.joint_groups[index]
        solver_name = solver.name

        # Get the unique driver joint names using the raw control names i.e. my_joint.qx becomes my_joint
        driver_joint_names: Set[str] = set()
        for raw_control_index in solver.raw_control_indices:
            driver_joint_names.add(model.definition.raw_control_names[raw_control_index].split(".")[0])

        # The default pose is shared across every solver.
        pose_data: Dict[str, Any] = {
            "default": {
                "drivers": [],
                "controllers": [],
                "driven": {},
                "function_type": "DefaultFunctionType",
                "scale_factor": 1.0,
                "distance_method": "DefaultMethod",
                "target_enable": True,
                "blendshape_data": [],
            }
        }

        # Iterate over the pose indices
        for pose_index in solver.pose_indices:
            # Get the relative pose index to calculate which pose this maps to in the rbf behavior layer
            dna_pose = model.rbf_behavior.poses[pose_index]
            # Generate placeholder data for the pose
            pose_data[dna_pose.name] = {
                "drivers": [],
                "controllers": [],
                "driven": {},
                "function_type": "DefaultFunctionType",
                "scale_factor": dna_pose.scale,
                "distance_method": "DefaultMethod",
                "target_enable": True,
                "blendshape_data": [],
            }

        # Driver raw control data is stored in chunks, one driver after another per pose before moving to the next.
        # I.e.
        # default_pose | driver_0.qx | driver_0.qy | driver_0.qz | driver_0.qw | driver_1.qx | driver_1.qy | driver_1.qz | driver_1.qw |
        # up_pose      | driver_0.qx | driver_0.qy | driver_0.qz | driver_0.qw | driver_1.qx | driver_1.qy | driver_1.qz | driver_1.qw |
        # With this in mind, the raw control offset is the number of channels used for an individual driver * the number
        # of drivers. As quaternions are the only raw control type supported, the number of channels is 4.
        driver_raw_control_offset = (len(driver_joint_names) - 1) * 4
        for i in range(len(driver_joint_names)):
            # Set the start index to be offset depending on the number of driver joints
            raw_control_index = i * 4
            for pose_index in solver.pose_indices:
                dna_pose = model.rbf_behavior.poses[pose_index]

                # Get the raw control values for the driver
                raw_driver_pose_rotation_quat = solver.raw_control_values[raw_control_index : raw_control_index + 4]
                driver_pose_rotation_quat = (
                    raw_driver_pose_rotation_quat[0],
                    raw_driver_pose_rotation_quat[1],
                    raw_driver_pose_rotation_quat[2],
                    raw_driver_pose_rotation_quat[3],
                )

                # Generate a matrix. Translation / scale are ignored as they can't be used as raw controls
                pose_data[dna_pose.name]["drivers"].append(
                    utils.compose_matrix(
                        (0.0, 0.0, 0.0), utils.quaternion_to_euler(driver_pose_rotation_quat), (1.0, 1.0, 1.0)
                    )
                )
                # Offset the raw control index to find the next pose start for this driver
                raw_control_index = raw_control_index + 4 + driver_raw_control_offset

        pose_count = len(solver.pose_indices) - 1
        # Driven data is stored differently to driver, instead grouped per channel instead of per pose i.e.
        # my_joint.translation.x | pose_1 | pose_2 | pose_3 |
        # my_joint.translation.y | pose_1 | pose_2 | pose_3 |
        # my_joint.translation.z | pose_1 | pose_2 | pose_3 |
        # Offset needed to move to the next joint (number of poses x number of channels - TRS XYZ)
        joint_data_offset = pose_count * 9
        joint_data_start_index = 0
        # Set the initial end index for the row to the joint data offset
        joint_data_end_index = joint_data_offset
        # Store the driven joint names
        driven_joint_names = []
        for joint_index in joint_group.joint_indices:
            # Get the joint channel values for this joint across all channels and poses
            joint_values = joint_group.values[joint_data_start_index:joint_data_end_index]
            # Get the joint name
            joint_name = model.definition.joint_names[joint_index]
            driven_joint_names.append(joint_name)

            # Counter to move between each pose in the values
            pose_offset_index = 0
            # Iterate over the pose indices to find the corresponding rbf pose data
            for pose_index in solver.pose_indices:
                dna_pose = model.rbf_behavior.poses[pose_index]
                # Special case for the default pose
                if pose_index == 0:
                    # Get the neutral transform for the joint
                    driven_transform = neutral_joint_transforms[joint_name]

                    # The default pose cannot contain rotation or scale changes, rotation must be on the joint orient
                    pose_data[dna_pose.name]["driven"][joint_name] = utils.compose_matrix(
                        driven_transform["translate"], (0, 0, 0), (1.0, 1.0, 1.0)
                    )
                    continue

                # Extract each poses values for the joint
                joint_pose_data = joint_values[pose_offset_index::pose_count]
                # Unpack to TRS to compose matrix
                translation = (joint_pose_data[0], joint_pose_data[1], joint_pose_data[2])
                rotation = (joint_pose_data[3], joint_pose_data[4], joint_pose_data[5])
                # convert delta scale to absolute
                scale = (joint_pose_data[6] + 1, joint_pose_data[7] + 1, joint_pose_data[8] + 1)
                # Compose Matrix
                pose_data[dna_pose.name]["driven"][joint_name] = utils.compose_matrix(translation, rotation, scale)
                # Move the pose offset by one column
                pose_offset_index += 1

            # Set the new start and index for the next joint chunk
            joint_data_start_index += joint_data_offset
            joint_data_end_index += joint_data_offset

        # Add the extracted solver data
        serialized_solver_data[solver_name] = {
            "solver_name": solver_name,
            "drivers": list(driver_joint_names),
            "driven_transforms": list(driven_joint_names),
            "controllers": [],
            "poses": pose_data,
            "driven_attrs": [],
            "mode": int(not bool(list(dna_model.RBFSolverType).index(solver.solver_type))),
            "radius": solver.radius,
            "automaticRadius": not bool(list(dna_model.AutomaticRadius).index(solver.automatic_radius)),
            "weightThreshold": solver.weight_threshold,
            "distanceMethod": list(dna_model.RBFDistanceMethod).index(solver.distance_method),
            "normalizeMethod": list(dna_model.RBFNormalizeMethod).index(solver.normalize_method),
            "functionType": list(dna_model.RBFFunctionType).index(solver.function_type),
            "twistAxis": list(dna_model.TwistAxis).index(solver.twist_axis),
            "inputMode": "Rotation",
        }

    return serialized_solver_data


def extract_swing_twist_data(model: dna_model.MHDNAModel) -> Dict[str, Dict[str, Optional[dna_model.Setup]]]:
    """
    Extract the swing and twist data portion from a MHDNAModel. The swing and twist data are stored separately and must
    be mapped into a format that combines both into a single setup to reduce SwingTwistEvaluator nodes.
    Despite the SwingTwistEvaluator node offering a start and end joint, it only uses one to operate. The swing and
    twists do not always share the same driving joint if the twist drives siblings instead of children. This process
    will attempt to map based on the hierarchical similarities where possible.
    """
    swing_twist_setups: Dict[str, Dict[str, Optional[dna_model.Setup]]] = {}
    # Exit early if not present
    if not model.twist_swing:
        return swing_twist_setups

    twist_setups = {}
    # Map the driving joint to the twist setups
    for twist in model.twist_swing.twist:
        for raw_control_index in twist.input_indices:
            joint_name = model.definition.raw_control_names[raw_control_index].split(".")[0]
            twist_setups[joint_name] = twist
            break

    # Map the driving joints to the swing setups
    swing_setups = {}
    for swing in model.twist_swing.swing:
        for raw_control_index in swing.input_indices:
            joint_name = model.definition.raw_control_names[raw_control_index].split(".")[0]
            swing_setups[joint_name] = swing
            break

    for twist_input, twist in twist_setups.items():
        # If the twist driver is also a swing driver, group the two together
        if twist_input in swing_setups:
            swing_twist_setups[twist_input] = {"twist": twist, "swing": swing_setups[twist_input]}
        else:
            # Get the parent hierarchy of the twist input from the dna
            parent_hierarchy = get_dna_parent_hierarchy(twist_input, model)
            # Check if any of the parent joints contain swing setups
            for parent_joint in parent_hierarchy:
                # If a match is found, group them
                if parent_joint in swing_setups:
                    swing_twist_setups[parent_joint] = {"twist": twist, "swing": swing_setups[parent_joint]}
                    break
            else:
                # No match was found, the resulting node will only contain twist
                swing_twist_setups[twist_input] = {"twist": twist, "swing": None}

    # Add any missing swing setups that weren't grouped
    for swing_input, swing in swing_setups.items():
        if swing_input not in swing_twist_setups:
            swing_twist_setups[swing_input] = {"twist": None, "swing": swing}

    return swing_twist_setups


class Serializer(base_serializer.Serializer):
    @classmethod
    def can_process(cls, model: dna_model.MHDNAModel, **kwargs) -> bool:
        """
        Check if the incoming model data is compatible with the version this serializer supports
        """
        if f"{model.version.generation}.{model.version.version}" in ["2.5"]:
            return True

        return False

    @classmethod
    def serialize(
        cls,
        solvers: List[rbf_node.RBFNode],
        export_selected_geometry: bool = False,
        export_geometry: bool = True,
        export_rbf: bool = True,
        export_swing_twist: bool = True,
        solver_data_cache: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> dna_model.MHDNAModel:
        """
        Export the current scene to an MHDNAModel
        """
        # If an existing solver data cache isn't supplied, create one to reduce the number of query calls to the
        # Maya scene
        if not solver_data_cache:
            solver_data_cache = [solver.data(enum_values=False) for solver in solvers]

        # ============================================ Scene Prep ==================================================== #
        # Before export can begin, the skeleton and geometry must be found. Regardless of whether geometry is being
        # exported or not, the association between skeleton and geometry is used to determine the lod settings.
        # The number of lods stored is based on the number of lodded meshes present in the scene and the behavior
        # falloff is determined based on the joints skinned to each lod mesh.
        # Lower lods are always a subset of the higher lods, you cannot have a solver or joint present in lod 1 that
        # does not exist in lod0.
        # For example, if the secondary joints used by an RBF solver for the upper arm were present in the lod1 mesh,
        # the export process would include that solver in lod1.

        # Find root joint
        root_joint = None

        # Try to get the root joint from the rbf solvers
        for solver in solver_data_cache:
            for joint in solver["drivers"]:
                new_root_joint = get_root_joint(joint)
                if new_root_joint:
                    root_joint = new_root_joint
                    break

            if root_joint:
                break

        # If the root joint could not be found from the rbf solvers, attempt to find it from the swing twist nodes
        if not root_joint:
            for node in cmds.ls(type="SwingTwistEvaluatorNode"):
                start_joints = cmds.listConnections(f"{node}.startJoint", skipConversionNodes=True) or []
                end_joints = cmds.listConnections(f"{node}.endJoint", skipConversionNodes=True) or []
                if start_joints:
                    for joint in start_joints:
                        new_root_joint = get_root_joint(joint)
                        if new_root_joint:
                            root_joint = new_root_joint
                            break

                if not root_joint and end_joints:
                    for joint in end_joints:
                        new_root_joint = get_root_joint(joint)
                        if new_root_joint:
                            root_joint = new_root_joint
                            break

                if root_joint:
                    break

        # If the root joint still can't be found, last resort to grab joints from the scene. This is unreliable and
        # should be avoided where possible
        if not root_joint:
            for joint in cmds.ls(selection=True, type="joint"):
                new_root_joint = get_root_joint(joint)
                if new_root_joint:
                    root_joint = new_root_joint
                    break

        # No root, can't export.
        if not root_joint:
            msg = "Unable to find root joint, no joints selected or found in use by RBF/SwingTwist."
            LOG.error(msg)
            raise RuntimeError(msg)

        # Get the joint hierarchy
        joint_hierarchy = [root_joint]
        get_hierarchy(root_joint, joint_hierarchy)

        # Generate a list of potentially non-unique joint names. If this list is fully unique, it can be used to
        # calculate the joint index. If non-unique, export will fail as this names must be unique to work with DNA.
        joint_names = [joint.split("|")[-1] for joint in joint_hierarchy]
        # Find the potential duplicates
        duplicate_names = set([joint_name for joint_name in joint_names if joint_names.count(joint_name) > 1])
        if duplicate_names:
            msg = f"Skeleton contains duplicate names: {duplicate_names}."
            LOG.error(msg)
            raise RuntimeError(msg)

        # Grab the meshes, either from selection or from the scene. Regardless of exporting geometry or not, these are
        # used to determine the lod settings for the skeleton and rbf layers
        if export_selected_geometry:
            mesh_collection = [
                node
                for node in cmds.ls(selection=True, long=True, type="transform")
                if cmds.listRelatives(node, fullPath=True, type="mesh")
            ]
        else:
            mesh_collection = [
                node
                for node in cmds.ls(long=True, type="transform")
                if cmds.listRelatives(node, fullPath=True, type="mesh")
            ]

        # Select the hierarchy in case a group was selected instead of a mesh.
        cmds.select(mesh_collection)
        cmds.select(hierarchy=True)

        # If there is a mesh collection, gather the lod information
        if mesh_collection:
            # Lods can contain multiple meshes, if only one is specified ensure it is a nested list
            if len(mesh_collection) == 1:
                mesh_lods = [mesh_collection]
            else:
                # With more than one mesh, a common group needs to be determined to associate meshes with different lod
                # levels. Group naming cannot be used as a scenes conventions may vary. This method will gather the
                # parents and siblings and group them accordingly. It assumes that at the very least, the structure is
                # geometry_group
                #   lod0
                #       mesh_name
                #   lod1
                #       mesh_name
                # The names of the groups or meshes do not matter, so long as this structure is adhered to.
                # Get the first mesh to start scanning for a common group
                top_shared_node = mesh_collection[0]
                siblings = {}
                for mesh_name in mesh_collection:
                    # Get the parent
                    split_name = mesh_name.split("|")
                    parent = "|".join(split_name[:-1])
                    # Check that the parent hasn't already been scanned
                    if parent and parent not in siblings:
                        # Get the other children of this parent
                        siblings[parent] = [
                            node
                            for node in cmds.listRelatives(parent, children=True, fullPath=True, type="transform")
                            if cmds.listRelatives(node, type="mesh")
                        ]
                    # If no parent is found and a root level group hasn't already been found, add it
                    elif not parent and "" not in siblings:
                        siblings[""] = [
                            node
                            for node in cmds.ls(assemblies=True, long=True)
                            if cmds.listRelatives(node, type="mesh")
                        ]

                    # Iterate backwards over the name's components to generate from the longest first
                    for i in reversed(range(len(split_name))):
                        # Re-construct the long name
                        name = "|".join(split_name[: i + 1])
                        if not name:
                            continue

                        # If the name is in the shared name, override it in case it is shorter and break
                        if name in top_shared_node:
                            top_shared_node = name
                            break
                    # If no part of the name was in the shared node, the lod level can't be determined as they don't
                    # reside under a shared lod group structure
                    else:
                        msg = (
                            f"Unable to determine lod level for {mesh_name}. "
                            f"When multiple meshes are selected each mesh must live under a lod group. "
                            f"i.e. |geometry_grp|lod0{mesh_name}"
                        )
                        LOG.error(msg)
                        raise RuntimeError(msg)

                # Get the full hierarchy of transforms under the top node
                scanned_hierarchy = (
                    cmds.listRelatives(top_shared_node, allDescendents=True, fullPath=True, type="transform") or []
                )
                # Sort the siblings based on their position in the hierarchy
                keys = list(siblings)
                keys.sort(key=lambda x: scanned_hierarchy.index(x))
                mesh_lods = [[] for i in range(len(keys))]

                # Group the meshes by lod index
                for mesh_name in mesh_collection:
                    split_name = mesh_name.split("|")
                    parent = "|".join(split_name[:-1])
                    mesh_lods[keys.index(parent)].append(mesh_name)

            # Generate the lod groups
            lod_groups = []
            for meshes in mesh_lods:
                lod_skeleton = set()
                valid_meshes = []
                for mesh_name in meshes:
                    # Only export skinned meshes
                    mfn_skin_cluster = get_skin_cluster(mesh_name)
                    if not mfn_skin_cluster:
                        continue

                    # Add the mesh name to the list
                    valid_meshes.append(mesh_name.split("|")[-1])
                    # Generate a unique skeleton joint name list for this lod
                    for influence in mfn_skin_cluster.influenceObjects():
                        lod_skeleton.add(influence.partialPathName())
                        for index in range(influence.length() - 1):
                            name = influence.pop().partialPathName()
                            if name in joint_names:
                                lod_skeleton.add(name)

                # Add the lod group
                valid_skeleton = list(lod_skeleton)
                lod_groups.append(
                    LodGroup(
                        geometry=valid_meshes,
                        joints=valid_skeleton,
                        solvers=[
                            solver["solver_name"].split(":")[-1]
                            for solver in solver_data_cache
                            if any([joint in valid_skeleton for joint in solver["driven_transforms"]])
                        ],
                    )
                )

        # Without a mesh collection, there can only be one lod.
        else:
            lod_groups = [
                LodGroup(
                    joints=joint_names,
                    solvers=[
                        solver["solver_name"].split(":")[-1]
                        for solver in solver_data_cache
                        if any([joint in joint_names for joint in solver["driven_transforms"]])
                    ],
                )
            ]

        missing_joints = []
        for lod_group in lod_groups:
            for joint in lod_group.joints:
                if joint not in joint_names:
                    missing_joints.append(joint)

        if missing_joints:
            msg = f"Missing joints from skeleton hierarchy. Driver skeletons are not supported by DNA. \n{list(set(missing_joints))}"
            LOG.error(msg)
            raise RuntimeError(msg)

        # ============================================ DNA Model ===================================================== #
        # Generate the coordinate system based on the current scene up axis
        coordinate_system = dna_model.CoorSystem.create_maya_yup_coordinate_system()
        if cmds.upAxis(query=True, axis=True) == "z":
            coordinate_system = dna_model.CoorSystem.create_maya_zup_coordinate_system()

        mh_dna_model = dna_model.MHDNAModel()

        # ============================================ Descriptor ==================================================== #
        # Ensure the dna file knows which co-ordinate space Maya is using so that it can be correctly converted if
        # necessary
        lod_count = len(lod_groups)
        mh_dna_model.descriptor = dna_model.Descriptor(coordinate_system=coordinate_system)
        mh_dna_model.descriptor.lod_count = lod_count
        mh_dna_model.descriptor.db_name = f"MHB.{0 if len(lod_groups) == 1 else 1}"

        # ============================================ Definition ==================================================== #
        definition = dna_model.Definition()

        definition.joint_names = [joint_name.split(":")[-1] for joint_name in joint_names]
        # Placeholders for animated maps and bs
        definition.lod_animated_maps_mapping = dna_model.Mapping(
            lods=list(range(lod_count)), indices=[[] for _ in range(lod_count)]
        )
        definition.lod_blend_shape_mapping = dna_model.Mapping(
            lods=list(range(lod_count)), indices=[[] for _ in range(lod_count)]
        )
        mh_dna_model.definition = definition

        # The default joint representations are fine
        mh_dna_model.joint_metadata = dna_model.JointMetadata(
            [dna_model.JointRepresentation() for joint in joint_hierarchy]
        )

        joint_hierarchy_indices = []
        neutral_joint_translations: Dict[str, List[float]] = {"xs": [], "ys": [], "zs": []}
        neutral_joint_rotations: Dict[str, List[float]] = {"xs": [], "ys": [], "zs": []}

        keys = ["xs", "ys", "zs"]
        # Generate the neutral joint transform data
        for joint in joint_hierarchy:
            parent_joint: List[str] = cast(List, cmds.listRelatives(joint, parent=True, type="joint")) or []
            if parent_joint:
                joint_hierarchy_indices.append(joint_hierarchy.index(parent_joint[0]))
            else:
                joint_hierarchy_indices.append(0)

            # existing_rotation = cmds.xform(joint, query=True, rotation=True)
            translation = cmds.xform(joint, query=True, translation=True)
            rotation = cmds.getAttr(f"{joint}.jointOrient")[0]
            for i in range(3):
                neutral_joint_translations[keys[i]].append(translation[i])
                neutral_joint_rotations[keys[i]].append(rotation[i])

        definition.joint_hierarchy = joint_hierarchy_indices

        # Generate the joint lod mapping to match
        lod_joint_mapping = dna_model.Mapping()
        for index, lod_group in enumerate(lod_groups):
            lod_joint_mapping.lods.append(index)
            joint_indices = [joint_names.index(joint) for joint in lod_group.joints]
            joint_indices.sort()
            lod_joint_mapping.indices.append(joint_indices)

        definition.lod_joint_mapping = lod_joint_mapping

        definition.neutral_joint_translations = neutral_joint_translations
        definition.neutral_joint_rotations = neutral_joint_rotations

        raw_controls = []
        driver_control_map = {}
        # If exporting rbf, get the raw controls from the solver drivers
        if export_rbf:
            for solver in solver_data_cache:
                for driver in solver["drivers"]:
                    # Ensure raw controls aren't duplicated
                    if driver in driver_control_map:
                        continue

                    driver_control_map[driver] = [f"{driver}.qx", f"{driver}.qy", f"{driver}.qz", f"{driver}.qw"]
                    raw_controls.extend(driver_control_map[driver])

        if export_swing_twist:
            # Need to ensure that raw controls are also captured for the swing twist joints
            swing_twist_nodes = cmds.ls(type="SwingTwistEvaluatorNode")
            if swing_twist_nodes:
                for node in cmds.ls(type="SwingTwistEvaluatorNode"):
                    start_joints = cmds.listConnections(f"{node}.startJoint", skipConversionNodes=True) or []
                    end_joints = cmds.listConnections(f"{node}.endJoint", skipConversionNodes=True) or []

                    if start_joints and start_joints[0] not in driver_control_map:
                        driver_control_map[start_joints[0]] = [
                            f"{start_joints[0]}.qx",
                            f"{start_joints[0]}.qy",
                            f"{start_joints[0]}.qz",
                            f"{start_joints[0]}.qw",
                        ]
                        raw_controls.extend(driver_control_map[start_joints[0]])

                    if end_joints and end_joints[0] not in driver_control_map:
                        driver_control_map[end_joints[0]] = [
                            f"{end_joints[0]}.qx",
                            f"{end_joints[0]}.qy",
                            f"{end_joints[0]}.qz",
                            f"{end_joints[0]}.qw",
                        ]
                        raw_controls.extend(driver_control_map[end_joints[0]])

        # Strip any namespaces from the raw control names
        definition.raw_control_names = [raw_control.split(":")[-1] for raw_control in raw_controls]

        # ============================================ RBF Layer ==================================================== #
        if export_rbf and solver_data_cache:
            # The start index for rbf poses is the total number of Raw controls + PSD controls + ML controls
            pose_index_start = len(raw_controls)
            # RBF is split into multiple layers, Behavior, RBFBehavior and RBFExtension
            rbf_behavior = dna_model.RBFBehavior()

            rbf_extension = dna_model.RBFExtension()

            # Behavior layer is also needed
            behavior = dna_model.Behavior()

            pose_names = ["default"]
            poses: List[dna_model.Pose] = [dna_model.Pose("default")]
            rbf_poses: List[dna_model.RBFPose] = [dna_model.RBFPose([], [pose_index_start], [1])]
            joint_groups: List[dna_model.JointGroup] = []
            rbf_solvers: List[dna_model.Solver] = []
            # Generate the solver lod mapping based on the lod groups
            solver_lods = dna_model.Mapping(
                lods=[i for i in range(len(lod_groups))], indices=[[] for i in range(len(lod_groups))]
            )

            for solver in solver_data_cache:
                # Joint group data stores the TRS data for the driven joints, Solvers store the parameters and the
                # driver (raw control) quaternion values. Not all features supported by UERBFSolver nodes are supported
                # by RigLogic, anything that isn't compatible will raise an error.
                joint_group = dna_model.JointGroup()
                joint_groups.append(joint_group)
                rbf_solver = dna_model.Solver()
                rbf_solver.name = solver["solver_name"].split(":")[-1]
                rbf_solver.solver_type = dna_model.RBFSolverType(solver["mode"])
                rbf_solver.radius = solver["radius"]
                rbf_solver.weight_threshold = solver["weightThreshold"]
                rbf_solver.automatic_radius = dna_model.AutomaticRadius(not solver["automaticRadius"])
                rbf_solver.distance_method = dna_model.RBFDistanceMethod(solver["distanceMethod"])
                normalize_method = solver["normalizeMethod"]
                if normalize_method > 1:
                    raise RuntimeError(
                        f"Error in solver {solver['solver_name']} - Normalize method `NoNormalization` not supported by RigLogic"
                    )

                if solver["inputMode"] != 1:
                    raise RuntimeError(
                        f"Error in solver {solver['solver_name']} - Input mode `Translation` not supported by RigLogic"
                    )

                rbf_solver.normalize_method = dna_model.RBFNormalizeMethod(normalize_method)
                rbf_solver.function_type = dna_model.RBFFunctionType(solver["functionType"])
                rbf_solver.twist_axis = dna_model.TwistAxis(solver["twistAxis"])
                rbf_solver_index = len(rbf_solvers)
                rbf_solvers.append(rbf_solver)

                joint_group.joint_indices = [joint_hierarchy.index(driven) for driven in solver["driven_transforms"]]

                output_indices = []
                # Generate the output indices, these are the TRS channels (9 in total) for each joint
                for joint_index in joint_group.joint_indices:
                    start = joint_index * 9
                    output_indices.extend([i for i in range(start, start + 9)])

                joint_group.output_indices = output_indices

                # Values are stored in a list starting with the tx for one joint and each pose followed by ty, tz etc
                raw_control_values: List[float] = []
                pose_indices = []
                input_indices = []
                # Prepopulate the pose data
                ordered_pose_data: List[List[float]] = [[] for driven in range(len(solver["driven_transforms"]) * 9)]
                # Lists to store the default driver and driven matrices so deltas can be calculated
                default_pose_driven_matrices = []
                default_pose_driver_matrices = []
                for index, (pose_name, pose_data) in enumerate(solver["poses"].items()):
                    # Default is always the first pose index
                    if pose_name == "default":
                        pose_indices.append(0)
                        default_pose_driven_matrices = pose_data["driven"]
                        default_pose_driver_matrices = pose_data["drivers"]
                        # Rotation is always 0 for the raw control values on the default pose. The rotations stored
                        # in the neutral rotations are from the joint orient
                        raw_control_values.extend((0.0, 0.0, 0.0, 1.0))
                        continue

                    poses.append(dna_model.Pose(pose_name))
                    pose_names.append(pose_name)
                    pose_index = len(pose_names) - 1
                    pose_indices.append(pose_index)
                    input_indices.append(pose_index_start + pose_index)
                    rbf_poses.append(dna_model.RBFPose([], [pose_index_start + pose_index], [1]))
                    # Iterate over the drivers, store the delta quaternion values as raw control values
                    for driver_index, driver in enumerate(pose_data["drivers"]):
                        default_driver = om.MMatrix(default_pose_driver_matrices[driver_index])
                        driver_transform = om.MMatrix(driver)
                        delta_matrix = list(driver_transform * default_driver.inverse())
                        translation, rotation, scale = utils.decompose_matrix(delta_matrix)
                        raw_control_values.extend(utils.euler_to_quaternion(rotation))

                    for driven_index, (driven_name, matrix) in enumerate(pose_data["driven"].items()):
                        start_index = driven_index * 9
                        default_driven = om.MMatrix(default_pose_driven_matrices[driven_name])
                        driven_transform = om.MMatrix(matrix)
                        # Calculate the delta matrix
                        delta_matrix = list(driven_transform * default_driven.inverse())
                        translation, rotation, scale = utils.decompose_matrix(delta_matrix)
                        scale = (scale[0] - 1.0, scale[1] - 1.0, scale[2] - 1.0)
                        column = translation + rotation + scale
                        for column_index, i in enumerate(range(start_index, start_index + 9)):
                            ordered_pose_data[i].append(column[column_index])

                unpacked_pose_data: List[float] = []
                for sorted_pose_data in ordered_pose_data:
                    unpacked_pose_data.extend(sorted_pose_data)

                output_count = len(joint_group.output_indices)
                # Calculate the joint groups lods if the solver is each lod group
                joint_group_lods = []
                for lod_index, lod_group in enumerate(lod_groups):
                    if rbf_solver.name in lod_group.solvers:
                        joint_group_lods.append(output_count)
                        solver_lods.indices[lod_index].append(rbf_solver_index)
                    else:
                        joint_group_lods.append(0)

                joint_group.lods = joint_group_lods
                joint_group.input_indices = input_indices
                joint_group.values = unpacked_pose_data
                rbf_solver.pose_indices = pose_indices
                rbf_solver.raw_control_values = raw_control_values
                raw_control_indices = []
                for driver in solver["drivers"]:
                    raw_control_indices.extend([raw_controls.index(control) for control in driver_control_map[driver]])
                rbf_solver.raw_control_indices = raw_control_indices

            behavior.joint_groups = joint_groups
            behavior.row_count = 9 * len(joint_names)
            # Order must be Raw controls + PSD controls + ML controls + RBF Poses
            behavior.col_count = pose_index_start + len(pose_names) - 1
            mh_dna_model.behavior = behavior

            rbf_behavior.solvers = rbf_solvers
            rbf_behavior.poses = poses
            rbf_behavior.lod_solver_mapping = solver_lods
            mh_dna_model.rbf_behavior = rbf_behavior

            rbf_extension.pose_control_names = pose_names
            rbf_extension.poses = rbf_poses
            mh_dna_model.rbf_extension = rbf_extension

        # ======================================== Swing / Twist Layer =============================================== #
        if export_swing_twist:
            twist_swing = dna_model.TwistSwing()
            twists: List[dna_model.Setup] = []
            swings: List[dna_model.Setup] = []
            swing_twist_nodes = cmds.ls(type="SwingTwistEvaluatorNode")
            if swing_twist_nodes:
                for node in cmds.ls(type="SwingTwistEvaluatorNode"):
                    start_attr = "startJoint"
                    end_attr = "endJoint"
                    twist_attr = start_attr
                    if cmds.getAttr(f"{node}.fromEnd"):
                        twist_attr = end_attr
                    twist_inputs = cmds.listConnections(f"{node}.{twist_attr}", skipConversionNodes=True) or []
                    swing_inputs = cmds.listConnections(f"{node}.{start_attr}", skipConversionNodes=True) or []
                    # Separate out the twist and swings into separate setups
                    if twist_inputs:
                        twist_outputs = cmds.listConnections(f"{node}.twists", skipConversionNodes=True) or []
                        if twist_outputs:
                            twist_blends = [
                                cmds.getAttr(f"{node}.twistBlend[{index}]")[0][0]
                                for index in cmds.getAttr(f"{node}.twistBlend", multiIndices=True)
                            ]

                            # Add the twist setup
                            twists.append(
                                dna_model.Setup(
                                    [raw_controls.index(control) for control in driver_control_map[twist_inputs[0]]],
                                    [joint_names.index(joint) for joint in twist_outputs],
                                    twist_blends,
                                )
                            )

                    if swing_inputs:
                        swing_outputs = cmds.listConnections(f"{node}.swing", skipConversionNodes=True) or []
                        if swing_outputs:
                            swing_blend = [cmds.getAttr(f"{node}.swingBlend")]

                            swings.append(
                                dna_model.Setup(
                                    [raw_controls.index(control) for control in driver_control_map[swing_inputs[0]]],
                                    [joint_names.index(joint) for joint in swing_outputs],
                                    swing_blend,
                                )
                            )

            twist_swing.twist = twists
            twist_swing.swing = swings

            mh_dna_model.twist_swing = twist_swing

        # ========================================== Geometry Layer ================================================== #
        if export_geometry:
            lod_mesh_mapping = dna_model.Mapping()
            mesh_geometry: List[dna_model.MeshGeometry] = []
            mesh_names = []
            for index, lod_group in enumerate(lod_groups):
                lod_mesh_mapping.lods.append(index)
                mesh_indices = []
                for mesh_name in lod_group.geometry:
                    # Strip any namespaces out of the name
                    mesh_names.append(mesh_name.split(":")[-1])
                    mesh_index = len(mesh_names) - 1
                    mesh_indices.append(mesh_index)

                    mesh_geo = dna_model.MeshGeometry()
                    # Convert the mesh string over to an MFnMesh
                    sel = om.MSelectionList()
                    sel.add(mesh_name)
                    mesh_dag_path = sel.getDagPath(0)
                    mfn_mesh = om.MFnMesh(mesh_dag_path)
                    # Get the vertices in world space
                    vertex_points = mfn_mesh.getPoints(om.MSpace.kWorld)
                    face_vertex_count, vertex_indices = mfn_mesh.getVertices()

                    face_indices = []
                    start_index = 0
                    # Generate a nested list of vertex indices that make up each face
                    for unique_count in face_vertex_count:
                        end_index = start_index + unique_count
                        face_indices.append(list(vertex_indices[start_index:end_index]))
                        start_index = end_index

                    # Get normals and UVs
                    normals = mfn_mesh.getVertexNormals(True, om.MSpace.kObject)
                    uvs = mfn_mesh.getUVs()

                    # Generate the vertex position list
                    positions = [list(vertex_point)[:3] for vertex_point in vertex_points]
                    # Reformat the UV layout
                    texture_coordinates = [[uvs[0][index], uvs[1][index]] for index in range(len(uvs[0]))]
                    # Reformat the normals
                    vertex_normals = [list(normal) for normal in normals]
                    # Vertex layouts are what describe the relationship between a vertex position index, UV index and
                    # normal index.
                    vertex_layouts = []
                    face_vertex_layouts = []
                    seen: Dict[Tuple[float, float, float], int] = {}
                    unique_count = 0
                    for face_index, face_vertices in enumerate(face_indices):
                        face_vertex_layout = []
                        for face_vertex_index, vertex_index in enumerate(face_vertices):
                            vertex_layout = (
                                vertex_index,
                                mfn_mesh.getPolygonUVid(face_index, face_vertex_index),
                                vertex_index,
                            )
                            # If the vertex layout has already been seen before, add a pointer to the existing layout.
                            if vertex_layout in seen:
                                face_vertex_layout.append(seen[vertex_layout])
                            else:
                                seen[vertex_layout] = unique_count
                                face_vertex_layout.append(unique_count)
                                vertex_layouts.append(list(vertex_layout))
                                unique_count += 1

                        face_vertex_layouts.append(face_vertex_layout)

                    mfn_skin_cluster = get_skin_cluster(mesh_name)

                    if not mfn_skin_cluster:
                        continue

                    # Extract the skinning
                    mfn_single_indexed_comp = om.MFnSingleIndexedComponent()
                    vertex_components = mfn_single_indexed_comp.create(om.MFn.kMeshVertComponent)
                    mfn_single_indexed_comp.addElements(range(mfn_mesh.numVertices))

                    weights, influence_count = mfn_skin_cluster.getWeights(mesh_dag_path, vertex_components)
                    influences = [
                        joint_names.index(dag.partialPathName()) for dag in mfn_skin_cluster.influenceObjects()
                    ]

                    influence_index = 0
                    vertex_index = 0
                    skin_weights = [dna_model.SkinWeight() for i in range(mfn_mesh.numVertices)]
                    max_influence_count = [0 for i in range(mfn_mesh.numVertices)]
                    for weight in weights:
                        if influence_index > influence_count - 1:
                            influence_index = 0
                            vertex_index += 1

                        # Ignore weights below a threshold
                        if weight > 0.0001:
                            skin_weight = skin_weights[vertex_index]
                            max_influence_count[vertex_index] += 1
                            skin_weight.values.append(weight)
                            skin_weight.joint_indices.append(influences[influence_index])

                        influence_index += 1

                    # Calculate the max influence count based on the highest number of influences for any vertex
                    max_influence_count.sort(reverse=True)
                    if not max_influence_count:
                        max_influence_count = [16]

                    mesh_geo.positions = positions
                    mesh_geo.texture_coordinates = texture_coordinates
                    mesh_geo.normals = vertex_normals
                    mesh_geo.layouts = vertex_layouts
                    mesh_geo.faces = face_vertex_layouts
                    mesh_geo.maximum_influence_per_vertex = max_influence_count[0]
                    mesh_geo.skin_weights = skin_weights
                    mesh_geometry.append(mesh_geo)

                lod_mesh_mapping.indices.append(mesh_indices)

            definition.lod_mesh_mapping = lod_mesh_mapping
            definition.mesh_names = mesh_names

            mh_dna_model.geometry = dna_model.Geometry(mesh_geometry)

        return mh_dna_model

    @classmethod
    def deserialize(
        cls,
        model: dna_model.MHDNAModel,
        unpack_rbf: bool = True,
        unpack_swing_twist: bool = True,
        solver_names: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        cmds.loadPlugin("SwingTwistEvaluatorPlugin")
        if unpack_rbf:
            absolute_solver_data = {}
            # Take the delta solver data from the model and calculate the absolute values based on the data in the scene
            for solver_name, solver_data in extract_solver_data(model).items():
                # Validate that the correct joints exist in the scene to generate this solver
                expected_drivers = cast(List, solver_data["drivers"])
                expected_driven = cast(List, solver_data["driven_transforms"])

                actual_drivers = [d for d in expected_drivers if cmds.ls(d, type="joint")]
                actual_driven = [d for d in expected_driven if cmds.ls(d, type="joint")]

                missing_joints = False
                if len(actual_drivers) != len(expected_drivers):
                    LOG.warning(f"Missing drivers: {set(expected_drivers) - set(actual_drivers)}")
                    missing_joints = True

                if len(actual_driven) != len(expected_driven):
                    LOG.warning(f"Missing driven: {set(expected_driven) - set(actual_driven)}")
                    missing_joints = True

                if missing_joints:
                    continue

                # Get the current drivers matrices from its current object space position as an MMatrix for ease of use
                current_drivers = [
                    om.MMatrix(cmds.xform(d, query=True, matrix=True, objectSpace=True)) for d in expected_drivers
                ]

                current_driven_transforms = {
                    d: om.MMatrix(utils.get_local_matrix_without_joint_orient(d)) for d in expected_driven
                }

                poses = solver_data["poses"]
                new_pose_data = {}

                for pose_index, (pose_name, pose_data) in enumerate(poses.items()):
                    # If this is the first pose, it is treated as the rest pose and the driver matrices should be set
                    # to their current value from the scene
                    if pose_index == 0:
                        pose_data["drivers"] = [list(d) for d in current_drivers]
                        pose_data["driven"] = {d: list(m) for d, m in current_driven_transforms.items()}
                    else:
                        # If it isn't the first pose, the new matrix must be calculated by taking the delta stored in
                        # the file and adding it to the rest pose value. This needs to be done for each driver
                        new_drivers = []
                        drivers = copy.deepcopy(pose_data["drivers"])
                        for index, driver in enumerate(drivers):
                            default_driver = current_drivers[index]
                            driver = om.MMatrix(driver)
                            new_drivers.append(list(driver * default_driver))
                        # Update the driver data
                        pose_data["drivers"] = new_drivers

                        new_driven = {}
                        driven_transforms = copy.deepcopy(pose_data["driven"])

                        for name, driven_transform in driven_transforms.items():
                            default_driven = current_driven_transforms[name]
                            driven_transform = om.MMatrix(driven_transform)
                            new_driven[name] = list(driven_transform * default_driven)

                        pose_data["driven"] = new_driven

                    # Update the solver pose data
                    new_pose_data[pose_name] = pose_data

                # Set the pose data for the solver
                solver_data["poses"] = new_pose_data
                # Set the new solver data
                absolute_solver_data[solver_name] = solver_data

            for solver_name, solver_data in absolute_solver_data.items():
                if solver_names:
                    if solver_name in solver_names:
                        rbf_node.RBFNode.create_from_data(solver_data)
                else:
                    rbf_node.RBFNode.create_from_data(solver_data)

        if unpack_swing_twist:
            # Generate the swing twist nodes
            for joint_input, swing_twist_setup in extract_swing_twist_data(model).items():
                start_joint = joint_input
                end_joint = None
                swing_joint = None
                twist_joints = []
                twist_blends = []
                swing_blend = 0.5
                from_end = False
                swing_setup: Optional[dna_model.Setup] = swing_twist_setup["swing"]
                twist_setup: Optional[dna_model.Setup] = swing_twist_setup["twist"]
                # If both setups are present, determine if from_end is needed
                if twist_setup and swing_setup:
                    if twist_setup.input_indices != swing_setup.input_indices:
                        for raw_control_index in swing_setup.input_indices:
                            start_joint = model.definition.raw_control_names[raw_control_index].split(".")[0]
                            break
                        for raw_control_index in twist_setup.input_indices:
                            end_joint = model.definition.raw_control_names[raw_control_index].split(".")[0]
                            break
                        from_end = True

                if twist_setup:
                    twist_joints = [
                        model.definition.joint_names[joint_index] for joint_index in twist_setup.output_indices
                    ]
                    twist_blends = twist_setup.weights

                if swing_setup:
                    swing_blend = swing_setup.weights[0]
                    swing_joints = [
                        model.definition.joint_names[joint_index] for joint_index in swing_setup.output_indices
                    ]
                    if swing_joints:
                        swing_joint = swing_joints[0]

                for joint in [joint_input, start_joint, end_joint, swing_joint, *twist_joints]:
                    if joint is not None and not cmds.ls(joint, type="joint"):
                        break
                else:
                    # Generate the node
                    create_swing_twist_evaluator(
                        joint_input,
                        start_joint=start_joint,
                        end_joint=end_joint,
                        swing_joint=swing_joint,
                        swing_blend=swing_blend,
                        twist_joints=twist_joints,
                        twist_blends=twist_blends,
                        from_end=from_end,
                    )
