# Copyright Epic Games, Inc. All Rights Reserved.
"""
slist = OpenMaya.MSelectionList()
slist.add('pSphere1')
my_obj = OpenMaya.MObject()
slist.getDependNode(0, my_obj)
fn_obj = OpenMaya.MFnDependencyNode(my_obj)

fn_obj.addAttribute()

fn_numeric_attr = OpenMaya.MFnNumericAttribute()
new_attr = fn_numeric_attr.create('float2NumericAttr', 'float2NumericAttr')
"""
from maya import cmds


def create_attribute(node, name, data_type, value=None, abc_geom_scope=None, abc_type=None):
    if data_type == "float2":
        return create_float2(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "char":
        return create_char(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "short":
        return create_short(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "long":
        return create_long(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "string":
        return create_string(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "bool":
        return create_bool(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "vectorArray":
        return create_vector_array(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "floatArray":
        return create_float_array(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "doubleArray":
        return create_double_array(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    elif data_type == "Int32Array":
        return create_int_array(node, name, value=value, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    else:
        raise NotImplementedError(f'Invalid DataType: "{data_type}"')


def create_char(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    create_char('null1', 'foo', value=1)
    """
    #
    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, at="char", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        if abs(value) > 127:
            raise ValueError("Provided value over char range")

    cmds.setAttr(f"{node}.{name}", value)

    return f"{node}.{name}"


def create_short(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    create_short('null1', 'foo', value=1)
    """
    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, at="short", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        if abs(value) > 32767:
            raise ValueError("Provided value over short range")

        cmds.setAttr(f"{node}.{name}", value)

    return f"{node}.{name}"


def create_long(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    create_long('null1', 'foo', value=1)
    """
    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, at="long", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", value)

    return f"{node}.{name}"


def create_string(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    create_string('null1', 'foo', value='foo')
    """
    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, dt="string", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", value, type="string")

    return f"{node}.{name}"


def create_vector_array(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    >>> create_vector_array('null1', 'foo', value=[[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]])
    """

    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, dt="vectorArray", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", len(value), *value, type="vectorArray")

    return f"{node}.{name}"


def create_float_array(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    >>> create_float_array('null1', 'foo', value=[0.0, 1.0, 2.0])
    """

    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, dt="floatArray", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", value, type="floatArray")

    return f"{node}.{name}"


def create_double_array(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    >>> create_double_array('null1', 'foo', value=[0.0, 1.0, 2.0])
    """

    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, dt="doubleArray", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", value, type="doubleArray")

    return f"{node}.{name}"


def create_int_array(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    >>> create_int_array('null1', 'foo', value=[0, 1, 2])
    """

    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, dt="Int32Array", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", value, type="Int32Array")

    return f"{node}.{name}"


def create_bool(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    >>> create_bool('null1', 'foo', value=True)
    """

    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, at="bool", k=True)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", value)

    return f"{node}.{name}"


def create_float2(node, name, value=None, abc_geom_scope=None, abc_type=None):
    """
    >>> create_float2('null1', 'foo', value=[1.1, 2.2])
    """
    if not cmds.objExists(f"{node}.{name}"):
        cmds.addAttr(node, ln=name, at="float2", k=True)
        cmds.addAttr(node, ln=f"{name}0", at="float", p=name)
        cmds.addAttr(node, ln=f"{name}1", at="float", p=name)

    # create scope tag attr
    if abc_geom_scope is not None:
        create_string(node, f"{name}_AbcGeomScope", value=abc_geom_scope)

    # create scope tag attr
    if abc_type is not None:
        create_string(node, f"{name}_AbcType", value=abc_type)

    if value is not None:
        cmds.setAttr(f"{node}.{name}", *value, type="float2")

    return f"{node}.{name}"


# ----------------------------------------------------------------------------


def get_user_defined_attributes(nodes):
    """
    Return list of user defined attributes.

    >>> nodes = cmds.ls()
    >>> attributes = get_user_defined_attributes(nodes)
    """

    # convert to list
    if not hasattr(nodes, "__iter__"):
        nodes = [nodes]

    # get user defined attributes
    attributes = set()
    for node in nodes:
        attributes_ = cmds.listAttr(node, ud=True)
        if attributes_:
            for attr in attributes_:
                if cmds.attributeQuery(attr, node=node, numberOfChildren=True):
                    continue

                attributes.add(attr)

    return list(attributes)
