# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om

from .mayautil import getDagNode


def getMeshNode(node):
    if isinstance(node, om.MFnMesh):
        return node
    
    dagNode = getDagNode(node)
    if dagNode and dagNode.object().hasFn(om.MFn.kMesh):
        return om.MFnMesh(dagNode.dagPath())
    return None


def getMeshVertices(node, space=om.MSpace.kObject):
    mesh = getMeshNode(node)
    if mesh is not None:
        return [val for vtx in mesh.getPoints(space=space) for val in [vtx.x, vtx.y, vtx.z]]
    else:
        return None

def getMeshTopology(node):
    mesh = getMeshNode(node)
    if mesh is not None:
        polygons, vtxIDs = mesh.getVertices()
        return [x for x in polygons], [x for x in vtxIDs]
    else:
        return None, None