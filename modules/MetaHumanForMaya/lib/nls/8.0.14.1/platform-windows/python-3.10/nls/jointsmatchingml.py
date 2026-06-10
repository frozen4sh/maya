# Copyright Epic Games, Inc. All Rights Reserved.

from __future__ import absolute_import

from . import nlstools
from . import nlstoolsutil

class JointsMatchingML:
    def __init__(self):
        self.opt = nlstools.JointsMatchingModelEvaluator()

    def loadModel(self, modelPath, batchSize=1):
        self.opt.loadModel(modelPath, batchSize)

    def setBindPose(self, jointsBindPoseDict, neutralGeometryDict):
        self.opt.setBindPoseJsonBased(nlstoolsutil.ToJsonStr(jointsBindPoseDict), nlstoolsutil.ToJsonStr(neutralGeometryDict))

    def meshIndices(self):
        return self.opt.meshIndices()

    def modelFilename(self):
        return self.opt.modelFilename()

    def optimize(self, targetDict, jointState, jointsToOptimize):
        output = self.opt.runJsonBased(nlstoolsutil.ToJsonStr(targetDict), nlstoolsutil.ToJsonStr(jointState), nlstoolsutil.ToJsonStr(jointsToOptimize))

        return nlstoolsutil.FromJsonStr(output)
