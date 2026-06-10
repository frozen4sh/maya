# Copyright Epic Games, Inc. All Rights Reserved.

import maya.api.OpenMaya as om


def selectObject(obj):
    '''
    Selects an object in the scene. Also works for type MFnDependencyNode.
    '''
    selList = om.MSelectionList()
    name = obj
    if isinstance(obj, om.MFnDependencyNode):
        name = obj.name()
    selList.add(name)
    om.MGlobal.setActiveSelectionList(selList)


def getCurrentSelectionList():
    '''
    Returns the current active selection list
    '''
    return om.MGlobal.getActiveSelectionList()


def getFirstSelection():
    '''
    Returns the first item on the current activte selection list.
    '''
    selList = om.MGlobal.getActiveSelectionList()
    if selList.length() > 0:
        return selList.getDependNode(0)
    return None


def getObject(obj):
    '''
    Retrieves the object (om.MObject) of the given name or object.
    '''
    if isinstance(obj,om.MObject):
        return obj
    elif isinstance(obj, str):
        selList = om.MSelectionList()
        selList.add(obj)
        return selList.getDependNode(0)
    elif isinstance(obj, om.MFnBase):
        return obj.object()
    elif isinstance(obj, om.MDagPath):
        return obj.node()
    else:
        return None


def getDagPath(obj):
    '''
    Retrieves the dag path (om.MDagPath) of the given name or object.
    '''
    if isinstance(obj,om.MFnDagNode):
        return obj.getPath()
    elif isinstance(obj, om.MDagPath):
        return obj
    elif isinstance(obj, om.MObject) and obj.hasFn(om.MFn.kDagNode):
        return om.MFnDagNode(obj).getPath()
    elif isinstance(obj, str):
        selList = om.MSelectionList()
        try:
            selList.add(obj)
        except:
            raise RuntimeError('no object {} exists in the scene'.format(obj))

        if selList.length() > 0:
            return selList.getDagPath(0)
    
    return None


def getDagNode(obj):
    '''
    Retrieves the dag node (om.MFnDagNode) of the given name or object.
    '''
    if isinstance(obj,om.MFnDagNode):
        return obj
    elif isinstance(obj, om.MDagPath):
        return om.MFnDagNode(obj)
    elif isinstance(obj, om.MObject) and obj.hasFn(om.MFn.kDagNode):
        return om.MFnDagNode(obj)
    elif isinstance(obj, str):
        dagPath = getDagPath(obj)
        if dagPath is not None:
            return om.MFnDagNode(dagPath)

    return None


def getParent(node):
    '''
    Returns the next parent joint along the DAG hierarchy if any exists.
    '''
    if node is None:
        raise RuntimeError('do not call getParent on null object')
    node = getDagNode(node)
    if node is None:
        raise RuntimeError('object is not a DAG node and cannot have parents')
    if node.parentCount() == 1:
        return getDagNode(node.parent(0))
    elif node.parentCount() == 0:
        return None
    else:
        raise RuntimeError('only single parents are supported')


