# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import Tuple
from pathlib import Path

import dnacalib2 as dnacalib

# External
from dna import FileStream, DataLayer_All, BinaryStreamReader, BinaryStreamWriter

# Internal
from mh_pose_editor.model import exceptions


def calculate_rotation_vector(source_up_axis: str, destination_up_axis: str):
    if source_up_axis == destination_up_axis:
        return [0.0, 0.0, 0.0]
    if source_up_axis == "y":
        if destination_up_axis == "z":
            return [90.0, 0.0, 0.0]
    elif source_up_axis == "z":
        if destination_up_axis == "y":
            return [-90.0, 0.0, 0.0]
    raise exceptions.PoseEditorException(
        f"Unsupported up axis combination, from {source_up_axis} to {destination_up_axis}"
    )


def orient_dna(dna_file_path: Path, selected_up_axis: str) -> Tuple[Path, bool]:
    stream = FileStream(dna_file_path.as_posix(), FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
    reader = BinaryStreamReader(stream, DataLayer_All)
    reader.read()
    coordinate_system = reader.getCoordinateSystem()

    if coordinate_system.yAxis == 2:
        dna_up_axis = "y"
    elif coordinate_system.zAxis == 2:
        dna_up_axis = "z"
    else:
        dna_up_axis = "x"
    if selected_up_axis == "dna":
        up_axis = dna_up_axis
    else:
        up_axis = selected_up_axis
    if up_axis not in ["y", "z"]:
        raise exceptions.PoseEditorException(
            "Wrong coordinate system specified in the provided MetaHuman DNA, Y-up and Z-up supported."
        )

    rotation_vector = calculate_rotation_vector(dna_up_axis, up_axis)

    if rotation_vector == [0.0, 0.0, 0.0]:
        # Return original path, ensure the caller knows that the path isn't temporary
        return dna_file_path, False

    dna_calib_reader = dnacalib.DNACalibDNAReader(reader)
    rotate_command = dnacalib.RotateCommand(rotation_vector, [0.0, 0.0, 0.0])
    rotate_command.run(dna_calib_reader)

    temp_dna_file_path = dna_file_path.parent / f"{dna_file_path.stem}_{selected_up_axis}Up.dna"
    stream = FileStream(temp_dna_file_path.as_posix(), FileStream.AccessMode_Write, FileStream.OpenMode_Binary)
    writer = BinaryStreamWriter(stream)
    writer.setFrom(dna_calib_reader)
    writer.write()

    # Return temp path and ensure the caller knows the path is temporary
    return temp_dna_file_path, True
