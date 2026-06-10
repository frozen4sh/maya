# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import re
import math
from typing import TYPE_CHECKING, Any, Dict, List, Union, Optional, cast
from collections import OrderedDict

# External
from maya import OpenMaya, cmds
from maya.api import OpenMaya as om

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import exceptions, pose_blender

if TYPE_CHECKING:
    from mh_pose_editor.model import mirror_mapping


class RBFNode:
    node_type = "UERBFSolverNode"

    def __init__(self, node: str) -> None:
        """
        Initialize RBFNode on give node

        >>> node = cmds.createNode('UERBFSolverNode')
        >>> RBFNode(node)
        """

        if not cmds.objectType(node, isAType=self.node_type):
            raise TypeError(f'Invalid "{self.node_type}" node: "{node}"')

        self._node = node

    def __repr__(self) -> str:
        """
        Returns class string representation
        """
        return f"<{self.node_type}>: {self}"

    def __str__(self) -> str:
        """
        Returns class as string
        """
        return str(self._node)

    def __eq__(self, other) -> bool:
        """
        Overrides equals operator to allow for different RBFNode instances to be matched against each other
        """
        return str(self) == str(other)

    def set_defaults(self) -> None:
        """
        Sets node default values
        """
        self.set_mode("Interpolative")
        self.set_radius(45)
        self.set_automatic_radius(False)

    # -------------------------------------------------------------------------

    @classmethod
    def create(cls, name: Optional[str] = None) -> "RBFNode":
        """
        Create RBF node

        >>> new_node = RBFNode.create()
        """

        if name is None:
            name = f"{cls.node_type}#"
        active_selection = cmds.ls(selection=True)
        # create node
        node = cmds.createNode(cls.node_type, name=name)
        rbf_node = cls(node)
        rbf_node.set_defaults()
        cmds.select(active_selection, replace=True)

        return rbf_node

    @classmethod
    def create_from_data(cls, data: Dict[str, Any]) -> "RBFNode":
        """
        Creates RBF network from dictionary

        >>> new_joint = cmds.createNode('joint')
        >>> data = {'drivers': [new_joint], 'poses': {'drivers': {'default': [[1,0,0,0,0,1,0,0,0,0,1,0,2,0,0,1]]}}}
        >>> RBFNode.create_from_data(data)
        """

        if not cmds.objExists(data["solver_name"]):
            rbf_node = cls.create(name=data["solver_name"])
        else:
            rbf_node = cls(data["solver_name"])

        # add drivers
        drivers = data["drivers"]
        for driver in drivers:
            if not rbf_node.has_driver(driver):
                rbf_node.add_driver(driver)

        driven_transforms = data.get("driven_transforms", [])
        if driven_transforms:
            rbf_node.add_driven_joints(joint_names=driven_transforms, edit=False)

        # add poses
        for pose_name, pose_data in data["poses"].items():
            drivers_matrices = pose_data["drivers"]
            driven_matrices = pose_data.get("driven", {})
            # function_type = pose_data.get("function_type", "DefaultFunctionType")
            # distance_method = pose_data.get("distance_method", "DefaultMethod")
            # scale_factor = pose_data.get("scale_factor", 1.0)
            target_enable = pose_data.get("target_enable", True)

            rbf_node.add_pose(
                pose_name,
                drivers=drivers,
                matrices=drivers_matrices,
                driven_matrices=driven_matrices,
                target_enable=target_enable,
            )

        # set solver attributes
        attributes = ["radius", "automaticRadius", "weightThreshold"]
        enum_attributes = ["mode", "distanceMethod", "normalizeMethod", "functionType", "twistAxis", "inputMode"]

        for attr in attributes:
            if attr in data:
                cmds.setAttr(f"{rbf_node}.{attr}", data[attr])

        for attr in enum_attributes:
            if attr in data:
                value = data[attr]
                attr = f"{rbf_node}.{attr}"
                rbf_node._set_enum_attribute(attr, value)

        return rbf_node

    @classmethod
    def find_all(cls) -> List["RBFNode"]:
        """
        Returns all RBF nodes in scene
        """
        return [cls(node) for node in cmds.ls(type=cls.node_type)]

    # ----------------------------------------------------------------------------------------------
    #                                       PARAMETERS
    # ----------------------------------------------------------------------------------------------

    def mode(self, enum_value: bool = True) -> Union[str, int]:
        return cast(Union[str, int], cmds.getAttr(f"{self}.mode", asString=enum_value))

    def set_mode(self, value: Union[str, int]) -> None:
        self._set_enum_attribute(f"{self}.mode", value)

    def radius(self) -> float:
        return cast(float, cmds.getAttr(f"{self}.radius"))

    def set_radius(self, value: float) -> None:
        cmds.setAttr(f"{self}.radius", value)

    def automatic_radius(self) -> bool:
        return cast(bool, cmds.getAttr(f"{self}.automaticRadius"))

    def set_automatic_radius(self, value: bool) -> None:
        cmds.setAttr(f"{self}.automaticRadius", value)

    def weight_threshold(self) -> float:
        return cast(float, cmds.getAttr(f"{self}.weightThreshold"))

    def set_weight_threshold(self, value: float) -> None:
        cmds.setAttr(f"{self}.weightThreshold", value)

    def distance_method(self, enum_value: bool = True) -> Union[str, int]:
        return cast(Union[str, int], cmds.getAttr(f"{self}.distanceMethod", asString=enum_value))

    def set_distance_method(self, value: Union[str, int]) -> None:
        self._set_enum_attribute(f"{self}.distanceMethod", value)

    def normalize_method(self, enum_value: bool = True) -> Union[str, int]:
        return cast(Union[str, int], cmds.getAttr(f"{self}.normalizeMethod", asString=enum_value))

    def set_normalize_method(self, value: Union[str, int]) -> None:
        self._set_enum_attribute(f"{self}.normalizeMethod", value)

    def function_type(self, enum_value: bool = True) -> Union[str, int]:
        return cast(Union[str, int], cmds.getAttr(f"{self}.functionType", asString=enum_value))

    def set_function_type(self, value: Union[str, int]) -> None:
        self._set_enum_attribute(f"{self}.functionType", value)

    def twist_axis(self, enum_value: bool = True) -> Union[str, int]:
        return cast(Union[str, int], cmds.getAttr(f"{self}.twistAxis", asString=enum_value))

    def set_twist_axis(self, value: Union[str, int]) -> None:
        self._set_enum_attribute(f"{self}.twistAxis", value)

    def input_mode(self, enum_value: bool = True) -> Union[str, int]:
        return cast(Union[str, int], cmds.getAttr(f"{self}.inputMode", asString=enum_value))

    def set_input_mode(self, value: Union[str, int]) -> None:
        self._set_enum_attribute(f"{self}.inputMode", value)

    def data(self, enum_values: bool = True) -> Dict[str, Any]:
        """
        Returns dictionary with the setup
        """
        data: Dict[str, Any] = OrderedDict()
        data["solver_name"] = str(self)
        data["drivers"] = self.drivers()
        data["driven_transforms"] = self.driven_joints()
        data["poses"] = self.poses()
        data["mode"] = self.mode(enum_value=enum_values)
        data["radius"] = self.radius()
        data["automaticRadius"] = self.automatic_radius()
        data["weightThreshold"] = self.weight_threshold()
        data["distanceMethod"] = self.distance_method(enum_value=enum_values)
        data["normalizeMethod"] = self.normalize_method(enum_value=enum_values)
        data["functionType"] = self.function_type(enum_value=enum_values)
        data["twistAxis"] = self.twist_axis(enum_value=enum_values)
        data["inputMode"] = self.input_mode(enum_value=enum_values)

        return data

    def output_weights(self) -> List[float]:
        """
        Returns output weights
        """
        return [cmds.getAttr(attr) for attr in self.output_attributes()]

    def output_attributes(self) -> List[str]:
        """
        Returns output attributes
        """
        return [
            f"{self}.outputs[{pose_index}]" for pose_index in cmds.getAttr(f"{self}.outputs", multiIndices=True) or []
        ]

    def driven_joints(self) -> List[str]:
        """
        Returns driven transform nodes
        :return:
        """
        driven = []
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            # Iterate through all the pose blenders
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                if pose_blender_node.driven_transform:
                    driven.append(pose_blender_node.driven_transform)

        return driven

    # ----------------------------------------------------------------------------------------------
    #                                           DRIVERS
    # ----------------------------------------------------------------------------------------------

    def num_drivers(self) -> int:
        """
        Returns number of drivers
        """
        return cast(int, cmds.getAttr(f"{self}.inputs", size=True))

    def has_driver(self, joint: str) -> bool:
        """
        Check if node is using this transform as input
        """
        return joint in self.drivers()

    def drivers(self) -> List[str]:
        """
        Returns list of drivers
        """
        indices = cmds.getAttr(f"{self}.inputs", multiIndices=True)
        drivers = list()
        if indices:
            for i in indices:
                connections = cmds.listConnections(f"{self}.inputs[{i}]")
                if connections:
                    drivers.append(connections[0])
                else:
                    raise RuntimeError(f"Unable to get driver at index: {i}")

        return drivers

    def add_driver(self, joint_names: Optional[List[str]] = None) -> None:
        """
        Adds driver to RBF Node
        """
        if joint_names is None:
            joint_names = cmds.ls(selection=True, type="transform")
        if self.num_poses() > 1:
            raise RuntimeError("Unable to add driver after poses have been added")

        if not isinstance(joint_names, (list, set, tuple)):
            joint_names = [joint_names]

        for transform_node in joint_names:
            if not cmds.objExists(transform_node):
                raise RuntimeError(f'Node not found: "{transform_node}"')

            if not cmds.objectType(transform_node, isAType="transform"):
                raise RuntimeError(f'Invalid transform node: "{transform_node}"')

            if self.has_driver(transform_node):
                raise RuntimeError(f'Already has driver "{transform_node}"')

            index = self.num_drivers()
            cmds.connectAttr(f"{transform_node}.matrix", f"{self}.inputs[{index}]")
            # set rest matrix
            rest_matrix = cmds.xform(transform_node, q=True, ws=False, matrix=True)
            cmds.setAttr(f"{self}.inputsRest[{index}]", rest_matrix, type="matrix")

    def remove_drivers(self, joint_names: List[str]) -> None:
        """
        Removes the specified drivers from this solver
        :param joint_names :type list: list of transform node names
        """
        # Get the valid driver names - converts from MObject to DagPath if MObjects are specified
        valid_drivers = []
        for driver in joint_names:
            # Check if its an MObject
            if isinstance(driver, om.MObject):
                # Get the fullPathName and add to list of valid drivers
                valid_drivers.append(om.MDagPath.getAPathTo(driver).fullPathName())
            else:
                # Check if the driver exists and get the full path name
                matching_driver = cmds.ls(driver, long=True)
                if matching_driver:
                    # Add to list of valid drivers
                    valid_drivers.append(matching_driver[0])

        LOG.debug(f"Removing drivers: '{valid_drivers}' from solver: {self}")
        # Get the existing drivers from the solver
        existing_drivers = self.drivers()
        # Create an empty dict to store the remaining {driver: pose_node}
        remaining_drivers = []
        poses_indices = cmds.getAttr(f"{self}.targets", multiIndices=True) or []
        # Iterate through the existing drivers in reverse
        for index in reversed(range(len(existing_drivers))):
            # Grab the driver from the index
            existing_driver = existing_drivers[index]
            # Check that the driver exists
            matching_driver = cmds.ls(existing_driver, long=True)
            # If the driver doesn't exist, warn and continue
            if not matching_driver:
                LOG.warning(f"Could not find driver: {existing_driver} in the scene")
                continue
            # Existing driver found
            existing_driver = matching_driver[0]
            # Remove the drivers connections from the solver
            cmds.removeMultiInstance(f"{self}.inputs[{index}]", b=True)
            cmds.removeMultiInstance(f"{self}.inputsRest[{index}]", b=True)
            for pose_index in poses_indices:
                cmds.removeMultiInstance(f"{self}.targets[{pose_index}]", b=True)

            # If the driver is in the not valid drivers list we want to keep it
            if existing_driver not in valid_drivers:
                # Add it back to the list of drivers to reconnect
                remaining_drivers.append(existing_driver)

        # Iterate through the remaining drivers and reconnect them
        for index, driver in enumerate(remaining_drivers):
            cmds.connectAttr(f"{driver}.matrix", f"{self}.inputs[{index}]")
            # set rest matrix
            rest_matrix = cmds.xform(driver, q=True, ws=False, matrix=True)
            cmds.setAttr(f"{self}.inputsRest[{index}]", rest_matrix, type="matrix")

        # If we have any drivers left, recreate the default pose
        if self.drivers():
            self.add_pose_from_current("default")

    # ----------------------------------------------------------------------------------------------
    #                                       DRIVEN TRANSFORMS
    # ----------------------------------------------------------------------------------------------
    def add_driven_joints(self, joint_names: Optional[List[str]] = None, edit: bool = False) -> None:
        """
        Add driven transforms to this node, creating UEPoseBlenderNodes where needed
        :param joint_names :type list: list of transform_node names
        :param edit :type bool: should we be editing the transforms on creation? When set to true, no connection is
        made from the output of the UEPoseBlenderNode to the driven transform translate, rotate and scale. When set
        to False, a decompose matrix is created and connected between the output of the UEPoseBlenderNode and the
        translate, rotate and scale of the driven transform.
        """
        # If no driven nodes are specified, grab the current selection
        if not joint_names:
            joint_names = cmds.ls(selection=True, type="transform")

        if not joint_names:
            return None

        # For each driven node
        for node in joint_names:
            existing_connection = pose_blender.UEPoseBlenderNode.find_by_transform(node)
            if existing_connection:
                LOG.error(
                    f"Driven transform {node} is already connected to {existing_connection.rbf_solver}. "
                    "Unable to add, skipping."
                )
                continue
            # Create a UEPoseBlender node
            pose_blender_node = pose_blender.UEPoseBlenderNode.create(driven_transform=node)
            # Create a message attr connection to the rbf solver node
            pose_blender_node.set_rbf_solver(f"{self}.poseBlenders")
            # Connect each output attribute from the solver to the corresponding weight
            for index, attribute in enumerate(self.output_attributes()):
                pose_blender_node.set_weight(index=index, in_float_attr=attribute)
            # Set the mode to edit
            pose_blender_node.edit = edit

    def remove_driven_joints(self, joint_names: List[str]) -> None:
        """
        Remove the specified driven transforms from this solver
        :param joint_names :type list: list of transform names
        """
        # Can only remove transforms if we have connected UEPoseBlenderNodes
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            # Iterate through the pose blender nodes
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Generate an API wrapper for the UEPoseBlenderNode
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                # If the pose blender's driven transform is in the list to remove
                if pose_blender_node.driven_transform in joint_names:
                    # Remove it from the list
                    joint_names.pop(joint_names.index(pose_blender_node.driven_transform))
                    # Delete the UEPoseBlenderNode
                    pose_blender_node.delete()

    # ----------------------------------------------------------------------------------------------
    #                                           POSES
    # ----------------------------------------------------------------------------------------------

    def num_poses(self) -> int:
        """
        Returns number of poses
        """
        return cast(int, cmds.getAttr(f"{self}.targets", size=True))

    def has_pose(self, pose_name: str) -> bool:
        """
        Returns if pose already exists
        """
        return pose_name in self.poses()

    def pose_index(self, pose_name: str) -> int:
        """
        Returns pose index
        """

        poses_indices: List[int] = cmds.getAttr(f"{self}.targets", multiIndices=True)
        if poses_indices:
            for pose_index in poses_indices:
                if pose_name == cmds.getAttr(f"{self}.targets[{pose_index}].targetName"):
                    return pose_index

        return -1

    def pose(self, pose_name: str) -> Dict[str, Any]:
        """
        Returns a serialized pose
        """

        pose_index = self.pose_index(pose_name)
        if pose_index == -1:
            raise exceptions.InvalidPose(f'Pose not found: "{pose_name}"')

        # ---------------------------------------------------------------------
        num_drivers = self.num_drivers()

        # get driver indices
        driver_indices = cmds.getAttr(f"{self}.targets[{pose_index}].targetValues", multiIndices=True)
        # If the driver indices is None, it is likely due to the transform being aligned with its parent
        if driver_indices is None:
            driver_indices = [i for i in range(num_drivers)]

        # just to be sure ...
        if len(driver_indices) != num_drivers:
            raise exceptions.InvalidPose("Invalid Driver Indices")

        # get matrices
        matrices = list()
        for driver_index in driver_indices:
            matrix = cmds.getAttr(f"{self}.targets[{pose_index}].targetValues[{driver_index}]")
            matrices.append(matrix)

        # ---------------------------------------------------------------------

        # get properties
        function_type = cmds.getAttr(f"{self}.targets[{pose_index}].targetFunctionType", asString=True)
        scale_factor = cmds.getAttr(f"{self}.targets[{pose_index}].targetScaleFactor", asString=True)
        distance_method = cmds.getAttr(f"{self}.targets[{pose_index}].targetDistanceMethod", asString=True)

        pose_blender_data = OrderedDict()
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                pose_matrix = pose_blender_node.get_pose(index=pose_index)
                pose_blender_data[pose_blender_node.driven_transform] = pose_matrix

        pose_data: Dict[str, Any] = OrderedDict()
        pose_data["drivers"] = matrices
        pose_data["driven"] = pose_blender_data
        pose_data["function_type"] = function_type
        pose_data["scale_factor"] = scale_factor
        pose_data["distance_method"] = distance_method
        pose_data["target_enable"] = cmds.getAttr(f"{self}.targets[{pose_index}].targetEnable")
        return pose_data

    def go_to_pose(self, pose_name: str) -> None:
        """
        Sets drivers to current pose
        :param pose_name :type str: name of the pose to move the solvers drivers/driven transform nodes to
        """

        # get drivers
        pose = self.pose(pose_name)
        pose_index = self.pose_index(pose_name)

        matrices = pose["drivers"]
        for driver_index, driver in enumerate(self.drivers()):
            cmds.xform(driver, matrix=matrices[driver_index])

        # If we have pose blenders connected we need to the corresponding pose if we are in edit mode
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                if pose_blender_node.edit:
                    pose_blender_node.go_to_pose(index=pose_index)

    def poses(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns dictionary with poses and their transformation.
        """
        poses = OrderedDict()
        poses_indices = cmds.getAttr(f"{self}.targets", multiIndices=True)
        if poses_indices:
            for pose_index in poses_indices:
                # get pose name
                pose_name = cmds.getAttr(f"{self}.targets[{pose_index}].targetName")
                # BUG - sometimes an unnamed pose will appear when selecting the node causing issues with the indexing
                if pose_name:
                    # get pose transforms
                    poses[pose_name] = self.pose(pose_name)

        return poses

    def add_pose(
        self,
        pose_name: str,
        drivers: Optional[List[str]] = None,
        matrices: Optional[List[float]] = None,
        driven_matrices: Optional[Dict[str, List[float]]] = None,
        function_type: str = "DefaultFunctionType",
        distance_method: str = "DefaultMethod",
        scale_factor: float = 1.0,
        target_enable: bool = True,
    ) -> None:
        """
        Adds pose to RBF Node
        """
        if matrices is None:
            matrices = []

        if drivers and not matrices:
            matrices = [cmds.xform(driver, q=True, matrix=True, objectSpace=True) for driver in drivers]

        if not self.num_drivers():
            raise exceptions.InvalidPose("You must add a driver first.")

        if self.has_pose(pose_name):
            raise exceptions.InvalidPose(f'Already a pose called: "{pose_name}"')

        if len(matrices) != self.num_drivers():
            raise exceptions.InvalidPose("Invalid number of matrices. Must match number of drivers.")
        # get new index
        pose_index = self.num_poses()

        # set matrices
        for driver_index, matrix in enumerate(matrices):
            attr = f"{self}.targets[{pose_index}].targetValues[{driver_index}]"
            cmds.setAttr(attr, matrix, type="matrix")

        # If we have poseBlenders connected we need to create a matching pose on each of those
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            output_attr = f"{self}.outputs[{pose_index}]"
            # Iterate through all the pose blenders
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                driven_transform = pose_blender_node.driven_transform
                if not driven_transform:
                    continue
                # If we have driven matrices we need to set the pose from the matrix provided
                if driven_matrices and driven_matrices.get(driven_transform, []):
                    pose_blender_node.set_pose(
                        index=pose_index, pose_name=pose_name, matrix=driven_matrices.get(driven_transform)
                    )
                else:
                    # Create a pose at the current position in the matching index
                    pose_blender_node.add_pose_from_current(pose_name=pose_name, index=pose_index)
                pose_blender_node.set_weight(index=pose_index, in_float_attr=output_attr)

        # set pose name
        cmds.setAttr(f"{self}.targets[{pose_index}].targetName", pose_name, type="string")

        # create output instance
        cmds.getAttr(f"{self}.outputs[{pose_index}]", type=True)
        # set the enabled status of the pose
        cmds.setAttr(f"{self}.targets[{pose_index}].targetEnable", target_enable)

    def update_pose(
        self, pose_name: str, drivers: Optional[List[str]] = None, matrices: Optional[List[float]] = None
    ) -> None:
        """
        Updates an existing pose on the RBF Node
        """
        if matrices is None:
            matrices = []

        if drivers and not matrices:
            matrices = [cmds.xform(driver, q=True, matrix=True) for driver in drivers]

        if not self.has_pose(pose_name):
            raise RuntimeError(f'Pose "{pose_name}" does not exist')

        # get new index
        pose_index = self.pose_index(pose_name)

        # set matrices
        for driver_index, matrix in enumerate(matrices):
            attr = f"{self}.targets[{pose_index}].targetValues[{driver_index}]"
            cmds.setAttr(attr, matrix, type="matrix")

        # If we have poseBlenders connected we need to create a matching pose on each of those
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                pose_blender_node.set_pose(index=pose_index)

    def add_pose_from_current(self, pose_name: str, update: bool = False) -> None:
        """
        Adds current pose to RBF Node
        """

        # drivers
        matrices = list()
        drivers = self.drivers()
        for driver in drivers:
            matrix = cmds.xform(driver, q=True, matrix=True, objectSpace=True)
            matrices.append(matrix)

        if update:
            self.update_pose(pose_name, drivers, matrices)
        else:
            self.add_pose(pose_name=pose_name, drivers=drivers, matrices=matrices)

    def mirror_pose(
        self,
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
        """
        Mirrors the specified pose using the given mirror mapping to determine the target drivers/driven transforms
        :param pose_name :type str: pose name to mirror
        :param mirror_rotation_axis:
        :param mirror_translation_axis:
        :param solver_search: solver substring to search for
        :param solver_replace: solver substring to replace with
        :param joint_name_search: joint name substring to search for
        :param joint_name_replace: joint name substring to replace with
        """
        mirror_pose_name = pose_name
        if pose_name.lower() != "default" and pose_name_search and pose_name_replace:
            if pose_use_regex:
                match = re.match(pose_name_search, pose_name)
                if not match:
                    raise RuntimeError(f"Unable to mirror pose, could not match {pose_name_search} to {pose_name}")

                mirror_pose_name = pose_name_replace.format(**match.groupdict())
            else:
                mirror_pose_name = pose_name.replace(pose_name_search, pose_name_replace)

        # Get the name of the mirrored solver
        target_solver_name = str(self).replace(solver_search, solver_replace)
        if solver_use_regex:
            match = re.match(solver_search, str(self))
            if not match:
                raise RuntimeError(f"Unable to mirror pose, could not match {solver_search} to {str(self)}")

            target_solver_name = solver_replace.format(**match.groupdict())

        # Check if the solver already exists
        existing_solver_match = [s for s in self.find_all() if str(s) == target_solver_name]
        # Force the base pose
        for solver in self.find_all():
            if solver == self:
                continue
            if solver.has_pose("default"):
                solver.go_to_pose("default")
        # If it does, use it
        if existing_solver_match:
            new_solver = existing_solver_match[0]
        # Otherwise create a new solver that is a mirror of this one
        else:
            new_solver = self.mirror(mirror_poses=False)

        # Go to the pose we want to mirror
        self.go_to_pose(pose_name=pose_name)
        # Store a list of all the transforms affecting this pose
        transforms = self.drivers()
        # Generate a list of the mirrored transforms based on the transforms we found
        mirrored_transforms = [transform.replace(joint_name_search, joint_name_replace) for transform in transforms]
        if joint_use_regex:
            mirrored_transforms = []
            for transform in transforms:
                match = re.match(joint_name_search, transform)
                if not match:
                    raise RuntimeError(f"Unable to mirror pose, could not match {joint_name_search} to {transform}")

                mirrored_transforms.append(joint_name_replace.format(**match.groupdict()))

        for index, source_transform in enumerate(transforms):
            target_transform = mirrored_transforms[index]

            rotate = cmds.getAttr(f"{source_transform}.rotate")[0]
            cmds.setAttr(f"{target_transform}.rotate", *rotate)

        transforms = self.driven_joints()
        # Generate a list of the mirrored transforms based on the transforms we found
        mirrored_transforms = [transform.replace(joint_name_search, joint_name_replace) for transform in transforms]

        if joint_use_regex:
            mirrored_transforms = []
            for transform in transforms:
                match = re.match(joint_name_search, transform)
                if not match:
                    raise RuntimeError(f"Unable to mirror pose, could not match {joint_name_search} to {transform}")

                mirrored_transforms.append(joint_name_replace.format(**match.groupdict()))

        # If we have poseBlenders connected we need to create a matching pose on each of those
        if cmds.attributeQuery("poseBlenders", node=new_solver, exists=True):
            for pose_blender_node_name in cmds.listConnections(f"{new_solver}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                pose_blender_node.edit = True

        # Iterate through all the source transforms
        for index, source_transform in enumerate(transforms):
            # Get the target transform at the same index
            target_transform = mirrored_transforms[index]
            # Need to get each transforms parent so that we can get the relative offset
            # Get the sources parent matrix
            source_parent_matrix = om.MMatrix(cmds.getAttr(f"{source_transform}.parentMatrix"))
            # Get the targets parent matrix
            target_parent_matrix = om.MMatrix(cmds.getAttr(f"{target_transform}.parentMatrix"))
            # Calculate the translation
            translate = om.MVector(*cmds.getAttr(f"{source_transform}.translate"))

            driver_mat_fn = om.MTransformationMatrix(om.MMatrix.kIdentity)
            driver_mat_fn.setTranslation(translate, om.MSpace.kWorld)
            driver_mat = driver_mat_fn.asMatrix()

            if mirror_translation_axis.lower() == "x":
                scale = [-1.0, 1.0, 1.0]
            elif mirror_rotation_axis.lower() == "y":
                scale = [1.0, -1.0, 1.0]
            else:
                scale = [1.0, 1.0, -1.0]

            scale_matrix_fn = om.MTransformationMatrix(om.MMatrix.kIdentity)
            scale_matrix_fn.setScale(scale, om.MSpace.kWorld)
            scale_matrix = scale_matrix_fn.asMatrix()

            pos_matrix = driver_mat * source_parent_matrix
            pos_matrix = pos_matrix * scale_matrix
            pos_matrix = pos_matrix * target_parent_matrix.inverse()
            mat_fn = om.MTransformationMatrix(pos_matrix)

            cmds.setAttr(f"{target_transform}.translate", *mat_fn.translation(om.MSpace.kWorld))

            # Calculate the rotation
            rotate = om.MVector(*cmds.getAttr(f"{source_transform}.rotate"))

            driver_mat_fn = om.MTransformationMatrix(om.MMatrix.kIdentity)
            # set the values to radians
            euler = om.MEulerRotation(*[math.radians(i) for i in rotate])

            driver_mat_fn.setRotation(euler)
            driver_matrix = driver_mat_fn.asMatrix()

            world_matrix = driver_matrix * source_parent_matrix
            rot_matrix = source_parent_matrix.inverse() * world_matrix
            rot_matrix_fn = om.MTransformationMatrix(rot_matrix)
            rot = rot_matrix_fn.rotation(asQuaternion=True)
            if mirror_rotation_axis.lower() == "x":
                rot.x = rot.x * -1.0
            elif mirror_rotation_axis.lower() == "y":
                rot.y = rot.y * -1.0
            else:
                rot.z = rot.z * -1.0

            rot.w = rot.w * -1.0
            rot_matrix = rot.asMatrix()
            final_rot_matrix = target_parent_matrix * rot_matrix * target_parent_matrix.inverse()

            rot_matrix_fn = om.MTransformationMatrix(final_rot_matrix)
            rot = rot_matrix_fn.rotation(asQuaternion=False)
            m_rot = om.MVector(*[math.degrees(i) for i in rot])

            cmds.setAttr(f"{target_transform}.rotate", *m_rot)

            # Assume scale is the same
            cmds.setAttr(f"{target_transform}.scale", *cmds.getAttr(f"{source_transform}.scale")[0])
        # Add a new pose on the mirrored solver with the same name, update if the pose already exists
        new_pose_name = mirror_pose_name if mirror_pose_name else pose_name
        new_solver.add_pose_from_current(
            pose_name=new_pose_name,
            update=new_solver.has_pose(pose_name=new_pose_name),
        )

        # If we have poseBlenders connected we need to create a matching pose on each of those
        if cmds.attributeQuery("poseBlenders", node=new_solver, exists=True):
            for pose_blender_node_name in cmds.listConnections(f"{new_solver}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                pose_blender_node.edit = False

    def delete_pose(self, pose_name: str) -> None:
        """
        Delete the specified pose name
        :param pose_name :type str: pose name to delete
        """
        # If the pose doesn't exist, raise an exception
        if not self.has_pose(pose_name):
            raise exceptions.InvalidPose(f"Pose {pose_name} does not exist.")

        LOG.debug(f"Removing pose: '{pose_name}'")

        # Get the existing poses from the solver
        poses = self.poses()
        pose_index = self.pose_index(pose_name)

        # Iterate through the existing drivers in reverse
        for index in reversed(range(len(list(poses.keys())))):
            # Remove the pose from the list of targets
            cmds.removeMultiInstance(f"{self}.targets[{index}]", b=True)

        # Remove the deleted pose
        poses.pop(pose_name)

        # If we have poseBlenders connected we need to create a matching pose on each of those
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                pose_blender_node.delete_pose(index=pose_index)

        # Iterate through the remaining poses and recreate them
        for pose_name, pose_data in poses.items():
            pose_data["matrices"] = pose_data.pop("drivers")
            pose_data["driven_matrices"] = pose_data.pop("driven")
            # Add the pose with the specified kwargs
            self.add_pose(pose_name=pose_name, **pose_data)

    def is_pose_muted(self, pose_name: str = "", pose_index: int = -1) -> bool:
        """
        Gets the current status of the pose if it is muted or not
        :param pose_name :type str: optional pose name
        :param pose_index :type index, optional pose index
        :return :type bool: True if the pose is muted, else False
        """
        # Get the pose index if name is specified and the index hasn't been
        if pose_index < 0 and pose_name:
            pose_index = self.pose_index(pose_name)
        elif not pose_name and pose_index < 0:
            raise exceptions.InvalidPoseIndex("Unable to query the mute status, no pose name or index specified")

        attr = f"{self}.targets[{pose_index}].targetEnable"
        return not cmds.getAttr(attr)

    def mute_pose(self, pose_name: str = "", pose_index: int = -1, mute: bool = True) -> bool:
        """
        Mute or unmute the specified pose, removing all influences of the pose from the solver.
        NOTE: This will affect the solver radius if automatic radius is enabled.
        :param pose_name :type str: optional name of the pose
        :param pose_index :type index, optional pose index
        :param mute :type bool: mute or unmute the pose
        """
        # Get the pose index if name is specified and the index hasn't been
        if pose_index < 0 and pose_name:
            pose_index = self.pose_index(pose_name)
        elif not pose_name and pose_index < 0:
            raise exceptions.InvalidPoseIndex("Unable to query the mute status, no pose name or index specified")

        attr = f"{self}.targets[{pose_index}].targetEnable"
        if mute is None:
            mute = not self.is_pose_muted(pose_index=pose_index)
        cmds.setAttr(attr, not mute)
        return not mute

    def edit_solver(self, edit: bool = True) -> None:
        """
        Edit or finish editing this solver
        :param edit :type bool: set edit mode on or off
        """
        # If we have poseBlenders connected we need to toggle the output connection based on the edit param
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            # Iterate through all the pose blenders
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                # Enable or disable edit mode on the blender
                pose_blender_node.edit = edit

        # Force the base pose
        for solver in self.find_all():
            if solver != self and solver.has_pose("default"):
                solver.go_to_pose("default")

    def get_solver_edit_status(self) -> bool:
        """
        Gets this solvers edit status
        :return :type bool: True if in edit mode, False if not
        """
        # If we have poseBlenders connected we need to toggle the output connection based on the edit param
        if cmds.attributeQuery("poseBlenders", node=self, exists=True):
            # Iterate through all the pose blenders
            for pose_blender_node_name in cmds.listConnections(f"{self}.poseBlenders") or []:
                # Get the pose blender wrapper from the node name
                pose_blender_node = pose_blender.UEPoseBlenderNode(pose_blender_node_name)
                # If one blender node is in edit mode, then mark the solver as in edit mode
                if pose_blender_node.edit:
                    return True
        return False

    def pose_name(self, pose_index: int) -> Optional[str]:
        """
        Returns pose name from index
        """

        poses_indices = cmds.getAttr(f"{self}.targets", multiIndices=True)
        if poses_indices and pose_index in poses_indices:
            return cast(str, cmds.getAttr(f"{self}.targets[{pose_index}].targetName"))

        return None

    def rename_pose(self, pose_index: int, pose_name: str) -> str:
        """
        Renames a pose given an index
        """

        poses_indices = cmds.getAttr(f"{self}.targets", multiIndices=True)
        if poses_indices:
            if pose_index not in poses_indices:
                raise RuntimeError(f'Pose Index "{pose_index}" not found')

            if self.has_pose(pose_name):
                raise RuntimeError(f'Pose "{pose_name}" already exists')

            cmds.setAttr(f"{self}.targets[{pose_index}].targetName", pose_name, type="string")

        return pose_name

    def mirror(
        self,
        mirror_poses: bool = True,
        mirror_rotation_axis: str = "x",
        mirror_translation_axis: str = "x",
        solver_search: str = "",
        solver_replace: str = "",
        joint_name_search: str = "",
        joint_name_replace: str = "",
        pose_name_search: str = "",
        pose_name_replace: str = "",
        solver_use_regex: bool = False,
        joint_use_regex: bool = False,
        pose_use_regex: bool = False,
    ) -> "RBFNode":
        """
        Mirror this RBF Solver
        :param mirror_poses :type bool: should we mirror poses too?
        :param mirror_rotation_axis:
        :param mirror_translation_axis:
        :param solver_search: solver substring to search for
        :param solver_replace: solver substring to replace with
        :param joint_name_search: joint name substring to search for
        :param joint_name_replace: joint name substring to replace with
        :param pose_name_search: Optional pose name substring to search for
        :param pose_name_replace: Optional pose name substring to replace with
        :return :type RBFNode: mirrored RBF Solver wrapper
        """
        # Get the name of the mirrored solver
        target_solver_name = str(self).replace(solver_search, solver_replace)
        if solver_use_regex:
            match = re.match(solver_search, str(self))
            if not match:
                raise RuntimeError(f"Unable to mirror pose, could not match {solver_search} to {str(self)}")

            target_solver_name = solver_replace.format(**match.groupdict())

        LOG.debug(f"Creating mirrored solver: '{target_solver_name}")
        # Serialize the solver data
        solver_data = self.data()
        # Grab the drivers  and driven from the serialized data
        mirrored_transform_data = {
            "drivers": solver_data.pop("drivers"),
            "driven_transforms": solver_data.pop("driven_transforms"),
        }
        # Iterate through the drivers and driven transforms to find their mirrored counterpart
        for key, transforms in mirrored_transform_data.items():
            # Update the dict with the new transforms
            mirrored_transform_data[key] = [
                transform.replace(joint_name_search, joint_name_replace) for transform in transforms
            ]
            if joint_use_regex:
                mirrored_transform_data[key] = []
                for transform in transforms:
                    match = re.match(joint_name_search, transform)
                    if not match:
                        raise RuntimeError(f"Unable to mirror pose, could not match {joint_name_search} to {transform}")

                    mirrored_transform_data[key].append(joint_name_replace.format(**match.groupdict()))

        # Update the solver data with the new drivers
        solver_data["drivers"] = mirrored_transform_data.pop("drivers")
        # Update the solver data with the new driven transforms
        solver_data["driven_transforms"] = mirrored_transform_data.pop("driven_transforms")
        # Update the solver data with the new solver name
        solver_data["solver_name"] = target_solver_name

        # Remove pose data to iterate over later
        pose_data = solver_data.pop("poses")
        solver_data["poses"] = OrderedDict()

        # Delete any existing solvers:
        for solver in [solver for solver in RBFNode.find_all() if str(solver) == target_solver_name]:
            solver.delete()
        # Create a new solver from the data
        mirrored_solver = RBFNode.create_from_data(solver_data)

        # If we are mirroring poses, iterate through each pose and mirror it
        if mirror_poses:
            for pose_name in pose_data:
                self.mirror_pose(
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

            # Force the base pose
            for solver in self.find_all():
                if solver.has_pose("default"):
                    solver.go_to_pose("default")
        # If we aren't mirroring poses, create the default pose
        else:
            mirrored_solver.add_pose_from_current(pose_name="default")

        return mirrored_solver

    def delete(self) -> None:
        """
        Delete the Maya node associated with this class
        """
        cmds.delete(self._node)

    # ----------------------------------------------------------------------------------------------
    #                                        ENUM UTILS
    # ----------------------------------------------------------------------------------------------

    def _set_enum_attribute(self, attribute: str, value: Union[str, int]) -> None:
        """
        Sets enum attribute either by string or index value
        """

        if isinstance(value, str):
            # get enum index
            selection_list = OpenMaya.MSelectionList()
            selection_list.add(attribute)

            plug = OpenMaya.MPlug()
            selection_list.getPlug(0, plug)

            mfn = OpenMaya.MFnEnumAttribute(plug.attribute())
            index = mfn.fieldIndex(value)

            cmds.setAttr(attribute, index)

        else:
            cmds.setAttr(attribute, value)

    def _get_mirrored_solver_name(self, mirror_mapping: "mirror_mapping.MirrorMapping") -> str:
        """
        Generate the mirrored solver name using the specified mirror mapping
        :param mirror_mapping :type pose_editor.model.mirror_mapping.MirrorMapping: mirror mapping ref
        :return :type str: mirrored solver name
        """
        # Grab the solver expression from the mirror mapping and check that this solver matches the correct naming
        match = re.match(mirror_mapping.solver_expression, str(self))
        # If it doesn't match, raise exception
        if not match:
            raise exceptions.InvalidMirrorMapping(
                f"Unable to mirror solver '{self}'. The naming conventions do "
                f"not match the mirror mapping specified: {mirror_mapping.solver_expression}"
            )

        # Generate the new pose driver name
        target_rbf_solver_name = ""
        for group in match.groups():
            # If the the group matches the source solver syntax, change the group to be the target syntax.
            # I.e if the source is _l_, change it to _r_
            if group == mirror_mapping.source_solver_syntax:
                group = mirror_mapping.target_solver_syntax
            # If the group matches the target, change the group to the source and swap the sides in the config
            elif group == mirror_mapping.target_solver_syntax:
                group = mirror_mapping.source_solver_syntax
                mirror_mapping.swap_sides()
            # Add the group name to generate the new name for the solver
            target_rbf_solver_name += group
        return target_rbf_solver_name

    def _get_mirrored_transforms(
        self, transforms: List[str], mirror_mapping: "mirror_mapping.MirrorMapping", ignore_invalid_nodes: bool = False
    ) -> List[str]:
        """
        Generate a list of transforms that mirror the list given
        :param transforms :type list: list of transforms to get the mirrored name for
        :param mirror_mapping :type pose_editor.model.mirror_mapping.MirrorMapping: mirror mapping ref
        :return :type list: list of mirrored transform names
        """
        # Generate empty list to store the newly mapped transforms
        new_transforms = []
        for transform in transforms:
            # Check if the transform matches the target transform expression
            match = re.match(mirror_mapping.transform_expression, transform)
            # If it doesn't, raise exception. Can't work with incorrectly named transforms
            if not match:
                raise exceptions.InvalidMirrorMapping(
                    f"Unable to mirror transform '{transform}'. The naming conventions do "
                    f"not match the mirror mapping specified: {mirror_mapping.transform_expression}"
                )
            # Generate the new pose transform name
            target_transform_name = ""
            # Iterate through the groups
            for group in match.groups():
                # If the group matches the source transform syntax, change the group to be the target syntax.
                if group == mirror_mapping.source_transform_syntax:
                    group = mirror_mapping.target_transform_syntax
                elif group == mirror_mapping.target_transform_syntax:
                    group = mirror_mapping.source_transform_syntax
                # Add the group name to generate the new name for the transform
                target_transform_name += group
            # If the generated transform name doesn't exist, raise exception
            if not cmds.ls(target_transform_name) and not ignore_invalid_nodes:
                raise exceptions.InvalidMirrorMapping(
                    f"Unable to mirror transform '{transform}'. Target transform does not exist: '{target_transform_name}'"
                )
            # Add the new transform to the list
            new_transforms.append(target_transform_name)
        return new_transforms
