# Copyright Epic Games, Inc. All Rights Reserved.
import os
import tempfile
import contextlib

from maya import mel, cmds

from . import logger

cmds.loadPlugin("fbxmaya", quiet=True)
cmds.loadPlugin("AbcImport", quiet=True)


def new_scene():
    """ """
    cmds.file(new=True, force=True)


def set_project(directory):
    """ """
    # setProject may fail in mayapy because savePrefs command is not found
    with contextlib.suppress(Exception):
        mel.eval(f'setProject "{directory}"')


def load_scene(filepath):
    """
    >>> filepath = os.path.join(directory, 'my_maya_scene.ma')
    >>> load_scene(filepath)
    """
    if not os.path.exists(filepath):
        raise OSError(f'Invalid filepath: "{filepath}"')

    if cmds.file(q=True, sn=True) != filepath:
        return cmds.file(filepath, o=True, force=True, returnNewNodes=True)


def save_scene(filepath=None):
    """ """
    if not filepath:
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, "temp.ma")

    cmds.file(rename=filepath)
    cmds.file(save=True, typ="mayaAscii")

    logger.info(filepath)


def import_scene(filepath):
    """
    >>> filepath = os.path.join(directory, 'my_maya_scene.ma')
    >>> import_scene(filepath)
    """

    if not os.path.exists(filepath):
        raise OSError(f'Invalid filepath: "{filepath}"')

    nodes = []
    try:
        nodes = cmds.file(filepath, i=True, returnNewNodes=True, ignoreVersion=True)
    except:
        raise
    finally:
        return nodes
