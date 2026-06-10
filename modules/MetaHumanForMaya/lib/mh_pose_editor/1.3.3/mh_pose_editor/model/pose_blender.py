# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import copy
from typing import TYPE_CHECKING, List, Union, Optional, cast

# External
from maya import cmds
from maya.api import OpenMaya as om

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import utils, exceptions

if TYPE_CHECKING:
    from mh_pose_editor.model import rbf_node


class UEPoseBlenderNode:
    """
    Class wrapper for UEPoseBlenderNode
    """

    node_type = "UEPoseBlenderNode"

    @classmethod
    def create(cls, driven_transform: Optional[str] = None) -> "UEPoseBlenderNode":
        """
        Create Pose Blender Node
        >>> new_node = UEPoseBlenderNode.create()
        """
        name = driven_transform
        # If no name is specified, generate unique name
        if name is None:
            name = f"{cls.node_type}#"
        name += f"_{cls.__name__}"
        # Create node
        node = cmds.createNode(cls.node_type, name=name)
        node_ref = cls(node)
        # If a driving transform is specified, connect it via a message attribute and set the base pose
        if driven_transform is not None:
            utils.message_connect(
                from_attribute=f"{node}.drivenTransform",
                to_attribute=f"{driven_transform}.poseBlender",
            )
            # Set the base pose
            node_ref.base_pose = utils.get_local_matrix_without_joint_orient(transform_name=driven_transform)
        # Return the new UEPoseBlenderNode reference
        return node_ref

    @classmethod
    def find_all(cls) -> List["UEPoseBlenderNode"]:
        """
        Returns all PoseBlender nodes in scene
        """
        return [cls(node) for node in cmds.ls(type=cls.node_type)]

    @classmethod
    def find_by_name(cls, name: str) -> Optional["UEPoseBlenderNode"]:
        """
        Find a UEPoseBlenderNode class with the specified name
        :param name :type str: name of the node
        :return :type UEPoseBlenderNode or None:
        """
        if not name.endswith(cls.node_type):
            name += f"_{cls.node_type}"
        match = cmds.ls(name, type=cls.node_type)
        return cls(match[0]) if match else None

    @classmethod
    def find_by_transform(cls, transform: str) -> Optional["UEPoseBlenderNode"]:
        """
        Finds a UEPoseBlenderNode class connected to the specified joint
        :param transform :type str: name of the transform
        :return :type UEPoseBlenderNode or None
        """
        if not cmds.attributeQuery("poseBlender", node=transform, exists=True):
            return None
        connections = cmds.listConnections(f"{transform}.poseBlender")
        if not connections:
            return None

        return cls(connections[0])

    def __init__(self, node: str) -> None:
        # If the node doesn't exist, raise an exception
        if not cmds.objectType(node, isAType=self.node_type):
            raise exceptions.InvalidNodeType(f'Invalid "{self.node_type}" node: "{node}"')
        # Store a reference ot the MObject in case the name of the node is changed whilst this class is still in use
        self._node = om.MFnDependencyNode(om.MGlobal.getSelectionListByName(node).getDependNode(0))

    def __repr__(self) -> str:
        """
        Returns class string representation
        """
        return f"<{self.node_type}>: {self}"

    def __str__(self) -> str:
        """
        Returns class as string
        """
        return str(self.node)

    def __eq__(self, other) -> bool:
        """
        Returns if two objects are the same, allows for comparing two different UEPoseBlenderNode references that wrap
        the same MObject
        """
        return str(self) == str(other)

    def __enter__(self) -> None:
        """
        Override the __enter__ to allow for this class to be used as a context manager to toggle edit mode
        >>> pose_blender = UEPoseBlenderNode('TestPoseBlenderNode')
        >>> with pose_blender:
        >>>     # Edit mode enabled so changes can be made
        >>>     pass
        >>> # Edit mode is now disabled
        """
        self.edit = True

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        On exit, disable edit mode
        """
        self.edit = not self.edit

    @property
    def node(self) -> str:
        return str(self._node.name())

    @property
    def rbf_solver_attr(self) -> str:
        return f"{self.node}.rbfSolver"

    @property
    def base_pose_attr(self) -> str:
        return f"{self.node}.basePose"

    @property
    def envelope_attr(self) -> str:
        return f"{self.node}.envelope"

    @property
    def in_matrix_attr(self) -> str:
        return f"{self.node}.inMatrix"

    @property
    def out_matrix_attr(self) -> str:
        return f"{self.node}.outMatrix"

    @property
    def poses_attr(self) -> str:
        return f"{self.node}.poses"

    @property
    def weights_attr(self) -> str:
        return f"{self.node}.weights"

    @property
    def driven_transform(self) -> Optional[str]:
        """
        Get the current driven transform
        :return :type str: transform node name
        """
        if cmds.attributeQuery("drivenTransform", node=self.node, exists=True):
            transforms: List[str] = cmds.listConnections(f"{self.node}.drivenTransform")
            if transforms:
                return transforms[0]

        return None

    @property
    def edit(self) -> bool:
        """
        :return :type bool: are the driven transforms connected to this node editable?
        """
        transform = self.driven_transform
        # If no transform, we can edit!
        if not transform:
            return True
        # False if we have any matrix connections, otherwise we have no connections and can edit
        return not bool(cmds.listConnections(self.out_matrix_attr))

    @edit.setter
    def edit(self, value: bool) -> None:
        """
        Allow the driven transforms to be edited (or not)
        :param value :type bool: edit mode enabled True/False
        """
        # If we don't have a driven transform we can't do anything
        transform = self.driven_transform
        if not transform:
            return None

        # If we are in edit mode, disable out connections
        if bool(value):
            self.set_out_matrix(None)
        # Otherwise connect up the transform
        else:
            self.set_out_matrix(transform)

    @property
    def rbf_solver(self) -> Optional["rbf_node.RBFNode"]:
        """
        :return:The connected rbf solver node if it exists
        """
        # Check the attr exists
        exists = cmds.attributeQuery(self.rbf_solver_attr.split(".")[-1], node=self.node, exists=True)
        if exists:
            # Query the connections
            connections = cmds.listConnections(self.rbf_solver_attr) or []
            if connections:
                from mh_pose_editor.model import rbf_node

                # Return the node if the attr exists and a connection is found
                return rbf_node.RBFNode(connections[0])

        return None

    def set_rbf_solver(self, rbf_solver_attr: str) -> None:
        """
        Connects up this node to an rbf solver node
        :param rbf_solver_attr: the attribute on the rbf solver to connect this to i.e my_rbf_solver.poseBlend_back_120
        """
        utils.message_connect(rbf_solver_attr, self.rbf_solver_attr)

    @property
    def base_pose(self) -> Optional[List[float]]:
        """
        :return :type list: matrix
        """
        return self.get_pose(index=0)

    @base_pose.setter
    def base_pose(self, matrix: List[float]) -> None:
        """
        Set the base pose to a specific pose.PoseNode
        :param matrix :type list: Matrix to set as base pose
        """
        # Connect up the pose's outputLocalMatrix to the basePose plug
        utils.set_attr_or_connect(source_attr_name=self.base_pose_attr, value=matrix, attr_type="matrix")
        # Set the inMatrix to the basePose plug
        self.in_matrix = matrix
        # Set the first pose in the pose list to the new base pose
        self.set_pose(index=0, overwrite=True, matrix=matrix)

    @property
    def envelope(self) -> Union[float, int, str]:
        """
        Get the value of the envelope attr from this node
        """
        return cast(Union[float, int, str], utils.get_attr(self.envelope_attr, as_value=True))

    @envelope.setter
    def envelope(self, value: Union[float, int, str]) -> None:
        """
        Sets the envelope
        :param value: float, int or string (i.e node.attributeName). Float/Int will set the value, whilst
        passing an attribute will connect the plugs
        """
        if isinstance(value, float) or isinstance(value, int) and 0 > value > 1:
            value = min(max(0.0, value), 1.0)
        utils.set_attr_or_connect(source_attr_name=self.envelope_attr, value=value)

    @property
    def in_matrix(self) -> Union[List[float], str]:
        """
        Get the inMatrix value
        :return: matrix or attributeName
        """
        # Get the current value of the attribute
        return cast(Union[List[float], str], utils.get_attr(self.in_matrix_attr, as_value=True))

    @in_matrix.setter
    def in_matrix(self, value: Union[List[float], str]) -> None:
        """
        Sets the inMatrix attribute to a value or connects it to another matrix plug
        :param value: matrix (list) or string node.attributeName
        """
        utils.set_attr_or_connect(source_attr_name=self.in_matrix_attr, value=value, attr_type="matrix")

    @property
    def out_matrix(self) -> List[float]:
        """
        :return:
        """
        return cast(List[float], cmds.getAttr(self.out_matrix_attr))

    def set_out_matrix(self, transform_name: Optional[str] = None) -> None:
        """
        Connect the output matrix up to a given transform node
        :param transform_name: name of a transform node to connect to
        """
        # If a transform is specified, connect it
        current_selection = cmds.ls(selection=True)
        if transform_name:
            # Check that the node type is a transform
            if not cmds.ls(transform_name, type="transform"):
                # If it's not a transform raise an error
                raise exceptions.InvalidNodeType(
                    f"Invalid node type. Expected 'transform', received '{cmds.objectType(transform_name)}'"
                )
            # Create a new decomposeMatrix node to convert the outMatrix to T,R,S
            mx_decompose_node = cmds.createNode("decomposeMatrix", name=f"{self.node}_dmt")
            # Connect the outMatrix up to the decomposeMatrix's input
            cmds.connectAttr(self.out_matrix_attr, f"{mx_decompose_node}.inputMatrix")
            # Create an iterator with TRS attributes
            attributes = ("translate", "rotate", "scale")
            # Iterate through each attr and connect it
            for attr in attributes:
                out_attr = f"{mx_decompose_node}.output{attr.capitalize()}"
                in_attr = f"{transform_name}.{attr}"
                cmds.connectAttr(out_attr, in_attr, force=True)
        else:
            # No transform was specified, disconnect all existing connections
            connections = cmds.listConnections(self.out_matrix_attr, type="decomposeMatrix")
            current_matrix = cmds.xform(self.driven_transform, query=True, matrix=True, worldSpace=True)

            if connections:
                cmds.delete(connections)
            for connection in cmds.listConnections(self.out_matrix_attr, plugs=True) or []:
                cmds.disconnectAttr(self.out_matrix_attr, connection)
            cmds.xform(self.driven_transform, matrix=current_matrix, worldSpace=True)
        cmds.select(current_selection, replace=True)

    def get_pose(self, index: int = -1) -> Optional[List[float]]:
        """
        Get the pose at the specified index
        :param index :type int: index to query
        :return :type list matrix or None
        """
        # Get the value of the pose_attr at the specified index
        attr: Optional[List[float]] = utils.get_attr(f"{self.poses_attr}[{index}]", as_value=True)
        return attr

    def get_poses(self) -> List[List[float]]:
        """
        :return :type list of matrices
        """
        return utils.get_attr_array(attr_name=self.poses_attr, as_value=True)

    def add_pose_from_current(self, pose_name: str, index: int = -1) -> None:
        """
        Add a pose from the current transforms positions
        :param pose_name :type str: name of the pose
        :param index :type int: target index for the pose
        """
        # Find the next index if no index is specified
        if index < 0:
            # If the index is less than 0 find the next available index
            index = len(cmds.getAttr(self.poses_attr, multiIndices=True) or [0]) - 1
        # Store driven transform in var to reduce number of cmds calls
        driven_transform = self.driven_transform
        if not driven_transform:
            raise exceptions.PoseBlenderPoseError(
                "No driven transform associated with this node, " "unable to get the current matrix"
            )
        # Set the pose
        self.set_pose(
            index=index, pose_name=pose_name, matrix=utils.get_local_matrix_without_joint_orient(driven_transform)
        )

    def set_pose(
        self,
        index: int = -1,
        pose_name: Optional[str] = "",
        overwrite: bool = True,
        matrix: Optional[List[float]] = None,
    ) -> None:
        """
        Set a pose for the specified index
        :param index: int value of the index to set
        :param pose_name: name of the pose as a string
        :param overwrite: should it overwrite any existing pose at the index or insert
        :param matrix: local matrix value to set
        """
        # Find the next index if no index is specified
        if index < 0:
            if pose_name:
                LOG.warning("Set Pose has not been implemented to support a pose name. FIXME")
                return
            else:
                # If the index is less than 0 find the next available index
                index = len(cmds.getAttr(self.poses_attr, multiIndices=True) or [0]) - 1

        # If no matrix is specified, grab the matrix for the driven transform
        driven_transform = self.driven_transform
        if matrix is None and driven_transform:
            matrix = utils.get_local_matrix_without_joint_orient(transform_name=driven_transform)

        if not overwrite:
            pose_count = len(cmds.getAttr(self.poses_attr, multiIndices=True) or [])
            if pose_count - 1 > index:
                pass

        # Generate the source attribute (the attribute on this node) from the default attr and given index
        source_attr_name = f"{self.poses_attr}[{index}]"
        # Set the pose
        utils.set_attr_or_connect(source_attr_name=source_attr_name, value=matrix, attr_type="matrix")

    def go_to_pose(self, index: int = -1) -> None:
        """
        Move the driven transform to the matrix stored in the pose list at the specified index
        :param index :type index: index to go to
        """
        # Get the matrix at the specified index
        pose_matrix = self.get_pose(index=index)
        if not pose_matrix:
            return None

        translation, rotation, scale = utils.decompose_matrix(pose_matrix)
        # Assume the position ignoring joint orient
        cmds.setAttr(f"{self.driven_transform}.translate", *translation)
        cmds.setAttr(f"{self.driven_transform}.rotate", *rotation)
        cmds.setAttr(f"{self.driven_transform}.scale", *scale)

    def delete_pose(self, index: int = -1, pose_name: str = "") -> None:
        """
        Delete a pose at the specified index or with the given name
        :param index :type int: index to delete or -1 to use pose_name
        :param pose_name :type str: pose name to delete
        """
        # TODO Delete pose will need to remember enabled state + reconnect up pose_name connection when the changes are
        #  made to the solver. Currently can't delete by pose name because there is nothing tying an index to a pose
        #  name
        # If no index and no pose name, raise exception
        if index < 0 and not pose_name:
            raise exceptions.InvalidPoseIndex("Unable to delete pose")

        # Copy a list of the poses
        poses = copy.deepcopy(self.get_poses())

        # Iterate through the existing poses in reverse
        for i in reversed(range(len(poses))):
            # Remove the pose from the list of targets
            cmds.removeMultiInstance(f"{self}.poses[{i}]", b=True)

        # Remove the pose at the given index
        poses.pop(index)

        # Re-add all the deleted poses (minus the one we popped)
        for pose_index, matrix in enumerate(poses):
            self.set_pose(index=pose_index, matrix=matrix)

    def get_weight(self, index: int, as_float: bool = True) -> Union[float, str]:
        """
        Get the current weight for the specified index
        :param index :type int
        :param as_float :type bool: return as float or as attribute name of the connected plug
        :return: float or plug
        """
        attr: Union[float, str] = utils.get_attr(f"{self.weights_attr}[{index}]", as_value=as_float)
        return attr

    def get_weights(self, as_float: bool = True) -> Union[List[float], str]:
        """
        Get all the weights associated with this node
        :param as_float :type bool: as list of floats or list of plugs
        :return: list of floats or plugs
        """
        attr: Union[List[float], str] = utils.get_attr_array(attr_name=self.weights_attr, as_value=as_float)
        return attr

    def set_weight(
        self, index: int = -1, in_float_attr: Optional[str] = "", float_value: Optional[float] = 0.0
    ) -> None:
        """
        Set the weight at a given index either by connecting an attribute or specifying a float value
        :param index :type int: index to set
        :param in_float_attr :type str: node.attributeName to connect to this plug
        :param float_value :type float: float value to set
        """
        if index < 0:
            # If the index is less than 0 find the next available index
            index = len(cmds.getAttr(self.weights_attr, multiIndices=True) or [0]) - 1
        # Generate the correct source attr name for the index specified
        source_attr_name = f"{self.weights_attr}[{index}]"
        # Set the array element to either the attr or the float value
        utils.set_attr_or_connect(source_attr_name=source_attr_name, value=in_float_attr or float_value)

    def set_weights(self, in_float_array_attr: Optional[str] = "", floats: Optional[List[float]] = None) -> None:
        """
        Set multiple weights either by an attribute array string or a float list.Will overwrite existing values
        :param in_float_array_attr :type str: node.attributeName array attribute to connect all indices with
        :param floats :type list: list of float values to set for each corresponding index
        """
        # Prioritize plugs over setting floats
        if in_float_array_attr:
            # Iterate through all the indices in the array
            for i in range(len(cmds.getAttr(in_float_array_attr, multiIndices=True) or [0])):
                # Generate the source attr name
                in_float_attr = f"{in_float_array_attr}[{i}]"
                # Set the weight for the current index
                self.set_weight(index=i, in_float_attr=in_float_attr)
        elif floats:
            # Iterate through the floats
            for index, float_value in enumerate(floats):
                # Set the weight for the current index
                self.set_weight(index=index, float_value=float_value)

    def delete(self) -> None:
        """
        Delete the node associated with this wrapper
        """
        # If we aren't in edit mode we still have connections made to decomposeMatrix nodes that we want to delete
        if not self.edit:
            # Enable edit mode to delete those decomposeMatrix nodes
            self.edit = True
        # Disconnect all attrs
        destination_conns = cmds.listConnections(self, plugs=True, connections=True, source=False) or []
        for i in range(0, len(destination_conns), 2):
            cmds.disconnectAttr(destination_conns[i], destination_conns[i + 1])
        source_conns = cmds.listConnections(self, plugs=True, connections=True, destination=False) or []

        for i in range(0, len(source_conns), 2):
            # we have to flip these because the output is always node centric and not connection centric
            cmds.disconnectAttr(source_conns[i + 1], source_conns[i])
        # Delete the node
        cmds.delete(self.node)
