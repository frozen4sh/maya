# Copyright Epic Games, Inc. All Rights Reserved.
from .file.reader import RDFReader
from .model.definition import RigDefinition


def get_rig_definition(rdf_file_path: str) -> RigDefinition:
    rig_definition = RigDefinition()
    reader = RDFReader(rdf_file_path, rig_definition)
    rig_definition = reader.read()
    return rig_definition
