# Copyright Epic Games, Inc. All Rights Reserved.

import dna
import dnacalib2 as dnacalib

from ..core import status_validator, status_validator_dna


class DNAFileHandler:
    @staticmethod
    @status_validator_dna
    def get_reader(dna_file_path):
        file_stream = dna.FileStream(dna_file_path, dna.FileStream.AccessMode_Read, dna.FileStream.OpenMode_Binary)
        reader = dna.BinaryStreamReader(file_stream)
        reader.read()
        return reader

    @staticmethod
    @status_validator([dna, dnacalib])
    def save_dna(rig_data_handler, dna_file_path: str) -> bool:
        stream = dna.FileStream(
            dna_file_path,
            dna.FileStream.AccessMode_Write,
            dna.FileStream.OpenMode_Binary,
        )

        output_reader = dnacalib.DNACalibDNAReader(rig_data_handler.dna_reader)

        rig_data_handler.rig.exportDNA(output_reader)
        writer = dna.BinaryStreamWriter(stream)
        writer.setFrom(output_reader)

        try:
            writer.write()
        except Exception:
            return False

        return True
