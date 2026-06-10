# Copyright Epic Games, Inc. All Rights Reserved.
from maya import cmds

from . import logger
from .xgen_utils import (
    get_guides,
    guide_to_curve,
    geometry_instancer_to_interactive_grooming,
)
from .alembic_exporter import abc_export


def export_geometry_instancer_guides(descriptions, filepath, degree=3):
    """
    >>> from xgen_utils import get_descriptions
    >>> descriptions = get_descriptions()
    >>> export_geometry_instancer_guides(descriptions, filepath)
    """

    description_guides = dict()
    for description in descriptions:
        description_guides[description] = get_guides(description)

    # Refresh Descriptions
    # NOTE: david.corral: i have experienced problems with refreshing, and data not being exported
    # properly. These issues were random and not reproducible.
    if not cmds.about(batch=True):
        cmds.xgmPreview(descriptions, progress=True)

    curve_shapes = list()
    curve_counts = dict()
    for description, guides in description_guides.items():
        description_curve_shape = list()
        for guide in guides:
            curve_shape = guide_to_curve(guide, degree=degree)
            description_curve_shape.append(curve_shape)
        curve_shapes.extend(description_curve_shape)
        curve_counts[description] = len(description_curve_shape)

    # export to alembic
    curve_xforms = cmds.listRelatives(curve_shapes, parent=True)
    abc_export(filepath, nodes=curve_xforms, start_frame=1, end_frame=1, attributes=None, attr_prefix=None)

    # delete curves
    cmds.delete(curve_xforms)

    return curve_counts


def export_geometry_instancer(descriptions, filepath):
    """
    Exports xGen Geometry Instancing to Alembic

    >>> from xgen_utils import get_descriptions
    >>> descriptions = get_descriptions()
    >>> filepath = 'C:/Users/david.corral/Documents/maya/projects/sphere_hair/scenes/temp2.abc'
    >>> export_geometry_instancer(descriptions, filepath)
    """

    # convert to interactive grooming
    interactive_descriptions = geometry_instancer_to_interactive_grooming(descriptions)

    # Refresh Descriptions
    # NOTE: david.corral: i have experienced problems with refreshing, and data not being exported
    # properly. These issues were random and not reproducible.
    if not cmds.about(batch=True):
        cmds.xgmPreview(interactive_descriptions, progress=True)

    # retrieve num of splines on a per-description basis
    spline_count = dict()
    for description_name, description in zip(descriptions, interactive_descriptions):
        spline_count[description_name] = cmds.xgmSplineQuery(description, splineCount=True)

    # export
    export_interactive_grooming(interactive_descriptions, filepath, multi_xform=False)

    # delete descriptors
    cmds.delete(interactive_descriptions)

    return spline_count


# --------------------------------------------------------------------------------------------------


def export_interactive_grooming(
    spline_descriptions,
    filepath,
    start_frame=1,
    end_frame=1,
    step=1,
    fileformat="ogawa",
    relative_sample=False,
    sample_low=-0.2,
    sample_high=0.2,
    pre_roll=False,
    pre_roll_start=0,
    pre_roll_step=1,
    multi_xform=True,
    final_width=True,
):
    '''
    Exports xGen Interactive Grooming to Alembic

    This logic has been extracted from:
        File: "C:/Program Files/Autodesk/Maya2018/plug-ins/xgen/scripts/xgmSplineCacheExport.mel"
        Proc: xgmSplineCacheExportCmd

    >>> filepath = 'C:/Users/david.corral/Documents/maya/projects/sphere_hair/scenes/temp2.abc'
    >>> export_xgm_spline(['test_layer1_splineDescription'], filepath)
    '''

    # The command xgmSplineCache does not support backlash
    filepath = filepath.replace("\\", "/")

    job_command = f" -file {filepath}"
    job_command += f" -df {fileformat}"
    job_command += f" -fr {start_frame} {end_frame}"
    job_command += f" -step {step}"

    if relative_sample:
        job_command += f" -frs {sample_low}"
        job_command += f" -frs {sample_high}"

    if pre_roll:
        job_command += " -pr"
        job_command += f" -pfs {pre_roll_start}"
        job_command += f" -ps {pre_roll_step}"

    if multi_xform:
        job_command += " -mxf"

    if final_width:
        job_command += " -wfw"

    for descriptor in spline_descriptions:
        job_command += f" -obj {descriptor}"

    logger.info(job_command)
    cmds.xgmSplineCache(export=True, j=job_command)
