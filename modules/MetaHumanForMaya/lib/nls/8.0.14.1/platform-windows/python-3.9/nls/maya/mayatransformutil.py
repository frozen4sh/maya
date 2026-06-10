# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om

from . import mayautil

def getTransformationNode(node):
    '''
    Returns a transformation node for an object (can handle name, object, dagpath, or mfndependencynode).
    '''
    obj = mayautil.getObject(node)
    if obj.hasFn(om.MFn.kTransform):
        return om.MFnTransform(obj)
    return None


def getWorldMatrix(node):
    '''
    Returns the world matrix of the node.
    '''
    if node is None:
        raise RuntimeError('cannot get world matrix for null object')
    tNode = mayautil.getDagNode(node)
    if tNode is None:
        raise RuntimeError('node is not a DAG node')
    matNode = om.MFnMatrixData(om.MPlug(tNode.object(), tNode.attribute('worldMatrix')).elementByLogicalIndex(0).asMObject())
    return matNode.matrix()


def getWorldMatrixRecursive(node):
    '''
    Returns the world matrix of the node by recursively combining the local matrix with the parent matrices.
    '''
    if node is None:
        raise RuntimeError('cannot get world matrix for null object')
    tNode = mayautil.getDagNode(node)
    if tNode is None:
        raise RuntimeError('node is not a DAG node')
    elif tNode.parentCount() == 1:
        return tNode.transformationMatrix() * getWorldMatrixRecursive(tNode.parent(0))
    elif tNode.parentCount() > 1:
        raise RuntimeError('only single parents are supported')
    else:
        return tNode.transformationMatrix()


def getLocalMatrix(node):
    '''
    Returns the local transformation matrix of the node.
    '''
    if node is None:
        raise RuntimeError('cannot get local matrix for null object')
    node = mayautil.getDagNode(node)
    if node is None:
        raise RuntimeError('node is not a DAG node')
    return node.transformationMatrix()


def scaleMatrix(scaleVec):
    '''
    Returns a Maya 4x4 MMatrix represening scale.
    '''
    mat = om.MTransformationMatrix()
    mat.setScale(scaleVec, om.MSpace.kTransform)
    return mat.asMatrix()
    

def shearMatrix(shearVec):
    '''
    Returns a Maya 4x4 MMatrix represening shear.
    '''
    mat = om.MTransformationMatrix()
    mat.setShear(shearVec, om.MSpace.kTransform)
    return mat.asMatrix()


def rotationMatrix(vec, angle):
    '''
    Returns a Maya 4x4 MMatrix represening a rotation.
    '''
    mat = om.MTransformationMatrix()
    mat.setToRotationAxis(vec, angle)
    return mat.asMatrix()
    

def translateMatrix(vec):
    '''
    Returns a Maya 4x4 MMatrix represening a translation.
    '''
    if isinstance(vec, list) and len(vec) == 3:
        vec = om.MVector(vec)
    elif isinstance(vec, om.MPoint):
        vec = om.MVector(vec.x, vec.y, vec.z)
    mat = om.MTransformationMatrix()
    mat.setTranslation(vec, om.MSpace.kTransform)
    return mat.asMatrix()


def decomposeIntoScalingAndShear(S):
    '''
    Decompose a scaling matrix as returned from decomposeIntoScalingRotationAndTranslation into its scaling and shear matrices Sc and Sh such
    that S = Sc * Sh. Sc and Sh can directly be set for the Maya transformation matrix.
    '''
    assert(isinstance(S, om.MMatrix))

    assert(S.getElement(0,1) == 0)
    assert(S.getElement(0,2) == 0)
    assert(S.getElement(0,3) == 0)
    assert(S.getElement(1,2) == 0)
    assert(S.getElement(1,3) == 0)
    assert(S.getElement(2,3) == 0)
    assert(S.getElement(0,3) == 0)
    assert(S.getElement(1,3) == 0)
    assert(S.getElement(2,3) == 0)
    assert(S.getElement(3,3) == 1)
    
    Sc = om.MMatrix()
    Sh = om.MMatrix()
    Sc.setElement(0, 0, S.getElement(0, 0))
    Sc.setElement(1, 1, S.getElement(1, 1))
    Sc.setElement(2, 2, S.getElement(2, 2))
    Sh.setElement(1, 0, S.getElement(1, 0) / S.getElement(1, 1))
    Sh.setElement(2, 0, S.getElement(2, 0) / S.getElement(2, 2))
    Sh.setElement(2, 1, S.getElement(2, 1) / S.getElement(2, 2))
    return Sc, Sh


def decomposeIntoScalingRotationAndTranslation(mat, allowNegativeScaling=False):
    '''
    Decomposes the matrix @p mat into a scaling matrix, rotation matrix, and a translation matrix.
    The scaling matrix is a lower triangular matrix for the top left 3x3 block of the 4x4 matrix. It represents both scale and shear).
    The rotation matrix is a 3x3 rotation matrix.
    The translation matrix just has the translational component on the 4th row.
    S = |s00 0   0   0|
        |s10 s11 0   0|
        |s20 s21 s22 0|
        |0   0   0   1|

    R = |r00 r01 r02 0|
        |r10 s11 r12 0|
        |r20 s21 s22 0|
        |0   0   0   1|    

    T = |1  0  0  0|
        |0  1  0  0|
        |0  0  1  0|
        |tx ty tz 1|

    @param allowNegativeScaling  When the matrix @p mat also contains a flip, then either the method triggers an assert, or the z scaling will be negative.
                                 The rotation matrix is always orthonormal with a determinant 1 (never negative 1)
    '''
    assert(isinstance(mat, om.MMatrix))
    assert(mat.getElement(0,3) == 0)
    assert(mat.getElement(1,3) == 0)
    assert(mat.getElement(2,3) == 0)
    assert(mat.getElement(3,3) == 1)
    S = om.MMatrix()
    R = om.MMatrix()
    T = om.MMatrix()
    # copy translation
    for i in range(3):
        T.setElement(3,i, mat.getElement(3,i))
    
    # the scale matrix S and rotation matrix R can be calculated using RQ decomposition.
    # note that S=R and R=Q in this case i.e. S is a lower triangular 3x3 matrix, and R the
    # rotation matrix
    def copyRow(src, target, index):
        for i in range(4):
            target.setElement(index, i, src.getElement(index, i))
        
    def scaleRow(target, scale, index):
        for i in range(4):
            target.setElement(index, i, target.getElement(index, i) * scale)
            
    def dotRow(A, indexA, B, indexB):
        result = 0
        for i in range(4):
            result += A.getElement(indexA, i) * B.getElement(indexB, i)
        return result
   
    def rowNorm(A, index):
        import math
        return math.sqrt(dotRow(A, index, A, index))
        
    def subtractScaledRow(A, index1, index2, val):
        for i in range(4):
            A.setElement(index1, i, A.getElement(index1, i) - val * A.getElement(index2, i))
            
    def rowVector(A, rowIndex):
        return om.MVector(A.getElement(rowIndex,0), A.getElement(rowIndex,1), A.getElement(rowIndex,2))
        
    def crossProduct(rowA, rowB):
        x = rowA.y * rowB.z -  rowA.z * rowB.y
        y = rowA.z * rowB.x -  rowA.x * rowB.z
        z = rowA.x * rowB.y -  rowA.y * rowB.x
        return om.MVector(x,y,z)
    
    # gram-schmidt rq decomposition
    copyRow(mat, R, 0)
    copyRow(mat, R, 1)
    copyRow(mat, R, 2)

    for i in range(3):
        for j in range(i):
            # subtract projections
            val = dotRow(R, i, R, j)
            S.setElement(i, j, val)
            subtractScaledRow(R, i, j, val)
            
        n = rowNorm(R, i)
        ninv = 1.0 / n
        S.setElement(i, i, n)
        scaleRow(R, ninv, i)
        
    if R.det4x4() < 0: #crossProduct(rowVector(R, 0), rowVector(R, 1)) * rowVector(R,2) < 0:
        if not allowNegativeScaling:
            assert False, 'no negative scaling supported'
        S.setElement(2,2, - S.getElement(2,2))
        R.setElement(2,0, - R.getElement(2,0))
        R.setElement(2,1, - R.getElement(2,1))
        R.setElement(2,2, - R.getElement(2,2))
    
    return S, R, T
