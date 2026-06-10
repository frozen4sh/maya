# Copyright Epic Games, Inc. All Rights Reserved.

from frt_api import ProgressEnd, ProgressStart, ProgressUpdate
from frt_api.rig import RigDataHandler, RigCalculationHandler

from mh_expression_editor.utils import general

from .base import BaseUpgradeHandler

FIX_SKINNING_MESHES_JOINTS_MAPPING = {
    "teeth_lod0_mesh": ["FACIAL_C_Tongue3"],
    "teeth_lod1_mesh": ["FACIAL_C_Tongue3"],
    "teeth_lod2_mesh": ["FACIAL_C_Tongue3"],
}


logger = general.get_logger()


class UpgradeHandler(BaseUpgradeHandler):
    INPUT_RIG_DEFINITION = "MH.4"
    INPUT_DNA_DESCRIPTION = "Unreal Engine 5.5 compatible DNA File."

    OUTPUT_RIG_DEFINITION = "MH.6"

    @staticmethod
    def get_step_count(rig):
        mesh_count = [rig.rdf_reader.getMeshExportedToRig(i) for i in range(rig.rdf_reader.getMeshCount())].count(True)
        expression_count = [
            rig.rdf_reader.getExpressionType(i) in [1, 4] for i in range(rig.rdf_reader.getExpressionCount())
        ].count(True)
        return mesh_count + expression_count

    @staticmethod
    def upgrade(resources, input_dna_file_path, output_dna_file_path):
        if UpgradeHandler.validate_inputs(resources, input_dna_file_path):
            resources.initialize_from_dna_file(input_dna_file_path)
            source_rig = RigDataHandler(
                resources.rdf_file_path,
                input_dna_file_path,
            )
            logger.info("Source rig initialized.")

            template_dna_file_path = general.resource(
                UpgradeHandler.OUTPUT_RIG_DEFINITION, UpgradeHandler.TEMPLATE_FILE_NAME
            )
            resources.initialize_from_dna_file(template_dna_file_path)
            config = general.load_json(resources.config_file_path)
            destination_rig = RigDataHandler(
                resources.rdf_file_path, template_dna_file_path, **config["pruning_threshold"]
            )
            logger.info("Destination rig initialized.")

            ProgressStart.emit(max_value=UpgradeHandler.get_step_count(destination_rig))

            for mesh in source_rig.rig_definition.meshes:
                if mesh.name in source_rig.rig_definition.get_dna_mesh_names():
                    destination_rig.set_neutral_mesh(mesh.name, source_rig.get_neutral_mesh_vertex_positions(mesh.name))
                    source_skinning = source_rig.get_maya_skin_weights(mesh.name)
                    # Fix missing joints in skin cluster
                    if mesh.name in FIX_SKINNING_MESHES_JOINTS_MAPPING:
                        for joint_name in FIX_SKINNING_MESHES_JOINTS_MAPPING[mesh.name]:
                            if joint_name not in source_skinning.joints:
                                source_skinning.joints.append(joint_name)
                                source_skinning.vertices_info[-1].append(source_skinning.joints.index(joint_name))
                                source_skinning.vertices_info[-1].append(0.0)
                    destination_rig.set_skin_weights(mesh.name, source_skinning)
                    ProgressUpdate.emit(status=f"{mesh.name} transferred")
            destination_rig.set_neutral_joints(source_rig.get_neutral_joints())

            RigCalculationHandler.calculate_neutral_mesh(destination_rig)

            for exp in source_rig.rig_definition.expressions:
                if exp.type in [1, 4]:
                    for phase_number in exp.get_phase_numbers():
                        destination_rig.set_expression_joints(
                            exp.name, phase_number, source_rig.get_expression_joints(exp.name, phase_number)
                        )
                        for mie in exp.meshes_in_expression:
                            if mie.type in [2, 3]:
                                destination_rig.set_sculpt(
                                    mie.mesh.name,
                                    exp.name,
                                    phase_number,
                                    source_rig.get_sculpt_mesh_vertex_positions(mie.mesh.name, exp.name, phase_number),
                                )
                    ProgressUpdate.emit(status=f"{exp.name} transferred")

            ProgressEnd.emit()

            RigCalculationHandler.ordered_calculation(
                destination_rig, [exp.name for exp in destination_rig.rig_definition.expressions]
            )

            RigCalculationHandler.ordered_calculation(
                destination_rig, [exp.name for exp in destination_rig.rig_definition.expressions]
            )
            logger.info(f"Saving a new MetaHuman DNA: {output_dna_file_path}.")
            destination_rig.save_rig_data_as_dna(output_dna_file_path)
            logger.info("MetaHuman DNA updated.")
