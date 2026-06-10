# Copyright Epic Games, Inc. All Rights Reserved.
from maya import mel, cmds

# Load XGen
if not cmds.pluginInfo("xgenToolkit", q=True, l=True):
    cmds.loadPlugin("xgenToolkit", quiet=True)

# Initialize XGen
# this creates global variables and so
if not mel.eval("exists xgen"):
    mel.eval('source "xgen.mel"; xgen()')

import xgenm

# --------------------------------------------------------------------------------------------------


def get_descriptions(palette=None):
    """
    Returns xGen desciptions from scene.

    :param palette: Returns descriptions for given palette. If None, all palette's descriptions will
                    be returned.
    """

    if palette:
        descriptions = list(xgenm.descriptions(palette))
        descriptions.sort()
        return descriptions
    else:
        descriptions = list()
        for palette in list(xgenm.palettes()):
            descriptions.extend(get_descriptions(palette))
        descriptions.sort()
        return descriptions


def get_guides(description=None):
    """ """

    if description:
        return list(xgenm.descriptionGuides(description))
    else:
        guides = list()
        for description in get_descriptions():
            guides.extend(get_guides(description))
        return guides


def get_bound_geometry(description):
    """
    Return mesh from given description
    """
    palette = xgenm.palette(description)
    return xgenm.boundGeometry(palette, description)


# --------------------------------------------------------------------------------------------------


def geometry_instancer_to_interactive_grooming(descriptions, prefix=None):
    """
    Converts Geometry Instancer to Interactive Grooming

    >>> descriptions = get_descriptions('head')
    >>> geometry_instancer_to_interactive_grooming(descriptions[0])
    """

    if prefix:
        interactive_descriptions = cmds.xgmGroomConvert(descriptions, prefix=prefix)
    else:
        interactive_descriptions = cmds.xgmGroomConvert(descriptions)

    # return parent transforms
    return cmds.listRelatives(interactive_descriptions, parent=True)


def guide_to_curve(guide, degree=3):  # , tag_as_guide=True, tag_attr_name='guide'):
    """
    Converts xGen Description Guide to NurbsCurve

    >>> import xgenm
    >>> palettes = xgenm.palettes()
    >>> descriptors = xgenm.descriptions(palette)
    >>> guides = list()
    >>> _ = [guides.extend(xgenm.descriptionGuides(description)) for description in descriptors]
    >>> _ = [guide_to_curve(guide) for guide in guides]
    """

    # get guide geometry data
    points = list()
    num_vertices = int(cmds.xgmGuideGeom(guide=guide, numVertices=True)[0])
    for i in range(num_vertices):
        point = cmds.pointPosition(f"{guide}.vtx[{i}]")
        points.append(point)

    # create new curve
    curve_xform = cmds.curve(degree=degree, point=points, name=f"{guide}_curve")
    curve_shape = cmds.listRelatives(curve_xform, shapes=True)[0]

    # Sets rotate and scale pivot
    cmds.xform(curve_xform, rp=points[0], sp=points[0])

    return curve_shape
