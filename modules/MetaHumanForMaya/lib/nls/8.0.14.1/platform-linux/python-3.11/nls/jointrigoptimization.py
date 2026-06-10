# Copyright Epic Games, Inc. All Rights Reserved.

from __future__ import absolute_import

from .maya import mayajoint
from .maya import mayarig
from . import nlstools
from . import nlstoolsutil


class PassData:

    def __init__(self, skinClusterName, jointNames=None, skinningDict=None, meshDict=None):
        """
        Initializes the Pass with data. If the skinClusterName is given, the data will be read from the scene.
        If not, the prepared data that is provided will be used.

        @param skinClusterName: Name of the skin cluster to read the data from.
        @param jointNames: List of joint names of all the joints present in the skin cluster.
        @param skinningDict: Skinning data in the dictionary format.
        @param meshDict: Mesh data in the dictionary format.
        """
        # Read data from the scene
        if skinClusterName:
            self.skinCluster = mayarig.getSkinCluster(skinClusterName)
            joints = mayarig.getJointsDagArrayForSkinCluster(self.skinCluster)
            self.allJoints = mayarig.getAllParentJoints(joints)
            self.skinningDict = mayarig.SkinningToDict(self.skinCluster, useJointArrayIndexing=True)

            self.jointDOFs = dict()
            for joint in self.allJoints:
                mayaJoint = mayajoint.MayaJoint(joint)
                jointName = mayaJoint.node().fullPathName()
                self.jointDOFs[jointName] = {"fixed": True, "rotation": False, "translation": False}

            self.geometryName = list(self.skinningDict["geometry"].keys())[0]
            self.meshDict = {self.geometryName: mayarig.MeshToMeshDict(self.geometryName)}
        elif jointNames and skinningDict and meshDict:
            self.skinningDict = skinningDict

            self.jointDOFs = dict()
            for jointName in jointNames:
                self.jointDOFs[jointName] = {"fixed": True, "rotation": False, "translation": False}

            self.geometryName = list(self.skinningDict["geometry"].keys())[0]
            self.meshDict = meshDict
        else:
            raise RuntimeError("Necessary data not provided.")

        if len(self.skinningDict["geometry"]) != 1:
            raise RuntimeError("JointRigOptimization currently only supports a single geometry per passID.")

        numOfVertices = len(self.meshDict[self.geometryName]["vertices"]["data"]) // 3
        self.defaultSplitMap = [1.0] * numOfVertices
        self.splitMap = self.defaultSplitMap

    def getState(self):
        state = dict()
        for jointName in self.jointDOFs:
            mayaJoint = mayajoint.MayaJoint(jointName)
            state[jointName] = mayaJoint.localMatrix()
        return state

    def setState(self, state):
        for jointName in self.jointDOFs:
            mayaJoint = mayajoint.MayaJoint(jointName)
            if jointName in state:
                mayaJoint.updateTransformation(state[jointName])

    def setStartState(self, state):
        jointsToMatch = []
        for jointName in self.jointDOFs:
            if self.jointDOFs[jointName]['fixed'] == False:
                mayaJoint = mayajoint.MayaJoint(jointName)
                if jointName in state:
                    mayaJoint.updateTransformation(state[jointName])
                    jointsToMatch.append(jointName)
        return jointsToMatch

    def setMutable(self, joints):
        for joint in joints:
            mayaJoint = mayajoint.MayaJoint(joint)
            jointName = mayaJoint.node().fullPathName()
            if jointName in self.jointDOFs:
                self.jointDOFs[jointName] = { "fixed" : False, "rotation" : True, "translation" : True }

    def setConstantAll(self):
        for jointName in self.jointDOFs:
            self.jointDOFs[jointName] = { "fixed" : True, "rotation" : False, "translation" : False }

    def isFixed(self, joint):
        mayaJoint = mayajoint.MayaJoint(joint)
        jointName = mayaJoint.node().fullPathName()

        if jointName in self.jointDOFs:
            return self.jointDOFs[jointName]["fixed"]
        else:
            raise RuntimeError("{} is not part of the pass data".format(jointName))


    def setDOF(self, joint, rotation, translation):
        '''
        Sets the DOF of the joint. Raises error if the joint is not part of this passID.
        Raises an error if the joint is fixed.
        '''
        mayaJoint = mayajoint.MayaJoint(joint)
        jointName = mayaJoint.node().fullPathName()

        if jointName not in self.jointDOFs:
            raise RuntimeError("{} is not part of the passID data".format(jointName))

        if self.isFixed(jointName):
            raise RuntimeError("joint {} is fixed and the DOF cannot be set".format(jointName))

        self.jointDOFs[jointName]["rotation"] = rotation
        self.jointDOFs[jointName]["translation"] = translation

    def setSplitMap(self, splitMap):
        self.splitMap = splitMap

class JointRigOptimization:
    def __init__(self):
        self.opt = nlstools.JointRigOptimization()
        self.passes = dict()

    def _verifyPassExists(self, passID):
        if not isinstance(passID, int):
            raise RuntimeError('Pass IDs need to be integer')

        if not passID in self.passes:
            raise RuntimeError('Pass with ID {} does not exist'.format(passID))

    def removePass(self, passID):
        self._verifyPassExists(passID)
        del self.passes[passID]

    def addPass(self, passID, skinClusterName, jointNames=None, skinningDict=None, meshDict=None):
        if not isinstance(passID, int):
            raise RuntimeError('Pass IDs need to be integer')

        if passID < 0:
            raise RuntimeError('Pass IDs need to be >= 0.')

        if passID in self.passes:
            raise RuntimeError('JointRigOptimization already contains data for pass with ID {}'.format(passID))

        self.passes[passID] = PassData(skinClusterName, jointNames, skinningDict, meshDict)


    def setDOF(self, passID, jointName, rotation, translation):
        '''
        Method to set the DOFs of a joint for a pass with index passID.
        '''
        self._verifyPassExists(passID)
        self.passes[passID].setDOF(jointName, rotation=rotation, translation=translation)

    def getAllStates(self):
        states = dict()
        for passID in self.passes:
            states.update(self.passes[passID].getState())
        return states


    def setAllStates(self, states):
        for passID in self.passes:
            self.passes[passID].setState(states)


    def optimize(self, passID, targetShapeName, iterations=10,
                 translationRegularization=0.0, rotationRegularization=5.0,
                 strainWeight=0.001, bendingWeight=0.001, targetDict=None, jointState=None):
        self._verifyPassExists(passID)

        # Load skinning information including the binding matrices and the rest poses for the pose regularization.
        self.opt.setJointRigJsonBased(nlstoolsutil.ToJsonStr(self.passes[passID].skinningDict))

        # Load the mesh (required to calculate stretching and bending terms)
        self.opt.setMeshJsonBased(nlstoolsutil.ToJsonStr(self.passes[passID].meshDict))

        # Set whether joints are constant or mutable
        for jointName in self.passes[passID].jointDOFs:
            jointDOFs = self.passes[passID].jointDOFs[jointName]
            rotation = not jointDOFs["fixed"] and jointDOFs["rotation"]
            translation = not jointDOFs["fixed"] and jointDOFs["translation"]
            self.opt.setJointDegreesOfFreedom(jointName, rotation, translation)

        # Read data from the scene
        if targetShapeName:
            jointState = mayarig.JointRigStateToJson(self.passes[passID].allJoints)

            deformedDict = mayarig.MeshToNamedGeometryDict(targetShapeName, targetname=self.passes[passID].geometryName)
            deformedDictStr = nlstoolsutil.ToJsonStr(deformedDict)
        # Use the provided target and joint state data
        elif targetDict and jointState:
            deformedDictStr = nlstoolsutil.ToJsonStr(targetDict)
        else:
            raise RuntimeError("Necessary data not provided.")

        # update the optimizer with the current state of all its joints
        self.opt.setRigStateJsonBased(nlstoolsutil.ToJsonStr(jointState))
        self.opt.optimizeJointsJsonBased(deformedDictStr, nlstoolsutil.ToJsonStr(self.passes[passID].splitMap), rotationRegularization, translationRegularization, strainWeight, bendingWeight, iterations)
        rigStateDict = nlstoolsutil.FromJsonStr(self.opt.rigStateJsonBased())

        # Update the scene
        if targetShapeName:
            mayarig.JointRigStateFromJson(rigStateDict)
        # Return the calculated joint state
        else:
            return rigStateDict
