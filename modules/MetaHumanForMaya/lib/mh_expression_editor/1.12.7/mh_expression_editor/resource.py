# Copyright Epic Games, Inc. All Rights Reserved.

import os

from . import lib
from .utils.general import SingletonMeta, resource


class Resources(metaclass=SingletonMeta):
    def __init__(self):
        self.use_default_resources = True

        self.db_name = ""
        self.dna_file_path = ""
        self.rdf_file_path = ""

        self.config_file_path = ""

        self.graph_presets_folder_path = ""

        self.joints_matching_presets_folder_path = ""
        self.ml_joints_matching_model_description_path = ""

        self.lod_generation_model_description_path = ""

        self.gui_file_path = ""
        self.analog_gui_file_path = ""
        self.aas_file_path = ""

        self.vertex_joint_mapping_folder_path = ""

        self.vertex_color_file_path = ""
        self.body_scenes_folder_path = ""

    @staticmethod
    def reset():
        SingletonMeta.clear(Resources)

    def initialize_from_dna_file(self, dna_file_path):
        if self.use_default_resources:
            self.db_name = lib.get_db_name(dna_file_path)

            if not self.db_name:
                return False

            self.rdf_file_path = resource(self.db_name, "definition.rdf")

            self.config_file_path = resource(self.db_name, "config.json")

            self.graph_presets_folder_path = resource(self.db_name, "bookmarks", "presets")

            self.joints_matching_presets_folder_path = resource(self.db_name, "jm")
            if os.path.exists(resource(self.db_name, "jm", "ml", "model_description.json")):
                self.ml_joints_matching_model_description_path = resource(
                    self.db_name, "jm", "ml", "model_description.json"
                )
            else:
                try:
                    self.ml_joints_matching_model_description_path = os.path.join(
                        os.environ["ML_MODEL_ROOT"].split(os.pathsep)[-1], self.db_name, "model_description.json"
                    ).replace("\\", "/")
                except KeyError:
                    self.ml_joints_matching_model_description_path = ""
            if os.path.exists(resource(self.db_name, "lod_generation", "model_description.json")):
                self.lod_generation_model_description_path = resource(
                    self.db_name, "lod_generation", "model_description.json"
                )
            else:
                try:
                    self.lod_generation_model_description_path = os.path.join(
                        os.environ["LOD_GENERATION_ROOT"].split(os.pathsep)[-1], self.db_name, "model_description.json"
                    ).replace("\\", "/")
                except KeyError:
                    self.lod_generation_model_description_path = ""

            self.gui_file_path = resource(self.db_name, "rig_editing", "gui.ma")
            self.analog_gui_file_path = resource(self.db_name, "rig_editing", "analog_gui.ma")
            self.aas_file_path = resource(self.db_name, "rig_editing", "additional_assemble_script.py")

            self.vertex_joint_mapping_folder_path = resource(self.db_name, "vertex_joint_mapping")

            self.vertex_color_file_path = resource(self.db_name, "export", "vtx_color.py")
            self.body_scenes_folder_path = resource(self.db_name, "export", "body")

        self.dna_file_path = dna_file_path
        return True
