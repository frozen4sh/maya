# Copyright Epic Games, Inc. All Rights Reserved.

import os

from qtpy import QtWidgets
from frt_api import ProgressEnd

from .file import FileChooser
from ..utils import general
from ..resource import Resources

logger = general.get_logger()


class UpgradeTool(QtWidgets.QDialog):
    MIN_WIDTH = 730
    WINDOW_TITLE = "MetaHuman DNA Upgrade Tool"

    def __init__(self, upgrade_handler, parent=None):
        super().__init__(parent)

        self.setModal(False)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.layout)
        self.setWindowTitle(f"{self.WINDOW_TITLE}")
        self.setMinimumWidth(self.MIN_WIDTH)

        self.input_dna_file_path = FileChooser(
            "Source MetaHuman DNA:",
            dialog_caption="Select a MetaHuman DNA file",
            dialog_filter="*.dna",
        )
        self.input_dna_file_path.fc_text_field.setPlaceholderText(upgrade_handler.INPUT_DNA_DESCRIPTION)
        self.input_dna_file_path.layout().setStretch(0, 2)
        self.input_dna_file_path.layout().setStretch(1, 5)
        self.input_dna_file_path.fc_text_field.setDisabled(True)

        self.output_dna_file_path = FileChooser(
            "Target MetaHuman DNA:",
            dialog_caption="Save As",
            dialog_filter="*.dna",
            allow_non_existent_files=True,
        )
        self.output_dna_file_path.layout().setStretch(0, 2)
        self.output_dna_file_path.layout().setStretch(1, 5)
        self.output_dna_file_path.fc_text_field.setDisabled(True)

        self.button_layout = QtWidgets.QHBoxLayout()

        self.upgrade_btn = QtWidgets.QPushButton(self)
        self.upgrade_btn.setText("Upgrade")
        self.upgrade_btn.clicked.connect(self.on_upgrade_clicked)

        self.cancel_btn = QtWidgets.QPushButton(self)
        self.cancel_btn.setText("Cancel")
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)

        self.button_layout.addWidget(self.upgrade_btn)
        self.button_layout.addWidget(self.cancel_btn)

        self.layout.addWidget(self.input_dna_file_path)
        self.layout.addWidget(self.output_dna_file_path)
        self.layout.addLayout(self.button_layout)

        self.upgrade_handler = upgrade_handler

    def on_upgrade_clicked(self):
        input_dna_file_path = self.input_dna_file_path.get_file_path()
        if not os.path.exists(input_dna_file_path):
            logger.error("Input MetaHuman DNA file does not exist.")
            return

        output_dna_file_path = self.output_dna_file_path.get_file_path()
        if not output_dna_file_path:
            logger.error("Output MetaHuman DNA file not provided.")
            return
        current_dna_file_path = None
        if Resources().dna_file_path:
            current_dna_file_path = Resources().dna_file_path
        try:
            self.upgrade_handler.upgrade(Resources(), input_dna_file_path, output_dna_file_path)
        except Exception as e:
            logger.error(f"MetaHuman DNA upgrade failed: {e}.")
        else:
            self.accept()
        finally:
            if current_dna_file_path:
                Resources().initialize_from_dna_file(current_dna_file_path)
            else:
                Resources.reset()
            ProgressEnd.emit()

    def on_cancel_clicked(self):
        self.reject()
