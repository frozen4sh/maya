# Copyright Epic Games, Inc. All Rights Reserved.


from __future__ import annotations

from typing import Tuple

import rdf
from rdf_model.file.reader import RDFReader
from rdf_model.model.definition import RigDefinition as _RigDefinition

from .helper import map_frt
from ..rig_definition.rig_definition import RigDefinition


def get_rig_definition(rdf_file_path: str) -> Tuple[RigDefinition, rdf.RigDefinitionBinaryStreamReader]:
    rig_definition = _RigDefinition()
    reader = RDFReader(rdf_file_path, rig_definition)
    reader.read()
    rdf_reader = reader.get_reader()

    return map_frt(rig_definition, rdf_reader), rdf_reader
