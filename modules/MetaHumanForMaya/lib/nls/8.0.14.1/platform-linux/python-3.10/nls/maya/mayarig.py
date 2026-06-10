# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

import logging

from . import mayajoint
from . import mayameshutil
from . import mayatransformutil
from . import mayautil


def getParentJoint(dag):
    '''
    @returns the next parent joint along the DAG hierarchy if any exists
    '''
    if dag is None:
        return None
    parentDag = mayautil.getDagPath(mayautil.getParent(dag))
    if parentDag and parentDag.apiType() == om.MFn.kJoint:
        return parentDag
    elif parentDag:
        return getParentJoint(parentDag)
    return None


def getAllParentJoints(jointsDag):
    '''
    @returns all joints that are in the joint hierarchy for all input joints
    '''
    jointsSet = set()
    toCheckSet = []
    for jointDag in jointsDag:
        jointsSet.add(jointDag.fullPathName())
        toCheckSet.append(jointDag)

    while len(toCheckSet) > 0:
        item = toCheckSet.pop(0)
        parent = getParentJoint(item)
        if parent:
            if parent.fullPathName() not in jointsSet:
                jointsSet.add(parent.fullPathName())
                toCheckSet.append(parent)

    allJoints = om.MDagPathArray()
    for item in jointsSet:
        allJoints.append(mayautil.getDagPath(item))

    return allJoints



def getSkinCluster(clusterName):
    '''
    Retrieves the skin cluster node of the given name
    '''
    return oma.MFnSkinCluster(mayautil.getObject(clusterName))


def getJointsDagArrayForSkinCluster(skinCluster):
    '''
    @returns the list of joints that are influence by the skin cluster
    '''
    influenceDags = skinCluster.influenceObjects()
    jointDags = om.MDagPathArray()
    for influenceDag in influenceDags:
        if influenceDag.apiType() == om.MFn.kJoint:
            jointDags.append(influenceDag)
        else:
            raise RuntimeError('currently only understand how to read joints from a skin cluster')
    return jointDags


def getWeightsForSkinClusterAndJoint(skinCluster, jointDag, jointIdx=-1):
    '''
    Returns a list of component, influence weights and vertex indices for @p skinCluster and joint @p jointDag.
    @param jointIdx  If jointIdx >= 0 then it will query the weights using the jointIdx instead of using indexForInfluenceObject.
                     The only reason to use it is that we have seen a bug where indexForInfluenceObject would return an invalid number
    '''

    # unfortunately we have observed cases where indexForInfluenceObject() returns an incorrect index. As a workaround we
    # can simply get the influence in order and pass in the index, but this may lead to errors if the joint order is not
    # correct
    jointIdxQuery = skinCluster.indexForInfluenceObject(jointDag)
    if jointIdx < 0:
        jointIdx = jointIdxQuery

    if jointIdx != jointIdxQuery:
        logging.warn('logical joint index ' + str(jointIdxQuery) + ' and input joint index ' + str(jointIdx) + ' do not match')

    shapeDagVtxIdsAndWeights = []

    # get all shapes and components that are influence by the joint
    (vertexInfluence, weights) = skinCluster.getPointsAffectedByInfluence(jointDag)

    for i in range(vertexInfluence.length()):
        # get the specific shape and component (mesh vertex list)
        (shapeDag, component) = vertexInfluence.getComponent(i)
        weights = []
        vtxList = []
        if component.apiType() == om.MFn.kMeshVertComponent:
            weights = skinCluster.getWeights(shapeDag, component, jointIdx)
            vtxList = om.MFnSingleIndexedComponent(component).getElements()
        else:
            raise RuntimeError('unsupported type ' + component.apiTypeStr() + ' for joint influence')

        if len(weights) != len(vtxList):
            raise RuntimeError('vertex list and weights do not match')

        shapeDagVtxIdsAndWeights.append((shapeDag, vtxList, weights))
        return shapeDagVtxIdsAndWeights


def MMatrixFromDict(matrixDict):
    '''
    Reads a maya transformation matrix from our custom matrix dictionary representation:
    {
        'rows' : R,
        'cols' : C,
        'data' : values stored in column major format; transformation matrices are stored as post-multiply matrices as
                 opposed to pre-multiply matrices that Maya uses.
    }
    '''
    assert('data' in matrixDict)
    assert('rows' in matrixDict)
    assert('cols' in matrixDict)
    assert(matrixDict['rows'] == 4)
    assert(matrixDict['cols'] == 4)
    # array is stored in column major, so we read in row major and would need to transpose.
    # however, in maya transformation matrices are applied as post-multiply, but we store the transformation
    # matrix as a pre-multiply matrix, and therefore the additional transpose cancels out
    return om.MMatrix(matrixDict['data'])


def MMatrixToDict(matrix):
    '''
    Saves a maya transformation matrix to our custom matrix dictionary representation:
    {
        'rows' : R,
        'cols' : C,
        'data' : values stored in column major format; transformation matrices are stored as post-multiply matrices as
                 opposed to pre-multiply matrices that Maya uses.
    }
    '''
    if not isinstance(matrix, om.MMatrix):
        raise RuntimeError('transformation matrix needs to be a 4x4 matrix')

    matrixDict = dict()
    matrixDict["rows"] = 4
    matrixDict["cols"] = 4
    # array is stored in column major, so we would need to write a transposed matrix in row major.
    # however, in maya transformation matrices are applied as post-multiply, but we store the transformation
    # matrix as a pre-multiply matrix, and therefore the additional transpose cancels out
    matrixDict["data"] = list(matrix)
    return matrixDict


def MeshToVerticesDict(meshNode, space=om.MSpace.kObject):
    '''
    Creates a vertices dictionary:
    {
        "vertices" : 3xN matrix
    }
    '''

    verticesDict = dict()

    # get all vertices
    vertices = mayameshutil.getMeshVertices(meshNode, space=space)
    if vertices is None:
        raise RuntimeError("no vertices for meshNode")
    verticesDict["vertices"] = dict()
    verticesDict["vertices"]["rows"] = 3
    verticesDict["vertices"]["cols"] = len(vertices) / 3
    verticesDict["vertices"]["data"] = vertices

    return verticesDict


def MeshToNamedGeometryDict(meshNode, outputDict=None, targetname=None, space=om.MSpace.kObject):
    '''
    Appends to or creates a named geometry dictionary:
    {
        "geometry" : {
            "name/targetname" : {
                "vertices" : 3xN matrix
            },
            ...
        },
        ...
    }
    '''

    if outputDict is None:
        outputDict = dict()

    if "geometry" not in outputDict:
        outputDict["geometry"] = dict()

    name = targetname
    if name is None:
        name = mayautil.getDagPath(meshNode).fullPathName()

    verticesDict = MeshToVerticesDict(meshNode, space=space)
    if verticesDict is None:
        dagPath = mayautil.getDagPath(meshNode)
        if dagPath is None:
            raise RuntimeError('{} does not exist, so no vertices can be extracted'.format(meshNode))
        else:
            raise RuntimeError('cannot get vertices for {}'.format(dagPath.fullPathName()))

    outputDict["geometry"][name] = verticesDict

    return outputDict


def MeshToMeshDict(meshNode, space=om.MSpace.kObject):
    '''
    Creates a mesh dictionary:
    {
        "vertices" : 3xN matrix,
        "topology" : {
            "polygons" : [3, 4, 4, 3, 3, ...]     // number of vertices per polygon
            "vtxIDs" : [0, 1, 2, 1, 3, 4, 2, ...] // the vertex ids for the polygons, len(vtxIDs) == sum(polygonCount)
        }
    }
    '''

    meshDict = dict()
    meshDict.update(MeshToVerticesDict(meshNode, space=space))
    polygons, vertexIDs = mayameshutil.getMeshTopology(meshNode)
    if polygons is None or vertexIDs is None:
        raise RuntimeError("No polygons in meshNode")

    meshDict["topology"] = dict()
    meshDict["topology"]["polygons"] = polygons
    meshDict["topology"]["vtxIDs"] = vertexIDs

    return meshDict


def SkinningToDict(skinCluster, useJointArrayIndexing=False):
    """
    Creates a dictionary with the joints, their local and world matrices, and the skin weights.
    Precondition: rig is in bind pose
    @param useJointArrayIndexing  Maya seems to have a bug where for some skinClusters the (indexForInfluenceObject) returns
                                  an incorrect index. Instead you can try using the joint array index directly.

    Format for joints and geometry:

    joints {
        "name of joint" : {

            "parent" : name of parent joint (not available means root node)
            "local": 4x4 matrix (column major, pre multiply - should be possible to calculate it from the parent)
            "world": 4x4 matrix (column major, pre multiply)
            "influence": {
                "name of geometry": {
                    "vertex indices": []
                    "vertex weights": []
                }
            }
        }
    }

    "geometry" : {
        "name of geometry" : {
            "vertices" : 3xN matrix
        },
        ...
    }
    """

    if isinstance(skinCluster, str):
        skinCluster = getSkinCluster(skinCluster)

    if not isinstance(skinCluster, oma.MFnSkinCluster):
        raise RuntimeError('not a valid skin cluster')

    joints = getJointsDagArrayForSkinCluster(skinCluster)
    jointsSet = set()
    counter = 0
    jointsIndices = {}
    for joint in joints:
        jointsSet.add(joint.fullPathName())
        jointsIndices[joint.fullPathName()] = counter
        counter = counter + 1

    allJoints = getAllParentJoints(joints)

    influencedMeshNames = set()

    # get all joints
    jointsDict = dict()
    for joint in allJoints:
        jointInfo = dict()
        hasDirectInfluence = joint.fullPathName() in jointsSet

        jointParent = getParentJoint(joint)
        if jointParent is not None:
            jointInfo["parent"] = jointParent.fullPathName()

        # transpose because we store the world and local information in post multiply format i.e. v = M v instead of v = v M
        jointInfo["world"] = MMatrixToDict(mayatransformutil.getWorldMatrix(joint))
        jointInfo["local"] = MMatrixToDict(mayatransformutil.getLocalMatrix(joint))

        influenceDict = dict()
        if hasDirectInfluence:
            jointIdx = -1
            if useJointArrayIndexing:
                # use array index and pass to getWeightsForSkinClusterAndJoint
                # ugly workaround for bug
                jointIdx = jointsIndices[joint.fullPathName()]

            shapeDagVtxIdsAndWeights = getWeightsForSkinClusterAndJoint(skinCluster, joint, jointIdx)
            if shapeDagVtxIdsAndWeights is not None:
                for (shapeDag, vtxIds, weights) in shapeDagVtxIdsAndWeights:
                    meshName = shapeDag.fullPathName()
                    influencedMeshNames.add(meshName)
                    influenceDict[meshName] = { "vertex indices": list(vtxIds), "vertex weights": list(weights) }
            else:
                print('Warning: joint {} does not have any influence'.format(joint.fullPathName()))

        jointInfo["influence"] = influenceDict

        jointsDict[joint.fullPathName()] = jointInfo

    geometryDict = dict()
    for meshName in influencedMeshNames:
        geometryDict[meshName] = MeshToVerticesDict(meshName)

    return { "joints" : jointsDict, "geometry" : geometryDict }


def JointRigStateFromJson(jsonData):
    '''
    Retrieves the matrix transformations for all joints and sets these in the scene
    '''
    joints = None

    if 'joints' in jsonData:
        jointsDict = jsonData['joints']
        for jointName in jointsDict:
            jointTransform = mayatransformutil.getTransformationNode(jointName)
            if jointTransform is None:
                raise RuntimeError('joint ' + jointName + ' is not of type MFnTransform')

            jointDict = jointsDict[jointName]
            # for Maya
            jointMatrix = MMatrixFromDict(jointDict['local'])
            mayaJoint = mayajoint.MayaJoint(jointTransform)
            mayaJoint.updateTransformation(jointMatrix)
    else:
        raise RuntimeError('failure to load joints skinning data')


def JointRigStateToJson(joints):
    '''
    Retrieves the matrix transformations for all joints and writes them into the output json structure.
    '''
    jsonData = dict()
    jsonData['joints'] = dict()

    for joint in joints:
        mJoint = mayajoint.MayaJoint(joint)
        jsonData['joints'][mJoint.node().fullPathName()] = { 'local' : MMatrixToDict(mJoint.localMatrix()) }

    return jsonData
