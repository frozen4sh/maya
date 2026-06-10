# Copyright Epic Games, Inc. All Rights Reserved.
from maya import OpenMaya, cmds


def as_dagpath(node, extend_to_shape=True):
    selection_list = OpenMaya.MSelectionList()
    selection_list.add(node)

    dagpath = OpenMaya.MDagPath()
    selection_list.getDagPath(0, dagpath)

    if extend_to_shape:
        dagpath.extendToShape()

    return dagpath


def find_closest_uv_point(points, mesh, uv_set="map1", uv_set_fallBack=False):
    # check UVSets
    uv_sets = cmds.polyUVSet(mesh, q=True, allUVSets=True)
    if not uv_sets:
        raise RuntimeError("No UV Sets found!")
    if uv_set not in uv_sets:
        if uv_set_fallBack:
            uv_set = uv_sets[0]
            print(f'UV Set "{uv_set}" not found, using "{uv_sets[0]}" instead')
        else:
            raise RuntimeError(f"Invalid UV Set provided: {uv_set}")

    mesh_dagpath = as_dagpath(mesh)
    fn_mesh = OpenMaya.MFnMesh(mesh_dagpath)

    uvs = list()
    for i in range(len(points)):
        script_util1 = OpenMaya.MScriptUtil()
        script_util1.createFromDouble(0.0, 0.0)
        uv_point = script_util1.asFloat2Ptr()

        point = OpenMaya.MPoint(*points[i])
        fn_mesh.getUVAtPoint(point, uv_point, OpenMaya.MSpace.kWorld, uv_set)

        u = OpenMaya.MScriptUtil.getFloat2ArrayItem(uv_point, 0, 0)
        v = OpenMaya.MScriptUtil.getFloat2ArrayItem(uv_point, 0, 1)

        uvs.append((u, v))

    return uvs
