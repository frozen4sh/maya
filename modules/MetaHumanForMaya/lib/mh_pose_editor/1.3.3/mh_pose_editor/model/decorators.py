# Copyright Epic Games, Inc. All Rights Reserved.

# External
from maya import cmds

# Internal
from mh_pose_editor.log import LOG


def deprecated(message: str):
    """
    Wraps the specified function with a deprecation warning
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            cmds.warning(message)
            LOG.warning(message)
            return func(*args, **kwargs)

        return wrapper

    return decorator
