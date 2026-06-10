# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import List, Optional

# External
from maya import cmds


def create_swing_twist_evaluator(
    name: str,
    start_joint: str,
    end_joint: Optional[str],
    swing_joint: Optional[str],
    swing_blend: float,
    twist_joints: List[str],
    twist_blends: List[float],
    from_end: int = False,
):
    # Create Swing-Twist-Evaluator node
    swing_twist_evaluator_node = cmds.createNode("SwingTwistEvaluatorNode", name=f"{name}_SwingTwistEvalNode")
    # Set twist from end if specified
    if from_end:
        cmds.setAttr(f"{swing_twist_evaluator_node}.fromEnd", True)

    if swing_joint:
        # Set swing blend attribute to default
        cmds.setAttr(f"{swing_twist_evaluator_node}.swingBlend", swing_blend)
        # Connect output swing
        cmds.connectAttr(f"{swing_twist_evaluator_node}.swing", f"{swing_joint}.rotate")

    # Connect input rotations
    cmds.connectAttr(f"{start_joint}.rotate", f"{swing_twist_evaluator_node}.startJoint")
    if end_joint:
        cmds.connectAttr(f"{end_joint}.rotate", f"{swing_twist_evaluator_node}.endJoint")

    # Connect output twists and create twist blends
    for i in range(len(twist_joints)):
        twist_output_attr = f"{swing_twist_evaluator_node}.twists{[i]}"
        twist_blend_attr = f"{swing_twist_evaluator_node}.twistBlend{[i]}"

        cmds.setAttr(twist_output_attr, 0, 0, 0)
        cmds.setAttr(twist_blend_attr, twist_blends[i])

        cmds.connectAttr(twist_output_attr, f"{twist_joints[i]}.rotate")

    return swing_twist_evaluator_node
