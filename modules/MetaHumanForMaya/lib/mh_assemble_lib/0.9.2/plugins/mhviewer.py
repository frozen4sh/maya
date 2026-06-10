# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om
from maya import cmds

from mh_assemble_lib import version

MENU_NAME = "MHViewer"

DEPENDENCIES = [
    "embeddedRL4.mll",
]


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


# Initialize the plug-in
def initializePlugin(plugin):
    om.MFnPlugin(plugin, "MHViewer", version, "Any")

    # Make sure dependent plugins are loaded
    for dep in DEPENDENCIES:
        if not cmds.pluginInfo(dep, query=True, loaded=True):
            cmds.loadPlugin(dep)

    # Check if the menu already exists; if so, delete it to recreate it
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)

    # Create a new menu in the Maya main menu bar
    cmds.menu(MENU_NAME, label=MENU_NAME, to=True, parent="MayaWindow")

    # Add menu items to the custom menu
    cmds.menuItem(label="MHViewer", command="import mh_assemble_lib;mh_assemble_lib.run_maya()")


# Uninitialize the plug-in
def uninitializePlugin(plugin):
    om.MFnPlugin(plugin)

    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)
