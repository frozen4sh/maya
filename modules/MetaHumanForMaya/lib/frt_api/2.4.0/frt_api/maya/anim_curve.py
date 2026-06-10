# Copyright Epic Games, Inc. All Rights Reserved.

from maya import cmds

from frt_api.maya.core import BaseHandler, MayaSceneError
from frt_api.model.maya.anim_curve import MayaAnimCurve


class AnimCurveMayaHandler(BaseHandler):
    """
    Animation curves Maya handler.

    Contains methods for manipulation with animation curves in scene.
    @see BaseHandler
    """

    # ---------------------------
    # Scene animated curves methods
    # ---------------------------

    def set_anim_curve_to_scene(self, curve: MayaAnimCurve):
        """
        Sets Maya animation curve objects to scene.

        @param curve: Instance of animation curves (MayaAnimCurve)
        @throws MayaSceneError: If scene doesn't contains required objects.
        """

        # current angle unit
        angle_unit = cmds.currentUnit(query=True, angle=True)
        cmds.currentUnit(angle="rad")

        try:
            # create new animated curves
            input_obj = None
            output_obj = None
            driver_attr = None
            driven_attr = None

            if curve and curve.anim_curve_type in MayaAnimCurve.AC_TYPES_DOUBLE:
                assert curve.input is not None
                input_obj = self.get_object(curve.input.obj_name, strict=True)
                if not cmds.attributeQuery(curve.input.attr_name, node=input_obj, exists=True):
                    raise MayaSceneError(f"Unable to find attribute: {curve.input.obj_name}.{curve.input.attr_name}")
                driver_attr = f"{curve.input.obj_name}.{curve.input.attr_name}"

            anim_curve_node = None
            for output in curve.outputs:
                output_obj = self.get_object(output.obj_name, strict=True)
                if not cmds.attributeQuery(output.attr_name, node=output_obj, exists=True):
                    raise MayaSceneError(f"Unable to find attribute: {output.obj_name}.{output.attr_name}")
                driven_attr = f"{output.obj_name}.{output.attr_name}"

                if curve.anim_curve_type in MayaAnimCurve.AC_TYPES_TIME:
                    for key in curve.keys:
                        cmds.setKeyframe(driven_attr, time=key.time, value=key.value)
                        cmds.keyTangent(
                            driven_attr,
                            e=True,
                            time=(int(key.time), int(key.time)),
                            ix=key.in_tangent[0],
                            iy=key.in_tangent[1],
                            ox=key.out_tangent[0],
                            oy=key.out_tangent[1],
                        )
                        cmds.keyTangent(
                            driven_attr,
                            e=True,
                            time=(int(key.time), int(key.time)),
                            inTangentType=key.in_tangent_type,
                            outTangentType=key.out_tangent_type,
                        )
                else:
                    if anim_curve_node:
                        cmds.connectAttr(anim_curve_node.output, driven_attr, force=True)
                    else:
                        for key in curve.keys:
                            cmds.setDrivenKeyframe(
                                driven_attr, currentDriver=driver_attr, driverValue=key.unitless_input, value=key.value
                            )
                        anim_curve_node = self.getAnimCurveForInOut(driver_attr, driven_attr)
                        if anim_curve_node:
                            for i, key in enumerate(curve.keys):
                                cmds.keyTangent(
                                    anim_curve_node, e=True, index=(i, i), ix=key.in_tangent[0], iy=key.in_tangent[1]
                                )
                                cmds.keyTangent(
                                    anim_curve_node, e=True, index=(i, i), ox=key.out_tangent[0], oy=key.out_tangent[1]
                                )
                                cmds.keyTangent(
                                    anim_curve_node, e=True, index=(i, i), inTangentType=key.in_tangent_type
                                )
                                cmds.keyTangent(
                                    anim_curve_node, e=True, index=(i, i), outTangentType=key.out_tangent_type
                                )
        finally:
            # angle unit
            cmds.currentUnit(angle=angle_unit)

    def getAnimCurveForInOut(self, inputAttrName, outAttrName):
        """
        Gets animated curve for given input and output attribute pattern.

        @param inputAttrName: Input attribute pattern in format object_name.attributeName. (string)
        @param outAttrName: Output attribute pattern in format object_name.attributeName. (string)
        @return Animated curve if exists, otherwise None. (maya.node.AnimCurve)
        """

        cons1 = cmds.listConnections(inputAttrName, source=False, destination=True, skipConversionNodes=True)
        cons2 = cmds.listConnections(outAttrName, source=True, destination=False, skipConversionNodes=True)
        if cons2 and cmds.objectType(cons2[0]) == "blendWeighted":
            cons2 = cmds.listConnections(cons2[0], source=True, destination=False, skipConversionNodes=True)

        for con1 in cons1:
            for con2 in cons2:
                if con1 == con2:
                    return con1
        return None
