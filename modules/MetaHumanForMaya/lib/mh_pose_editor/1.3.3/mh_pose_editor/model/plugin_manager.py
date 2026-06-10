# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import List
from collections import OrderedDict

# External
from maya import cmds

# Internal
from mh_pose_editor.model import exceptions


class PluginManager:
    """
    Class for loading latest available plugin
    """

    # The name of the recommended solver
    RECOMMENDED_SOLVER = "UERBFSolverNode"
    # Empty list to keep track of the loaded solver nodes
    LOADED_NODES: List[str] = []
    # Generate an ordered manifest of known plugin name variants with the newest plugins
    __PLUGIN_VERSIONS = OrderedDict(
        {
            f"MayaUERBFPlugin_{cmds.about(version=True)}": "UERBFSolverNode",
            f"MayaUERBFPlugin{cmds.about(version=True)}": "UERBFSolverNode",
            "MayaUERBFPlugin": "UERBFSolverNode",
        }
    )

    @staticmethod
    def load_plugin() -> List[str]:
        """
        Load any valid RBF plugins
        :return :type list: node names loaded
        """

        PluginManager.LOADED_NODES = []
        # Iterate through all the valid plugin versions and attempt to load
        for plugin_name, solver_name in PluginManager.__PLUGIN_VERSIONS.items():
            # If the plugin is already loaded, add the solver name to the list of loaded nodes
            if cmds.pluginInfo(plugin_name, q=True, loaded=True) and solver_name not in PluginManager.LOADED_NODES:
                PluginManager.LOADED_NODES.append(solver_name)
            else:
                try:
                    # Attempt to load the plugin
                    cmds.loadPlugin(plugin_name)
                    # If the solver name is not already in the list, add it
                    if solver_name not in PluginManager.LOADED_NODES:
                        PluginManager.LOADED_NODES.append(solver_name)
                # Ignore errors
                except RuntimeError:
                    pass
        # If we have no loaded nodes no plugin loaded correctly
        if not PluginManager.LOADED_NODES:
            raise exceptions.InvalidPoseEditorPlugin("Unable to load valid RBF plugin version.")

        return PluginManager.LOADED_NODES
