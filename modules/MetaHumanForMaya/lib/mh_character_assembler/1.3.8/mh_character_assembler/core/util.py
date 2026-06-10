# Copyright Epic Games, Inc. All Rights Reserved.
import os
from pathlib import Path

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel


class MayaUtil:
    ATTRIBUTE_NAMES = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]

    @staticmethod
    def create_workspace(maya_project_path):
        try:
            if os.path.exists(maya_project_path):
                path = Path(maya_project_path)
                cmd = 'setProject "' + path.as_posix() + '";'
                mel.eval(cmd)
        except Exception as e:
            print("Error while creating workspace:", e)

    @staticmethod
    def delete_history(mesh_names):
        for mesh_name in mesh_names:
            if cmds.objExists(mesh_name):
                cmds.select(clear=True)
                cmds.select(mesh_name)
                mel.eval('doBakeNonDefHistory( 1, {"prePost" });')

    @staticmethod
    def import_shader(shader_scene_path, mesh_shader_mapping):
        print("Importing shader scene...")
        cmds.file(shader_scene_path, options="v=0", type="mayaAscii", i=True)
        try:
            items = mesh_shader_mapping.iteritems()
        except Exception:
            items = mesh_shader_mapping.items()
        for meshName, shaderName in items:
            for lodLvl in range(0, 8):
                try:
                    # Apply shader to all meshes based on LOD level
                    resolved_mesh_name = meshName + str(lodLvl) + "_mesh"
                    shader = "shader_" + shaderName
                    cmds.select(resolved_mesh_name, replace=True)
                    mel.eval("sets -e -forceElement " + shader + "SG")
                except Exception:
                    print("Skipped adding shader for mesh %s." % meshName)

    @staticmethod
    def set_map_textures(map_infos, folder_name, prefix=""):
        for mapInfo in map_infos:
            node_name = "mapFile_" + mapInfo[0]
            if mapInfo[1]:
                node_name = prefix + "baseMapFile_" + mapInfo[0]

            if not cmds.objExists(node_name):
                continue

            MayaUtil.set_texture(folder_name, node_name)

    @staticmethod
    def set_mask_textures(masks, folder_name):
        for mask in masks:
            node_name = "maskFile_" + mask

            if not cmds.objExists(node_name):
                continue

            MayaUtil.set_texture(folder_name, node_name)

    @staticmethod
    def set_texture(folder_name, node_name):
        file_texture_name = cmds.getAttr(node_name + ".fileTextureName")
        _, texture_file_name = os.path.split(file_texture_name)
        cmds.setAttr(
            node_name + ".fileTextureName",
            os.path.join(folder_name, texture_file_name),
            type="string",
        )

    @staticmethod
    def resolve_scene_shader_paths(shaders, folder_name):
        for shader in shaders:
            node_name = "shader_" + shader
            if not cmds.objExists(node_name):
                continue
            file_shader_name = cmds.getAttr(node_name + ".shader")
            _, shader_file_name = os.path.split(file_shader_name)
            cmds.setAttr(
                node_name + ".shader",
                os.path.join(folder_name, shader_file_name),
                type="string",
            )

    @staticmethod
    def create_lights(lights_file_path, orient):
        print("Creating lights...")
        cmds.file(lights_file_path, defaultNamespace=True, i=True)

        # Set viewport 2.0 properties needed:
        model_panel_list = []
        model_editor_list = cmds.lsUI(editors=True)

        if model_editor_list:
            for my_model_panel in model_editor_list:
                if my_model_panel.find("modelPanel") != -1:
                    model_panel_list.append(my_model_panel)
                    try:
                        for modelPanel in model_panel_list:
                            cmds.modelEditor(
                                modelPanel=modelPanel,
                                lights=True,
                                displayAppearance="smoothShaded",
                                nurbsCurves=True,
                                joints=False,
                                nurbsSurfaces=True,
                                polymeshes=True,
                                textures=True,
                                dl="all",
                                useDefaultMaterial=False,
                                backfaceCulling=False,
                                displayTextures=True,
                                grid=False,
                            )
                    except Exception:
                        print("An error has occured importing lights scene!.\n")

        cmds.xform("Lights", ro=orient)
        cmds.makeIdentity("Lights", apply=True)

    @staticmethod
    def save_maya_scene(file_path, file_type="mayaAscii"):
        print(f"Saving maya scene to {file_path}.")
        cmds.file(rename=file_path)
        cmds.file(save=True, type=file_type)

    @staticmethod
    def connect_attributes_to_shader(shader_attributes_mapping):
        print("Connecting attributes to shader...")
        items = shader_attributes_mapping.items()

        for frm_attribute, shaderAttribute in items:
            if cmds.objExists(frm_attribute) and cmds.objExists(shaderAttribute):
                cmds.connectAttr(frm_attribute, shaderAttribute, force=True)

    @staticmethod
    def unlock_mesh_normals(mesh_name, seam_vertices):
        # Get MObject for the mesh
        sel = om.MSelectionList()
        sel.add(mesh_name)
        dag_path = sel.getDagPath(0)
        dag_path.extendToShape()

        mesh_fn = om.MFnMesh(dag_path)

        # Get all vertex indices
        num_vertices = mesh_fn.numVertices
        all_indices = set(range(num_vertices))

        # Get the vertices to unlock
        unlock_indices = sorted(all_indices - seam_vertices)

        # Unlock normals
        if unlock_indices:
            mesh_fn.unlockVertexNormals(unlock_indices)
        cmds.polySoftEdge(mesh_name, a=180, ch=False)
        # mel.eval('doBakeNonDefHistory( 1, {"prePost" });')
