# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import TYPE_CHECKING

# Internal
from mh_pose_editor.model import base_extension
from mh_pose_editor.extensions import copy_paste_trs

if TYPE_CHECKING:
    from qtpy import QtWidgets


class GenerateInbetweens(base_extension.PoseEditorExtension):
    __category__ = "Core"

    @property
    def view(self) -> "QtWidgets.QWidget":
        if self._view is not None:
            return self._view

        from qtpy import QtWidgets

        self._view: QtWidgets.QWidget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self._view.setLayout(layout)

        button_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(button_layout)

        generate_inbetweens_button = QtWidgets.QPushButton("Generate Inbetweens")
        button_layout.addWidget(generate_inbetweens_button)

        spin_label = QtWidgets.QLabel("Pose Count: ")
        button_layout.addWidget(spin_label)

        self._spin_box = QtWidgets.QSpinBox()
        self._spin_box.setMinimum(1)
        self._spin_box.setSingleStep(1)
        self._spin_box.setValue(1)
        button_layout.addWidget(self._spin_box)

        generate_inbetweens_button.clicked.connect(self._generate_inbetweens)

        return self._view

    def generate_inbetweens(self, count: int = 1, pose_prefix: str = "pose") -> None:
        """
        Generate inbetween poses between the current position and the default pose
        :param count :type int: number of poses to generate
        :param pose_prefix :type: name of the pose
        """
        context = self.api.get_context()

        solver = context.current_solver
        if not solver:
            return None

        copy_paste_trs_action = copy_paste_trs.BakePosesToTimeline(self.api)

        copy_paste_trs_action.copy_driven_trs(solver=solver)
        copy_paste_trs_action.copy_driver_trs(solver=solver)

        # Calculate the multiplier increment based on the number of desired poses
        multiplier_increment = 1.0 / float(count + 1)
        # Set the start multiplier
        multiplier = 1.0
        # Iterate through the number of desired poses
        for i in range(count):
            # Generate the new multiplier
            multiplier -= multiplier_increment
            # Paste the driver and driven translate, rotate and scale based on the new multiplier
            # Note: Driver only gets rotate and scale applied to it.
            copy_paste_trs_action.paste_driven_trs(multiplier)
            copy_paste_trs_action.paste_driver_trs(multiplier)
            # Create a new pose at this position
            self.api.create_pose(pose_name=f"{pose_prefix}_{i}", solver=solver)

        if self.app:
            self.app.update_solver_settings(solver)

    def _generate_inbetweens(self):
        self.generate_inbetweens(self._spin_box.value())
