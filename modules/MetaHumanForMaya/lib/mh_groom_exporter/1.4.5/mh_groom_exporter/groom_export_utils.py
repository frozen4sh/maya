# Copyright Epic Games, Inc. All Rights Reserved.
import os

from maya import OpenMaya, cmds

from . import timer
from .config import CONFIG
from .mesh_utils import find_closest_uv_point
from .scene_utils import save_scene, import_scene
from .attribute_utils import create_attribute
from .alembic_exporter import abc_export

# ----------------------------------------------------------------------------------------------


@timer
def add_id_attribute(group_id_list):
    """
    Add per-hair attribute:
        - groom_id
    """

    if not isinstance(group_id_list, list):
        raise TypeError("Must be a list")

    #
    attr_name = CONFIG["attribute"]["id"]["name"]
    data_type = CONFIG["attribute"]["id"]["maya_data_type"]
    abc_geom_scope = CONFIG["attribute"]["id"].get("abc_geom_scope", None)
    abc_type = CONFIG["attribute"]["id"].get("abc_type", None)

    offset = 0
    for curves_group in group_id_list:
        curve_shapes = cmds.listRelatives(curves_group, shapes=True, noIntermediate=True)
        values = range(offset, offset + len(curve_shapes))

        create_attribute(
            curves_group, attr_name, data_type, value=values, abc_geom_scope=abc_geom_scope, abc_type=abc_type
        )

        offset += len(curve_shapes)


@timer
def add_root_uv_attribute(curves_group, mesh_node, uv_set="map1"):
    """
    Adds per-hair attributes:
        - groom_root_uv
    """

    attr_name = CONFIG["attribute"]["root_uv"]["name"]
    data_type = CONFIG["attribute"]["root_uv"]["maya_data_type"]
    abc_geom_scope = CONFIG["attribute"]["root_uv"].get("abc_geom_scope", None)
    abc_type = CONFIG["attribute"]["root_uv"].get("abc_type", None)

    if not cmds.objExists(mesh_node):
        raise RuntimeError(f'Invalid mesh: "{mesh_node}"')

    # get curves in group
    curve_shapes = cmds.listRelatives(curves_group, shapes=True, noIntermediate=True)

    # get roots
    points = list()
    for curve_shape in curve_shapes:
        point = cmds.pointPosition(f"{curve_shape}.cv[0]", world=True)
        points.append(point)

    # find uvs
    all_values = list()
    uvs = find_closest_uv_point(points, mesh_node, uv_set=uv_set, uv_set_fallBack=True)  # lax with uv_set name
    for u, v in uvs:
        all_values.append([u, v, 0])

    create_attribute(
        curves_group, attr_name, data_type, value=all_values, abc_geom_scope=abc_geom_scope, abc_type=abc_type
    )


@timer
def create_top_group():
    """
    Groups all nurbs-curves under one single group.
    """

    # get group names
    top_group_name = CONFIG["top_group"]
    if cmds.objExists(top_group_name):
        raise RuntimeError(f'Invalid group name. Already existing a node called: "{top_group_name}"')

    # create top group
    top_group = cmds.createNode("transform", name=top_group_name)

    # ----------------------------------------------------------------------------------------------
    maya_version = cmds.about(version=True)

    # major
    attr_name = CONFIG["user_attribute"]["version_major"]["name"]
    data_type = CONFIG["user_attribute"]["version_major"]["maya_data_type"]
    create_attribute(top_group, attr_name, data_type, value=1)

    # minor
    attr_name = CONFIG["user_attribute"]["version_minor"]["name"]
    data_type = CONFIG["user_attribute"]["version_minor"]["maya_data_type"]
    create_attribute(top_group, attr_name, data_type, value=4)

    # tool
    attr_name = CONFIG["user_attribute"]["tool"]["name"]
    data_type = CONFIG["user_attribute"]["tool"]["maya_data_type"]
    create_attribute(top_group, attr_name, data_type, value=f"Maya {maya_version}")

    # properties
    attr_name = CONFIG["user_attribute"]["properties"]["name"]
    data_type = CONFIG["user_attribute"]["properties"]["maya_data_type"]
    create_attribute(top_group, attr_name, data_type, value="AbcExport -frameRange 1 1 -dataFormat otawa -root groom")

    return top_group


@timer
def create_guides_group(parent=None):
    guides_group_name = CONFIG["guides_group"]
    if cmds.objExists(guides_group_name):
        raise RuntimeError(f'Invalid group name. Already existing a node called: "{guides_group_name}"')

    guides_group = cmds.createNode("transform", name=guides_group_name, parent=parent)

    return guides_group


@timer
def create_curves_group(parent=None):
    curves_group_name = CONFIG["curves_group"]
    if cmds.objExists(curves_group_name):
        raise RuntimeError(f'Invalid group name. Already existing a node called: "{curves_group_name}"')

    curves_group = cmds.createNode("transform", name=curves_group_name, parent=parent)

    return curves_group


@timer
def create_group_id(curve_shapes, id_, name_=None, parent=None, run_checks=False, isGuide=False):
    """ """

    if not isinstance(id_, int):
        raise TypeError(f"Invalid id value provided: {id_}. Must be an int")
    if id_ < 0:
        raise ValueError("Invalid group_id value. Must be zero or greater")

    # create group
    group_name = f"group_id_{id_}"

    group = cmds.createNode("transform", name=group_name, parent=parent)
    curve_shapes = __parent_curves(group, curve_shapes=curve_shapes, run_checks=run_checks)

    # forces Maya's alembic to export curves as one group.
    # @ref: https://github.com/alembic/alembic/issues/164
    create_attribute(group, "riCurves", "bool", True)

    # add group_id attribute
    attr_name = CONFIG["attribute"]["group_id"]["name"]
    data_type = CONFIG["attribute"]["group_id"]["maya_data_type"]
    abc_geom_scope = CONFIG["attribute"]["group_id"].get("abc_geom_scope", None)
    abc_type = CONFIG["attribute"]["group_id"].get("abc_type", None)
    create_attribute(group, attr_name, data_type, value=id_, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    # add group_name attribute
    attr_name = CONFIG["attribute"]["group_name"]["name"]
    data_type = CONFIG["attribute"]["group_name"]["maya_data_type"]
    abc_geom_scope = CONFIG["attribute"]["group_name"].get("abc_geom_scope", None)
    abc_type = CONFIG["attribute"]["group_name"].get("abc_type", None)
    if name_:
        create_attribute(group, attr_name, data_type, value=name_, abc_geom_scope=abc_geom_scope, abc_type=abc_type)
    else:
        create_attribute(group, attr_name, data_type, value=str(id_), abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    if isGuide:
        # Add groom_guide attribute.
        attr_name = CONFIG["attribute"]["guide"]["name"]
        data_type = CONFIG["attribute"]["guide"]["maya_data_type"]
        abc_geom_scope = CONFIG["attribute"]["guide"].get("abc_geom_scope", None)
        abc_type = CONFIG["attribute"]["guide"].get("abc_type", None)
        create_attribute(group, attr_name, data_type, value=True, abc_geom_scope=abc_geom_scope, abc_type=abc_type)

    return group, curve_shapes


@timer
def __parent_curves(group, curve_shapes=None, run_checks=False):
    """
    Groups all nurbs-curves under given group.
    """

    if curve_shapes is None:
        curve_shapes = cmds.ls(type="nurbsCurve")

    # check degree / width
    # NOTE: this EXTREMELY slows down the exporting.
    if run_checks:
        # you cant have different degree curves under same AbcGeom.ICurves
        # @ref: https://github.com/alembic/alembic/blob/d36688f4eaa49b4837bb76bec6ffb5f225a160fd/maya/AbcExport/AbcWriteJob.cpp
        width_types = set()
        degrees = set()
        for curve_shape in curve_shapes:
            # check degree
            degree = cmds.getAttr(f"{curve_shape}.degree")
            degrees.add(degree)

            # check width
            if cmds.objExists(f"{curve_shape}.width"):
                type_ = cmds.getAttr(f"{curve_shape}.width", type=True)
                width_types.add(type_)

        # check degress
        if len(degrees) > 1:
            raise RuntimeError("Curves have different degrees or close states. Unable to write out as curve group")

        # check if curves under same group have different width ?
        if len(width_types) > 1:
            raise RuntimeError("Curves have different width data-type. Unable to write out as curve group")

    # make name unique
    for i, curve_shape in enumerate(curve_shapes):
        curve_shapes[i] = cmds.rename(curve_shape, "curve#")

    # parent curves
    curve_shapes = parent_objects(curve_shapes, group)

    return curve_shapes


@timer
def transform_group(group_name, scale=1, scene_up_axis="Y"):
    """
    Transforms group to Z-Up
    """

    # If scene is Y, flip Y by Z
    if scene_up_axis == "Y":
        matrix = [scale, 0, 0, 0, 0, 0, scale, 0, 0, scale, 0, 0, 0, 0, 0, 1]

    # if scene is already Z, only flip Y axis.
    elif scene_up_axis == "Z":
        matrix = [scale, 0, 0, 0, 0, -scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, 1]

    else:
        raise RuntimeError(f'Invalid Scene Up Axis: "{scene_up_axis}". Valid are: "Y" or "Z"')

    cmds.xform(group_name, matrix=matrix)

    # freeze transforms
    cmds.makeIdentity(group_name, apply=True, t=True, r=True, s=True, n=False, pn=True)


def parent_objects(objects, parent):
    """
    Parent objects using Maya API
    The command `parent -r -s` is extremely slow with hundred/thousand of objects
    """

    def as_mobject(node):
        """
        Returns node as MObject
        """
        selection_list = OpenMaya.MSelectionList()
        selection_list.add(node)

        obj = OpenMaya.MObject()
        selection_list.getDependNode(0, obj)

        return obj

    # get parent as mobjects
    mparent = as_mobject(parent)

    # parent objects
    num_objects = len(objects)
    dag_modifier = OpenMaya.MDagModifier()

    # allocate mobjects
    mobjects = OpenMaya.MObjectArray()
    mobjects.setLength(num_objects)

    for i in range(num_objects):
        mobject = as_mobject(objects[i])
        mobjects.set(mobject, i)
        dag_modifier.reparentNode(mobject, mparent)

    dag_modifier.doIt()

    # Returns paths
    new_objects = list()
    for i in range(num_objects):
        dag_node = OpenMaya.MFnDagNode(mobjects[i])
        new_objects.append(dag_node.partialPathName())

    return new_objects


# --------------------------------------------------------------------------------------------------


@timer
def import_curves(filepath):
    return cmds.ls(import_scene(filepath), type="nurbsCurve")


@timer
def export_curves(group_name, filepath):
    # NOTE: AbcExport will crash if this group is empty and 'riCurves' is True
    groups = cmds.ls(cmds.ls("*.riCurves", o=True), type="transform")
    for _group_name in groups:
        use_group = cmds.getAttr(f"{_group_name}.riCurves")
        if use_group:
            children = cmds.listRelatives(_group_name, ad=True, fullPath=True)
            curve_shapes = cmds.ls(children, type="nurbsCurve")

            if not curve_shapes:
                cmds.setAttr(f"{_group_name}.riCurves", False)

    # ----------------------------------------------------------------------------------------------
    # save temporary maya file (for debugging)
    if os.getenv("MH_GROOM_EXPORT_DEBUG"):
        save_scene()

    # user attributes
    user_attributes = [v["name"] for k, v in CONFIG["user_attribute"].items()]

    # geomArbParams to be exported
    attributes = [v["name"] for k, v in CONFIG["attribute"].items()]

    # export alembic
    abc_export(filepath, nodes=[group_name], attributes=attributes, user_attributes=user_attributes)
