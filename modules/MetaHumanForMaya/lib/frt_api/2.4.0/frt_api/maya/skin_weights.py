# Copyright Epic Games, Inc. All Rights Reserved.

import re
import logging
from typing import Any, List

import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
from maya import mel, cmds

from ..maya.core import BaseHandler
from ..model.skin_weights import MayaSkinWeights
from ..model.maya.symmetry import MayaVtxPair, MayaSymmetryInfo

logger = logging.getLogger("frt_api.maya.skin_weights")


class SkinWeightsMayaHandler(BaseHandler):
    """
    Skin weights Maya handler.

    Contains methods for manipulation with skin weights and split maps in scene.
    @see BaseHandler
    """

    def __init__(self):
        super().__init__()

    def get_skin_cluster(self, obj_name):
        """
        Gets skin cluster object for given object pattern.

        @param object_name: Object pattern. (string)
        @return Skin cluster object. (SkinCluster)
        """

        skin_cluster = None
        skin_cluster_name = mel.eval("findRelatedSkinCluster " + obj_name)
        if skin_cluster_name:
            skin_cluster = skin_cluster_name
        return skin_cluster

    def get_skin_cluster_influence(self, skin_cluster):
        """
        Gets skin cluster influence joint names.

        This method is implemented because of differences in API in
        Maya 2009 and Maya 2012 for method skinCluster.getInfluence().
        Maya 2009 returns list of strings representing joint names.
        Maya 2012 returns list of Joint objects.
        This method should be called, and it returns list of strings
        representing joint names, like in Maya 2009.
        @param skinCluster: Skin cluster object. (SkinCluster)
        @return List of joint names. (string[])
        """

        influences = cmds.skinCluster(skin_cluster, q=True, inf=True)
        if influences and (not isinstance(influences[0], bytes) and not isinstance(influences[0], str)):
            influences = [obj.name() for obj in influences]
        return influences

    def create_skin_cluster(self, influences, mesh, skin_cluster_name, max_influences=4, skinning_method=0):
        """
        Creates skin cluster deformer for given list of joints and mesh.

        @param influences: List of influence objects. (DagNode[] or string[])
        @param mesh: Mesh for which is created skin cluster. (DagNode or string)
        @param skinClusterName: Newly created skin cluster pattern. (string)
        @param maximumInfluences: Maximum number of influences per vertex. (int)
        @param skinning_method: Skinning method, linear, dual quaternion... (int)
        @return Skin cluster object. (SkinCluster)
        """

        cmds.select(influences[0], replace=True)
        cmds.select(mesh, add=True)
        skin_cluster = cmds.skinCluster(
            toSelectedBones=True,
            name=skin_cluster_name,
            maximumInfluences=max_influences,
            skinMethod=skinning_method,
            obeyMaxInfluences=True,
        )
        if len(influences) > 1:
            cmds.skinCluster(skin_cluster, edit=True, addInfluence=influences[1:], weight=0.0)
        return skin_cluster

    # ---------------------------
    # Scene skin weights methods
    # ---------------------------
    def get_skin_weights_data(self, mesh_name):
        """
        Gets mesh Maya node and skin cluster for given mesh.

        @param mesh_name: Mesh pattern. (string)
        @return Mesh node object and skin cluster object. ([DagNode, SkinCluster])
        @throws  MayaSceneError: If unable to find unique mesh and its skin cluster.
        """

        # find mesh
        mesh_node = self.get_object(mesh_name, type="transform", root=False, strict=True)
        if not mesh_node or not cmds.objectType(mesh_node, isType="transform"):
            raise RuntimeWarning(f"Unable to find mesh: {mesh_name}")

        # find skinCluster
        skinCluster = self.get_skin_cluster(mesh_name)
        if not skinCluster:
            raise RuntimeWarning(f"Unable to find skin for given mesh: {mesh_name}")
        return (mesh_node, skinCluster)

    def get_skin_weights_from_scene(self, mesh_name):
        """
        Gets skin weights data from scene.

        @param mesh_name: Mesh pattern to work with. (string)
        @return Skin weights data. (maya.node.MayaSkinWeights)
        @throws MayaSceneError: If unable to find mesh or skin cluster.
        """

        logger.debug("Get skin weights for mesh: " + mesh_name)
        skin_cluster_name = self.get_skin_weights_data(mesh_name)[1]
        skin_weights = MayaSkinWeights()

        # joints
        skin_weights.no_of_influences = cmds.skinCluster(
            skin_cluster_name, q=True, maximumInfluences=True
        )  # .getMaximumInfluences()
        skin_weights.skinning_method = cmds.skinCluster(skin_cluster_name, q=True, skinMethod=True)  # .getSkinMethod()
        skin_weights.joints = self.get_skin_cluster_influence(skin_cluster_name)

        # weights
        # .getWeights(mesh_name + ".vtx[:]")
        vertex_count = cmds.polyEvaluate(mesh_name, v=True)

        sel_list = om2.MSelectionList()
        sel_list.add(mesh_name)
        sel_list.add(skin_cluster_name)

        shape_dag = sel_list.getDagPath(0)
        skin_dep = sel_list.getDependNode(1)
        skin_fn = oma2.MFnSkinCluster(skin_dep)

        comp_ids = list(range(vertex_count))
        single_fn = om2.MFnSingleIndexedComponent()
        shape_comp = single_fn.create(om2.MFn.kMeshVertComponent)
        single_fn.addElements(comp_ids)

        flat_weights, inf_count = skin_fn.getWeights(shape_dag, shape_comp)

        weight_plug = skin_fn.findPlug("weights", False)
        list_plug = skin_fn.findPlug("weightList", False).attribute()

        inf_dags = skin_fn.influenceObjects()
        inf_count = len(inf_dags)
        sparse_map = {skin_fn.indexForInfluenceObject(inf_dag): i for i, inf_dag in enumerate(inf_dags)}

        for c, comp_id in enumerate(comp_ids):
            weight_plug.selectAncestorLogicalIndex(comp_id, list_plug)
            valid_ids = weight_plug.getExistingArrayAttributeIndices()

            # ignore non-valid influences
            valid_ids = set(valid_ids) & sparse_map.keys()

            vertex_weights: List[Any] = []
            skin_weights.vertices_info.append(vertex_weights)
            flat_index = c * inf_count
            for valid_id in sorted(valid_ids):
                inf_index = sparse_map[valid_id]
                if flat_weights[flat_index + inf_index]:
                    vertex_weights.append(inf_index)
                    vertex_weights.append(flat_weights[flat_index + inf_index])

        logger.debug("Get skin weights ended.")
        return skin_weights

    def setSkinWeightsToScene(self, mesh_name, skin_weights):
        """
        Sets skin weights to scene.
        This function will guess all influences are given to first influence in list for all vertices.
        Function will set only this influence to 0.0 before setting provided skin weights.
        If this is not case and current skin has some weights that don't exist in provided skin_weights,
        resulting skin after set function might not be normalized anymore.

        @param mesh_name: Mesh pattern to work with. (string)
        @param skin_weights: Skin weights data. (maya.node.MayaSkinWeights)
        @throws MayaSceneError: If unable to find unique mesh.
        """

        logger.debug("Set skin weights for mesh: " + mesh_name)
        mesh_node, skin_cluster_name = self.get_skin_weights_data(mesh_name)
        vtx_ids = range(cmds.polyEvaluate(mesh_node, vertex=True))

        # prepare mapping data
        file_joint_mapping = []
        for jointName in skin_weights.joints:
            # .indexForInfluenceObject(joint_name))
            file_joint_mapping.append(self.get_index_for_influence_object(skin_cluster_name, jointName))

        # import skin weights
        temp_str = skin_cluster_name + ".wl["
        for vtx_id in vtx_ids:
            # file vertices weights
            vtx_info = skin_weights.vertices_info[vtx_id]

            # set all skin weights to zero
            vtx_str = temp_str + str(vtx_id) + "].w["
            cmds.setAttr(vtx_str + "0]", 0.0)

            # import skin weights
            for w in range(0, len(vtx_info), 2):
                cmds.setAttr(vtx_str + str(file_joint_mapping[vtx_info[w]]) + "]", vtx_info[w + 1])
        logger.debug("Set skin weights ended.")

    def get_weights_for_joints_index(self, skin_weights, joint_index):
        values = []
        for vtxInfo in skin_weights.vertices_info:
            for ii in range(0, len(vtxInfo), 2):
                if vtxInfo[ii] == joint_index:
                    values.append(vtxInfo[ii + 1])
                    break
            else:
                values.append(0.0)
        return values

    def get_maya_skin_weights_from_split_maps(self, rig_definition, split_map_names):
        """
        Get MayaSkinWeights for given split_maps list.

        @param rig_definition: Rig definition of character we are working on. (RigDefinition)
        @param split_map_names: List of names of split maps to read into MayaSkinWeights. (string[])
        @return MayaSkinWeights object, None if unsuccessful. (maya.node.MayaSkinWeights)
        """

        character_def = rig_definition.characterDef
        if not character_def:
            return None

        msw = MayaSkinWeights()
        vertices_count = 0
        for splitMapName in split_map_names:
            split_map = rig_definition.get_split_map_by_name(splitMapName)
            split_map_list = split_map.value

            if not vertices_count:
                vertices_count = len(split_map_list)
                msw.vertices_info = [[] for i in range(vertices_count)]

            msw.joints.append(splitMapName)
            for i in range(len(split_map_list)):  # pylint: disable=consider-using-enumerate
                msw.vertices_info[i].extend([msw.no_of_influences, split_map_list[i]])

            msw.no_of_influences = msw.no_of_influences + 1

        return msw

    # ---------------------------
    # Mirror methods
    # ---------------------------
    def mirror_skin_weights(self, mesh_node, vtx_ids, mfm_infos, maya_vtx_pairs):
        """
        Mirrors skin weights asymmetric in scene.

        Mirrors all vertices for selected mesh, of just selected vertices.
        @param is_mesh_selected: Indicates whether mesh is selected. (boolean)
        @param mesh_node: Selected mesh node. (DagNode)
        @param vtx_ids: List of ids of selected vertices. (int[])
        @param mesh: Mesh whose skin is being mirrored. (Mesh)
        @param mfm_info: Mirror info. (maya.node.MayaFlipMirrorInfo)
        @return True if successfully mirrored. (boolean)
        """

        logger.debug("Mirroring skin weights for mesh: " + mesh_node)

        if not cmds.polyEvaluate(mesh_node, v=True) == len(maya_vtx_pairs.vtx_pairs):
            raise RuntimeError("Wrong symmetry mesh selected.")

        if not mfm_infos:
            raise RuntimeError("No symmetry info provided.")

        maya_skin_weights = self.get_skin_weights_from_scene(mesh_node)

        # get joint pairs
        logger.debug("Finding joint pairs for skin weights mirror.")
        joint_pairs = {}
        joint_nodes = set(maya_skin_weights.joints[:])
        for jointNode in maya_skin_weights.joints:
            joint_name = jointNode
            mirror_name = None
            for mfm_info in mfm_infos:
                mirror_name = MayaSymmetryInfo.get_joint_mirror_name(
                    joint_name, mfm_info.left_label, mfm_info.right_label, mfm_info.filter
                )
                if mirror_name:
                    break
            if mirror_name in joint_nodes:
                joint_pairs[joint_name] = mirror_name
                joint_pairs[mirror_name] = joint_name

        # create mirror map
        joint_indices = {joint_name: i for i, joint_name in enumerate(maya_skin_weights.joints)}
        mirror_map = list(range(len(maya_skin_weights.joints)))
        for i, joint_name in enumerate(maya_skin_weights.joints):
            if joint_name in joint_pairs:
                mirror_map[i] = joint_indices[joint_pairs[joint_name]]

        # select side
        side = (
            MayaVtxPair.SIDE_LEFT
            if mfm_infos[0].mirror_direction == MayaSymmetryInfo.LEFT_TO_RIGHT
            else MayaVtxPair.SIDE_RIGHT
        )

        # mirror skin weights
        vtx_ids_set = set(vtx_ids)
        for i, (vi, vertex_pair) in enumerate(zip(maya_skin_weights.vertices_info, maya_vtx_pairs.vtx_pairs)):
            if i in vtx_ids_set:
                if vertex_pair.side == side:
                    for pairId in vertex_pair.pairs:
                        new_vi = vi[:]
                        for ii in range(0, len(new_vi), 2):
                            if maya_skin_weights.joints[new_vi[ii]] in joint_pairs:
                                new_vi[ii] = joint_indices[maya_skin_weights.joints[mirror_map[new_vi[ii]]]]
                        maya_skin_weights.vertices_info[pairId] = new_vi

        # writing
        self.set_skin_weights_to_scene(mesh_node, maya_skin_weights)

        logger.debug("Mirroring skin weights finished.")

    def get_index_for_influence_object(self, skin_cluster_name, joint_name):
        sel = om2.MGlobal.getSelectionListByName(skin_cluster_name)
        skin_node = sel.getDependNode(0)
        skin_cluster = oma2.MFnSkinCluster(skin_node)
        influence_dags = skin_cluster.influenceObjects()
        inf_dag = [i.partialPathName() for i in influence_dags]
        return inf_dag.index(joint_name)

    def set_skin_weights_to_scene(self, mesh_name, skin_weights):
        influences_count = len(skin_weights.joints)
        # zero all influences
        single_w = [0.0] * influences_count * len(skin_weights.vertices_info)
        for vtx_id, vtx_info in enumerate(skin_weights.vertices_info):
            for i, jnt_index in enumerate(vtx_info[::2]):
                single_w[vtx_id * influences_count + jnt_index] = vtx_info[i * 2 + 1]
        single_weights = om2.MDoubleArray(single_w)

        # get shape
        mesh_path = om2.MSelectionList().add(mesh_name).getDagPath(0)

        # Find the skin cluster connected to the mesh
        skin_cluster_name = cmds.ls(cmds.listHistory(mesh_name), type="skinCluster")[0]
        skin_cluster = oma2.MFnSkinCluster(om2.MSelectionList().add(skin_cluster_name).getDependNode(0))

        inf_dags = skin_cluster.influenceObjects()
        inf_index = om2.MIntArray()
        for x in range(len(inf_dags)):
            inf_index.append(int(skin_cluster.indexForInfluenceObject(inf_dags[x])))

        # get influences
        component = om2.MFnSingleIndexedComponent()
        vertex_comp = component.create(om2.MFn.kMeshVertComponent)
        indices = [int(re.findall(r"\d+", vert)[-1]) for vert in cmds.ls(f"{mesh_name}.vtx[*]", fl=1)]
        component.addElements(indices)
        cmds.setAttr(f"{skin_cluster_name}.normalizeWeights", 0)
        skin_cluster.setWeights(mesh_path, vertex_comp, inf_index, single_weights, False)
        cmds.setAttr(f"{skin_cluster_name}.normalizeWeights", 1)
