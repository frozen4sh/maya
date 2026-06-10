# Copyright Epic Games, Inc. All Rights Reserved.
from pathlib import Path

from maya import cmds

from . import logger

# Load Alembic Plugins
cmds.loadPlugin("AbcExport", quiet=True)


def abc_export(
    filepath,
    nodes=None,
    start_frame=1,
    end_frame=1,
    user_attributes=None,
    attributes=None,
    attr_prefix=None,
    no_normals=False,
    strip_namespaces=False,
    data_format="Ogawa",
    uv_write=False,
    world_space=False,
    write_visibility=False,
):
    """
    Exports Maya nodes as Alembic

    :param nodes: List of nodes to export. If None, all nodes will be exported.
    :param attributes: List of user defined attributes to export.
    """

    job_command = f"-frameRange {start_frame} {end_frame} "
    job_command += f"-dataFormat {data_format} "

    if no_normals:
        job_command += "-noNormals "

    if uv_write:
        job_command += "-uvWrite "

    if world_space:
        job_command += "-worldSpace "

    if write_visibility:
        job_command += "-writeVisibility "

    if strip_namespaces:
        job_command += "-stripNamespaces "

    # GeomParam
    if attributes:
        for attr in attributes:
            job_command += f"-attr {attr} "

    if user_attributes:
        for user_attr in user_attributes:
            job_command += f"-userattr {user_attr} "

    if attr_prefix:
        job_command += f"-attrPrefix {attr_prefix} "

    if nodes:
        for node in nodes:
            job_command += f"-root {node} "

    filepath = Path(filepath.strip())
    if filepath.suffix.lower() != ".abc":
        filepath = filepath.with_suffix(".abc")
    job_command += f"-file '{filepath.as_posix()}' "

    logger.info(job_command)
    cmds.AbcExport(verbose=True, j=job_command)
