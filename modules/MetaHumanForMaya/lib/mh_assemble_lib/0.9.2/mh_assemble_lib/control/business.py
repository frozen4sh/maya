# Copyright Epic Games, Inc. All Rights Reserved.
import logging

from mh_assemble_lib.common import DNAReaderException
from mh_assemble_lib.control.form import LodForm, MeshForm, ProcessForm, MeshLayoutForm
from mh_assemble_lib.model.dnalib import DNA, Layer, DNAReader
from mh_assemble_lib.control.handler_api import Handler


class Controller:
    """
    Controller in MVC model.

    Forwards calls from Viewer to corresponding handler which builds MetaHuman.
    Reads and owns DNA file data.
    Handler instance depends on application context.
    """

    def __init__(self, handler: Handler):
        self._handler: Handler = handler
        self._dna: DNA = None

    def get_mesh_layout_form(self, dna_file_path: str) -> MeshLayoutForm:
        """Return MeshLayoutForm which is used to populate UI elements."""
        dna: DNA = None
        mesh_layout_form = MeshLayoutForm()
        try:
            # read dna definition
            dna = DNAReader.read(dna_file_path, Layer.definition)
        except DNAReaderException as e:
            logging.error(f"DNA Reader Error: {e}")
        else:
            # build MeshTreeListForm
            mesh_names = [dna.get_mesh_name(i) for i in range(dna.get_mesh_count())]
            for lod_id in range(dna.get_lod_count()):
                lod = LodForm(lod_id)
                mesh_layout_form.add_lod(lod)
                for i in dna.get_mesh_indices_for_lod(lod_id):
                    mesh = MeshForm(i, mesh_names[i])
                    lod.add_mesh(mesh)
        return mesh_layout_form

    def build_mh(self, form: ProcessForm) -> None:
        """Build MetaHuman for given form parameters."""
        logging.info(f"Building MH. {form}")
        form.set_progress("Reading DNA file...", 10)
        self._read_dna(form.dna_path, Layer.all)
        self._handler.set_state(self._dna, form)
        self._handler.build_mh()

    def _read_dna(self, dna_file_path: str, layer: Layer) -> None:
        if self._dna is None or self._dna.path != dna_file_path:
            self._dna = DNAReader.read(dna_file_path, layer)
