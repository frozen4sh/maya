# Copyright Epic Games, Inc. All Rights Reserved.

from __future__ import absolute_import

from . import nlstools
from . import nlstoolsutil

class AssetGeneration:
    def __init__(self):
        self.opt = nlstools.AssetGenerationWrapper()

    def LoadModelBinary(self, pathToModelDesctiption):
        self.opt.LoadModelBinary(pathToModelDesctiption)
        
    def Apply(self, inputDict):
        output = self.opt.Apply(nlstoolsutil.ToJsonStr(inputDict))

        return nlstoolsutil.FromJsonStr(output) 
        
class LodGeneration:
    def __init__(self):
        self.opt = nlstools.LodGenerationWrapper()

    def LoadModelBinary(self, pathToModelDesctiption, sourceLod):
        return self.opt.LoadModelBinary(pathToModelDesctiption, sourceLod)
        
    def Apply(self, inputDict):
        output = self.opt.Apply(nlstoolsutil.ToJsonStr(inputDict))

        return nlstoolsutil.FromJsonStr(output)
