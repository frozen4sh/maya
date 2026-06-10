# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import TYPE_CHECKING

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import base_extension
from mh_pose_editor.extensions.dna_io.model.validations.mhc import model_validator
from mh_pose_editor.extensions.dna_io.model.validations.riglogic import model_check

if TYPE_CHECKING:
    from qtpy import QtWidgets


class DNAValidator(base_extension.PoseEditorExtension):
    __category__ = "Core"

    @property
    def view(self) -> "QtWidgets.QWidget":
        if self._view is not None:
            return self._view

        from qtpy import QtWidgets

        self._view: QtWidgets.QWidget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self._view.setLayout(layout)

        self._validate_mhc_button = QtWidgets.QPushButton("Validate Scene for MetaHuman Creator in Unreal")
        self._validate_mhc_button.setStatusTip(
            "Validates the scene can be safely imported into MetaHuman Creator in Unreal"
        )
        self._validate_mhc_button.setStyleSheet("")
        self._validate_mhc_button.clicked.connect(self._validate_mhc)
        layout.addWidget(self._validate_mhc_button)

        self._validate_riglogic_button = QtWidgets.QPushButton("Validate Scene for RigLogic")
        self._validate_riglogic_button.setStatusTip("Validates the scene can be safely run by RigLogic in any DCC")
        self._validate_riglogic_button.setStyleSheet("")
        self._validate_riglogic_button.clicked.connect(self._validate_rig_logic)
        layout.addWidget(self._validate_riglogic_button)

        return self._view

    def _validate_mhc(self) -> bool:
        """ """
        try:
            model = self.api.serialize(solvers=self.api.rbf_solvers)
            errors = model_validator.MHDNAModelValidator.validate_model(model)
        except Exception as e:
            errors = [str(e)]

        if errors:
            for error in errors:
                LOG.error(error)

            if self.view:
                self._validate_mhc_button.setStyleSheet("background-color: rgb(184,48,48);")

            return False

        if self.view:
            self._validate_mhc_button.setStyleSheet("background-color: rgb(123,170,95);")

        LOG.info("Scene is compatible with MetaHuman Creator in Unreal")

        return True

    def _validate_rig_logic(self) -> bool:
        """ """
        try:
            model = self.api.serialize(solvers=self.api.rbf_solvers)
            check = model_check.DNAModelValidator(model)
            errors, warnings = check.check_model()
        except Exception as e:
            errors = [str(e)]
            warnings = []

        if errors:
            for error in errors:
                LOG.error(error)

            if self.view:
                self._validate_riglogic_button.setStyleSheet("background-color: rgb(184,48,48);")

            return False

        for warning in warnings:
            LOG.warning(warning)

        if self.view:
            self._validate_riglogic_button.setStyleSheet("background-color: rgb(123,170,95);")

        LOG.info("Scene is compatible with RigLogic")

        return True
