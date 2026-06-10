# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om

from .mayatransformutil import getTransformationNode
from .mayatransformutil import translateMatrix, scaleMatrix
from .mayatransformutil import getWorldMatrix, getWorldMatrixRecursive
from .mayatransformutil import decomposeIntoScalingAndShear, decomposeIntoScalingRotationAndTranslation


class MayaJoint:
    '''
    Wrapper for a Maya joint with convenience function to set the transformation without changing the joint orientation 
    and the rotation orientation

    Transformation: 
    matrix = [S] * [RO] * [R] * [JO] * [IS] * [T]
    info: http://help.autodesk.com/cloudhelp/2018/ENU/Maya-SDK/cpp_ref/class_m_fn_ik_joint.html
    '''

    def __init__(self, joint):
        self.joint = getTransformationNode(joint)
        assert self.joint and self.joint.object().hasFn(om.MFn.kJoint), "node is not a joint"
        assert self.joint.findPlug("inheritsTransform", False).asBool(), "only joints which inherit the parent transform are supported"
        # joints should not use segmentScaleCompensate when doing joint optimizations for the following two reasons:
        # 1) the transformations would need to be updated from root joint to leaf joint in the correct order as any scaling transformation
        #    would need to be updated in the child joint first before that one can then be updated
        # 2) an inverse scaling transform in a node means that even a new transformation without shear can result in a shear
        #    matrix when it is combined with the inverse scaling transform
        assert not self.hasSegmentScaleCompensate(), "joints should not use segmentScaleCompensate"
    

    def node(self):
        return self.joint


    def scaleVector(self):
        return self.joint.scale()
    

    def scaleMatrix(self):
        return scaleMatrix(self.scaleVector())


    def rotationMatrix(self):
        return self.joint.rotation().asMatrix()


    def rotationOrientation(self):
        return self.joint.rotateOrientation(om.MSpace.kTransform).asMatrix()
        

    def translationMatrix(self):
        return translateMatrix(self.joint.translation(om.MSpace.kTransform))
    

    def jointOrientation(self):
        jOvec = om.MVector(self.joint.findPlug("jointOrient", False).child(0).asDouble(),
                            self.joint.findPlug("jointOrient", False).child(1).asDouble(),
                            self.joint.findPlug("jointOrient", False).child(2).asDouble())
        return om.MEulerRotation(jOvec).asMatrix()


    def setSegmentScaleCompensate(self, enable):
        self.joint.findPlug("segmentScaleCompensate", False).setBool(enable)


    def hasSegmentScaleCompensate(self):
        return self.joint.findPlug("segmentScaleCompensate", False).asBool()


    def inverseScaleCompensateMatrix(self):
        '''
        Returns the inverse scale compensate matrix. However, segmentScaleCompensate should be disabled, see assert and comment in constructor.
        '''
        if self.hasSegmentScaleCompensate():
            invScaleVec = om.MVector(1.0 / self.joint.findPlug("inverseScale", False).child(0).asDouble(),
                                    1.0 / self.joint.findPlug("inverseScale", False).child(1).asDouble(),
                                    1.0 / self.joint.findPlug("inverseScale", False).child(2).asDouble())
            return scaleMatrix(invScaleVec)
        else:
            return om.MMatrix()


    def localMatrix(self):
        return self.joint.transformationMatrix()


    def localMatrixOwn(self):
        return self.scaleMatrix() * self.rotationOrientation() * self.rotationMatrix() * self.jointOrientation() * self.inverseScaleCompensateMatrix() * self.translationMatrix()


    def worldMatrix(self):
        return getWorldMatrix(self.joint)


    def worldMatrixOwn(self):
        return getWorldMatrixRecursive(self.joint)


    def updateTransformation(self, M, allowNegativeScaling=False):
        '''
        Update the transformation matrix while keeping the rotationOrientation, jointOrientation, and the inverseScaleCompensateMatrix intact.
        '''
        assert(isinstance(M, om.MMatrix))
        
        # joint does not have any pivots, so we cna get the translation component directly
        tx = M.getElement(3,0)
        ty = M.getElement(3,1)
        tz = M.getElement(3,2)
        Tvec = om.MVector(tx,ty,tz)
        T = translateMatrix(Tvec)

        # remove the inverse scale compensate matrix
        M2 = M * self.inverseScaleCompensateMatrix().inverse()

        S_, R_, _ = decomposeIntoScalingRotationAndTranslation(M2, allowNegativeScaling)
        assert M.isEquivalent(S_ * R_ * self.inverseScaleCompensateMatrix() * T, tolerance=1e-6), 'decomposition of transform has failed'

        # M = [S] * [RO] * [R] * [JO] * [IS] * [T]
        # => R_ = RO * R * JO = R_
        R = self.rotationOrientation().transpose() * R_ * self.jointOrientation().transpose()

        # [S] = S_ * R_ * invIS * invR_
        S, Sh = decomposeIntoScalingAndShear(S_)
        assert Sh.isEquivalent(om.MMatrix(), 1e-6), "joints do not support shear"

        recompM2 = S * self.rotationOrientation() * R * self.jointOrientation() * self.inverseScaleCompensateMatrix() * T
        assert M.isEquivalent(recompM2, tolerance=1e-6), 'decomposition of transform has failed'

        # update the parameters
        Svec = om.MVector(S.getElement(0,0), S.getElement(1,1), S.getElement(2, 2))
        self.joint.setScale(Svec)

        Rquat = om.MQuaternion()
        Rquat.setValue(R)
        self.joint.setRotation(Rquat, om.MSpace.kTransform)

        self.joint.setTranslation(Tvec, om.MSpace.kTransform)


