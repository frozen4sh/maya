# Copyright Epic Games, Inc. All Rights Reserved.

import os

from mh_expression_editor.utils import general

logger = general.get_logger()


class BaseUpgradeHandler:
    TEMPLATE_FILE_NAME = "template.dna"

    @classmethod
    def validate_inputs(cls, resources, input_dna_file_path):
        input_rig_definition = getattr(cls, "INPUT_RIG_DEFINITION", None)
        if input_rig_definition is None:
            raise NotImplementedError(f"{cls.__name__} must define INPUT_RIG_DEFINITION")
        output_rig_definition = getattr(cls, "OUTPUT_RIG_DEFINITION", None)
        if output_rig_definition is None:
            raise NotImplementedError(f"{cls.__name__} must define OUTPUT_RIG_DEFINITION")
        resources.initialize_from_dna_file(input_dna_file_path)
        if not os.path.exists(resources.rdf_file_path):
            if resources.db_name:
                raise RuntimeError(
                    f"Rig definition {resources.db_name} is not supported as input. Only {input_rig_definition} MetaHuman DNA files are supported"
                )
            raise RuntimeError(f"Input rig definition could not be extracted from {input_dna_file_path}")
        if not resources.db_name == input_rig_definition:
            raise RuntimeError(
                f"Rig definition {resources.db_name} is not supported as input. Only {input_rig_definition} MetaHuman DNA files are supported"
            )

        master_dna_file_path = general.resource(output_rig_definition, BaseUpgradeHandler.TEMPLATE_FILE_NAME)
        resources.initialize_from_dna_file(master_dna_file_path)
        if not os.path.exists(resources.rdf_file_path):
            if resources.db_name:
                raise RuntimeError(
                    f"Rig definition {resources.db_name} is not supported as output. Only {output_rig_definition} MetaHuman DNA files are supported"
                )
            raise RuntimeError(f"Output rig definition could not be extracted from {master_dna_file_path}")
        if not resources.db_name == output_rig_definition:
            raise RuntimeError(
                f"Rig definition {resources.db_name} is not supported as output. Only {output_rig_definition} MetaHuman DNA files are supported"
            )

        return True
