# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om

from .mayatransformutil import getTransformationNode
from .mayatransformutil import translateMatrix, scaleMatrix, shearMatrix
from .mayatransformutil import getWorldMatrix, getWorldMatrixRecursive
from .mayatransformutil import decomposeIntoScalingAndShear, decomposeIntoScalingRotationAndTranslation

class MayaTransform:
    '''
    Wrapper for a Maya transform with convenience function to set the transformation without changing the rotation orientation or pivots.
    For joints we need to use MayaJoint.

    Transformation: 
    matrix = [inv(Sp)] * [S] * [Sh] * [Sp] * [St] * [inv(Rp)] * [Ro] * [R] * [Rp] * [Rt] * [T]
    info: http://help.autodesk.com/view/MAYAUL/2018/ENU/?guid=__cpp_ref_class_m_fn_transform_html
    '''

    def __init__(self, transform):
        self.transform = getTransformationNode(transform)
        assert self.transform and isinstance(self.transform, om.MFnTransform), "node is not a transform"
        assert not self.transform.object().hasFn(om.MFn.kJoint), "node is a joint - use class MayaJoint"
        assert self.transform.findPlug("inheritsTransform", False).asBool(), "only transform which inherit the parent transform are supported"
    
    
    def node(self):
        return self.transform


    def scaleVector(self):
        return self.transform.scale()
    

    def scaleMatrix(self):
        return scaleMatrix(self.scaleVector())


    def shearVector(self):
        return self.transform.shear()
    

    def shearMatrix(self):
        return shearMatrix(self.shearVector())


    def scalePivot(self):
        return self.transform.scalePivot(om.MSpace.kTransform)


    def scalePivotTranslation(self):
        return self.transform.scalePivotTranslation(om.MSpace.kTransform)
    

    def rotationMatrix(self):
        return self.transform.rotation().asMatrix()


    def rotationOrientation(self):    
        return self.transform.rotateOrientation(om.MSpace.kTransform).asMatrix()
        

    def rotatePivot(self):
        return self.transform.rotatePivot(om.MSpace.kTransform)


    def rotatePivotTranslation(self):
        return self.transform.rotatePivotTranslation(om.MSpace.kTransform)


    def translationMatrix(self):
        return translateMatrix(self.transform.translation(om.MSpace.kTransform))
    

    def localMatrix(self):
        return self.transform.transformationMatrix()


    def localMatrixOwn(self):
        return translateMatrix(self.scalePivot()).inverse() * \
                self.scaleMatrix() * \
                self.shearMatrix() * \
                translateMatrix(self.scalePivot()) * \
                translateMatrix(self.scalePivotTranslation()) * \
                translateMatrix(self.rotatePivot()).inverse() * \
                self.rotationOrientation() * \
                self.rotationMatrix() * \
                translateMatrix(self.rotatePivot()) * \
                translateMatrix(self.rotatePivotTranslation()) * \
                self.translationMatrix()


    def worldMatrix(self):
        return getWorldMatrix(self.transform)


    def worldMatrixOwn(self):
        return getWorldMatrixRecursive(self.transform)


    def updateTransformation(self, M, allowNegativeScaling=False):
        Svec, Shvec, Rquat, Tvec = self._decomposeIntoScalingShearRotationAndTranslationWhileKeepingPivotsAndRotationOrientationFixed(M, allowNegativeScaling)
        self._setTransformParameters(S=Svec, Sh=Shvec, Rquat=Rquat, Tvec=Tvec)
    
    def _setTransformParameters(self, S=None, Sh=None, Rquat=None, Tvec=None):
        '''
        Utility function to set the transform parameters of a om.MFnTransform node consistent with how
        it is calculated from transformParametersFromMatrixWithFixedPivots.
        '''
        if S is not None:
            self.transform.setScale(S)
        if Sh is not None:
            self.transform.setShear(Sh)
        if Rquat is not None:
            self.transform.setRotation(Rquat, om.MSpace.kTransform)
        if Tvec is not None:
            self.transform.setTranslation(Tvec, om.MSpace.kTransform)
                

    def _decomposeIntoScalingShearRotationAndTranslationWhileKeepingPivotsAndRotationOrientationFixed(self, M, allowNegativeScaling=False):
        '''
        we have S_ * R_ * T_ = M
        maya transform uses: inv(Sp) * S * Sh * Sp * St * inv(Rp) * Ro * R * Rp * Rt * T = M
        we can calculate the new S, Sh, R, and T by combining the matrices appropriately
        '''
        transform = self.transform

        assert(isinstance(M, om.MMatrix))
        assert(isinstance(transform, om.MFnTransform))

        Sp_vec = transform.scalePivot(om.MSpace.kTransform)
        St_vec = transform.scalePivotTranslation(om.MSpace.kTransform)
        Rp_vec = transform.rotatePivot(om.MSpace.kTransform)
        Rt_vec = transform.rotatePivotTranslation(om.MSpace.kTransform)
        Ro = transform.rotateOrientation(om.MSpace.kTransform).asMatrix()
            
        Sp = translateMatrix(Sp_vec)
        invSp = Sp.inverse()
        St = translateMatrix(St_vec)
        Rp = translateMatrix(Rp_vec)
        invRp = Rp.inverse()
        Rt = translateMatrix(Rt_vec)

        S_, R_, T_ = decomposeIntoScalingRotationAndTranslation(M, allowNegativeScaling)
        
        # scaling and shearing can be decomposed
        S, Sh = decomposeIntoScalingAndShear(S_)
        
        # rotation is the combination of the rotation orietnation and rotation
        R = Ro.transpose() * R_
        
        # for translation we need to combine all pivot transformations and combine it with the translation
        # total_no_t = inv(Sp) * S * Sh * Sp * St * inv(Rp) * Ro * R * Rp * Rt
        # total_no_t * T = S_ * R_ * T_
        # S_ and R_ do not have a translation component
        # hence translation component of total_no_t (from pivots) and translation should add up to T_
        total_no_t = invSp * S * Sh * Sp * St * invRp * Ro * R * Rp * Rt
        tx = T_.getElement(3,0) - total_no_t.getElement(3,0)
        ty = T_.getElement(3,1) - total_no_t.getElement(3,1)
        tz = T_.getElement(3,2) - total_no_t.getElement(3,2)
        T = translateMatrix(om.MVector(tx,ty,tz))

        Svec = om.MVector(S.getElement(0,0), S.getElement(1,1), S.getElement(2, 2))
        Shvec = om.MVector(Sh.getElement(1,0), Sh.getElement(2,0), Sh.getElement(2, 1))
        Tvec = om.MVector(T.getElement(3,0), T.getElement(3,1), T.getElement(3,2))
        Rquat = om.MQuaternion()
        Rquat.setValue(R)

        recompM1 = total_no_t * T
        assert M.isEquivalent(recompM1, tolerance=1e-4), 'decomposition of transform has failed'

        recompM2 = invSp * scaleMatrix(Svec) * shearMatrix(Shvec) * Sp * St * invRp * Ro * Rquat.asMatrix() * Rp * Rt * translateMatrix(Tvec)
        assert M.isEquivalent(recompM2, tolerance=1e-4), 'decomposition of transform has failed'
        
        return Svec, Shvec, Rquat, Tvec
