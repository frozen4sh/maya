# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import math
import traceback
from typing import Any, List, Tuple, Optional

# External
from maya import OpenMaya, cmds

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import exceptions

# NOTE: MTransformationMatrix & MEulerRotation have different values for the same axis.
XFORM_ROTATION_ORDER = {
    "xyz": OpenMaya.MTransformationMatrix.kXYZ,
    "yzx": OpenMaya.MTransformationMatrix.kYZX,
    "zxy": OpenMaya.MTransformationMatrix.kZXY,
    "xzy": OpenMaya.MTransformationMatrix.kXZY,
    "yxz": OpenMaya.MTransformationMatrix.kYXZ,
    "zyx": OpenMaya.MTransformationMatrix.kZYX,
}

EULER_ROTATION_ORDER = {
    "xyz": OpenMaya.MEulerRotation.kXYZ,
    "yzx": OpenMaya.MEulerRotation.kYZX,
    "zxy": OpenMaya.MEulerRotation.kZXY,
    "xzy": OpenMaya.MEulerRotation.kXZY,
    "yxz": OpenMaya.MEulerRotation.kYXZ,
    "zyx": OpenMaya.MEulerRotation.kZYX,
}


def compose_matrix(
    position: Tuple[float, float, float],
    rotation: Tuple[float, float, float],
    scale: Tuple[float, float, float],
    rotation_order: str = "xyz",
) -> List[float]:
    """
    Compose a 4x4 matrix with given transformation.

    >>> compose_matrix((0.0, 0.0, 0.0), (90.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    """

    # create rotation ptr
    rot_script_util = OpenMaya.MScriptUtil()
    rot_script_util.createFromDouble(*[deg * math.pi / 180.0 for deg in rotation])
    rot_double_ptr = rot_script_util.asDoublePtr()

    # construct transformation matrix
    xform_matrix = OpenMaya.MTransformationMatrix()
    xform_matrix.setTranslation(OpenMaya.MVector(*position), OpenMaya.MSpace.kTransform)
    xform_matrix.setRotation(rot_double_ptr, XFORM_ROTATION_ORDER[rotation_order], OpenMaya.MSpace.kTransform)

    util = OpenMaya.MScriptUtil()
    util.createFromList(scale, 3)
    scale_pointer = util.asDoublePtr()
    xform_matrix.setScale(scale_pointer, OpenMaya.MSpace.kTransform)

    matrix = xform_matrix.asMatrix()
    return [matrix(m, n) for m in range(4) for n in range(4)]


def decompose_matrix(
    matrix: List[float], rotation_order: str = "xyz"
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Decomposes a 4x4 matrix into translation and rotation.

    >>> decompose_matrix([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    ((0.0, 0.0, 0.0), (90.0, 0.0, 0.0))
    """
    if isinstance(matrix, (list, tuple)):
        mmatrix = OpenMaya.MMatrix()
        OpenMaya.MScriptUtil.createMatrixFromList(matrix, mmatrix)
    else:
        mmatrix = matrix

    # create transformation matrix
    xform_matrix = OpenMaya.MTransformationMatrix(mmatrix)

    # get translation
    translation = xform_matrix.getTranslation(OpenMaya.MSpace.kTransform)

    # get rotation
    # @ref: https://github.com/LumaPictures/pymel/blob/master/pymel/core/datatypes.py
    # The apicls getRotation needs a "RotationOrder &" object, which is impossible to make in python...
    euler_rotation = xform_matrix.eulerRotation()
    euler_rotation.reorderIt(EULER_ROTATION_ORDER[rotation_order])
    rotation = euler_rotation.asVector()

    util = OpenMaya.MScriptUtil()
    util.createFromList([1.0, 1.0, 1.0], 3)
    scale_pointer = util.asDoublePtr()

    xform_matrix.getScale(scale_pointer, OpenMaya.MSpace.kTransform)

    scale_x = OpenMaya.MScriptUtil().getDoubleArrayItem(scale_pointer, 0)
    scale_y = OpenMaya.MScriptUtil().getDoubleArrayItem(scale_pointer, 1)
    scale_z = OpenMaya.MScriptUtil().getDoubleArrayItem(scale_pointer, 2)

    return (
        (translation.x, translation.y, translation.z),
        (rotation.x * 180.0 / math.pi, rotation.y * 180.0 / math.pi, rotation.z * 180.0 / math.pi),
        (scale_x, scale_y, scale_z),
    )


def euler_to_quaternion(
    rotation: Tuple[float, float, float], rotation_order: str = "xyz"
) -> Tuple[float, float, float, float]:
    """
    Returns Euler Rotation as Quaternion

    >>> euler_to_quaternion((90, 0, 0))
    (0.7071, 0.0, 0.0, 0.70710))
    """
    euler_rotation = OpenMaya.MEulerRotation(
        rotation[0] * math.pi / 180.0, rotation[1] * math.pi / 180.0, rotation[2] * math.pi / 180.0
    )
    euler_rotation.reorderIt(EULER_ROTATION_ORDER[rotation_order])

    quat = euler_rotation.asQuaternion()
    return quat.x, quat.y, quat.z, quat.w


def quaternion_to_euler(
    rotation: Tuple[float, float, float, float], rotation_order: str = "xyz"
) -> Tuple[float, float, float]:
    """
    Returns Quaternion Rotation as Euler

    quaternion_to_euler((0.7071, 0.0, 0.0, 0.70710))
    (90, 0, 0)
    """
    quat = OpenMaya.MQuaternion(*rotation)
    euler_rotation = quat.asEulerRotation()
    euler_rotation.reorderIt(EULER_ROTATION_ORDER[rotation_order])

    return euler_rotation.x * 180.0 / math.pi, euler_rotation.y * 180.0 / math.pi, euler_rotation.z * 180.0 / math.pi


def get_local_matrix_without_joint_orient(transform_name: str) -> List[float]:
    """
    Removes the joint orient from the local matrix if the transform is a joint
    """
    if cmds.objectType(transform_name) == "joint":
        joint_orient_matrix_list = compose_matrix(
            position=(0.0, 0.0, 0.0),
            rotation=cmds.getAttr(f"{transform_name}.jointOrient")[0],
            scale=(1.0, 1.0, 1.0),
        )
        joint_orient_matrix = OpenMaya.MMatrix()
        OpenMaya.MScriptUtil.createMatrixFromList(joint_orient_matrix_list, joint_orient_matrix)
        inverse_joint_orient_matrix = joint_orient_matrix.inverse()

        object_space_matrix_list = cmds.xform(transform_name, query=True, matrix=True, objectSpace=True)
        object_space_matrix = OpenMaya.MMatrix()
        OpenMaya.MScriptUtil.createMatrixFromList(object_space_matrix_list, object_space_matrix)

        m = object_space_matrix * inverse_joint_orient_matrix
        _, rotation, _ = decompose_matrix(m)
        translation, _, scale = decompose_matrix(object_space_matrix_list)

        return list(compose_matrix(translation, rotation, scale))

    matrix: List[float] = cmds.xform(transform_name, query=True, matrix=True, objectSpace=True)
    return matrix


def is_connected_to_array(attribute: str, array_attr: str) -> Optional[int]:
    """
    Check if the attribute is connected to the specified array
    :param attribute :type str: attribute
    :param array_attr :type str array attribute
    :return :type int or None: int of index in the array or None
    """
    try:
        indices: List[int] = cmds.getAttr(array_attr, multiIndices=True) or []
    except ValueError:
        return None
    for i in indices:
        attr = f"{array_attr}[{i}]"
        if attribute in (cmds.listConnections(attr, plugs=True) or []):
            return i
    return None


def get_next_available_index_in_array(attribute: str) -> int:
    """
    Get the next available index
    """
    indices = cmds.getAttr(attribute, multiIndices=True) or []
    for i, index in enumerate(indices):
        if index != i and i not in indices:
            indices.append(i)

    indices.sort()
    attrs = [f"{attribute}[{i}]" for i in indices]
    connections = [cmds.listConnections(attr, plugs=True) or [] for attr in attrs]
    target_index = len(indices)
    for index, conn in enumerate(connections):
        if not conn:
            target_index = index
            break
    return target_index


def message_connect(from_attribute: str, to_attribute: str, in_array: bool = False, out_array: bool = False) -> None:
    """
    Create and connect a message attribute between two nodes
    """
    # Generate the object and attr names
    from_object, from_attribute_name = from_attribute.split(".", 1)
    to_object, to_attribute_name = to_attribute.split(".", 1)

    # If the attributes don't exist, create them
    if not cmds.attributeQuery(from_attribute_name, node=from_object, exists=True):
        cmds.addAttr(from_object, longName=from_attribute_name, attributeType="message", multi=in_array)
    if not cmds.attributeQuery(to_attribute_name, node=to_object, exists=True):
        cmds.addAttr(to_object, longName=to_attribute_name, attributeType="message", multi=out_array)
    # Check that both attributes, if existing are message attributes
    for a in (from_attribute, to_attribute):
        if cmds.getAttr(a, type=1) != "message":
            raise exceptions.MessageConnectionError(
                f"Message Connect: Attribute {a} is not a message attribute. CONNECTION ABORTED."
            )
    # Connect up the attributes
    try:
        if in_array:
            from_attribute = f"{from_attribute}[{get_next_available_index_in_array(from_attribute)}]"

        if out_array:
            to_attribute = f"{to_attribute}[{get_next_available_index_in_array(to_attribute)}]"

        cmds.connectAttr(from_attribute, to_attribute, force=True)
    except Exception:
        LOG.error(traceback.format_exc())


def connect_attr(from_attr: str, to_attr: str) -> None:
    if not cmds.isConnected(from_attr, to_attr):
        cmds.connectAttr(from_attr, to_attr)


def get_attr(attr_name: str, as_value: bool = True) -> Any:
    """
    Get the specified attribute
    :param attr_name :type str: attribute name i.e node.translate
    :param as_value :type bool: return as value or connected plug name
    :return :type list or any: either returns a list of connections or the value of the attribute
    """
    # Check if the attribute is connected
    connections = cmds.listConnections(attr_name, plugs=True)
    if connections and not as_value:
        # If the attribute is connected and we don't want the value, return the connections
        return connections
    elif as_value:
        # Return the value
        return cmds.getAttr(attr_name)


def get_attr_array(attr_name: str, as_value: bool = True) -> List[Any]:
    """
    Get the specified array attr
    :param attr_name :type str: attribute name i.e node.translate
    :param as_value :type bool: return as value or connected plug name
    :return :type list or any: either returns a list of connections or the value of the attribute
    """
    # Get the number of indices in the array
    indices = cmds.getAttr(attr_name, multiIndices=True) or []
    # Empty list to store the connected plugs
    connected_plugs = []
    # Empty list to store values
    values = []
    # Iterate through the indices
    for i in indices:
        # Get all the connected plugs for this index
        connections = cmds.listConnections(f"{attr_name}[{i}]", plugs=True)
        # If we want the plugs and not values, store connections
        if connections and not as_value:
            connected_plugs.extend(connections)
        # If we want values, get the value at the index
        elif as_value:
            values.append(cmds.getAttr(f"{attr_name}[{i}]"))
    # Return plugs or values, depending on which one has data
    return connected_plugs or values


def set_attr_or_connect(
    source_attr_name: str, value: Any, attr_type: Optional[str] = None, output: bool = False
) -> None:
    """
    Set an attribute or connect it to another attribute
    :param source_attr_name :type str: attribute name
    :param value : type any: value to set the attribute to
    :param attr_type :type str: name of the attribute type i.e matrix
    :param output :type bool: is this plug an output (True) or input (False)
    """
    # Type conversion from maya: python
    attr_types = {"matrix": list}
    if attr_type:
        # Check if we have a matching type
        matching_type = attr_types.get(attr_type)
        # If we have a matching type and the value matches that type, set the attr
        if matching_type is not None and isinstance(value, matching_type):
            cmds.setAttr(source_attr_name, value, type=attr_type)
    # If the value is a string and no type is matched, we want to connect the attributes
    elif isinstance(value, str):
        try:
            # Connect from left->right depending on if the source is output or input
            if output:
                if not cmds.isConnected(source_attr_name, value):
                    cmds.connectAttr(source_attr_name, value)
            else:
                if not cmds.isConnected(value, source_attr_name):
                    cmds.connectAttr(value, source_attr_name)
        except Exception:
            raise exceptions.PoseEditorAttributeError(
                "Unable to {direction} {input} to '{output}'".format(
                    direction="connect" if value else "disconnect",
                    input=source_attr_name if output else value,
                    output=value if output else source_attr_name,
                )
            )
    else:
        cmds.setAttr(source_attr_name, value)


def disconnect_attr(attr_name: str, array: bool = False) -> None:
    """
    Disconnect the specified attribute
    :param attr_name :type str: attribute name to disconnect
    :param array :type bool: is this attribute an array?
    """
    attrs: List[str] = []
    # If we are disconnecting an array, get the names of all the attributes
    if array:
        attrs.extend(cmds.getAttr(attr_name, multiIndices=True) or [])
    # Otherwise append the attr name specified
    else:
        attrs.append(attr_name)
    # Iterate through all the attrs listed
    for attr in attrs:
        # Find their connections and disconnect them
        for plug in cmds.listConnections(attr, plugs=True) or []:
            cmds.disconnectAttr(attr, plug)


def get_selection(_type: str = "") -> List[str]:
    """
    Returns the current selection
    """
    selection: List[str] = cmds.ls(selection=True, type=_type)
    return selection


def set_selection(selection_list: List[str]) -> None:
    """
    Sets the active selection
    """
    cmds.select(selection_list, replace=True)


def recalculate_vtx_normals(mesh: str) -> None:
    """
    Recalculates the vertex normals for the specified mesh
    """
    try:
        # Unlock vertex normals
        cmds.polyNormalPerVertex(mesh, unFreezeNormal=True)
        # Soften all edges to recalculate smooth normals
        cmds.polySoftEdge(mesh, a=180, ch=False)
        # delete history
        cmds.bakePartialHistory(mesh, prePostDeformers=True, allShapes=True)
    except Exception:
        LOG.error(traceback.format_exc())
