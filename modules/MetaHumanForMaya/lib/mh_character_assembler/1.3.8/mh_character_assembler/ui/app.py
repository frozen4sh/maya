# Copyright Epic Games, Inc. All Rights Reserved.
import json
import os
import sys
from pathlib import Path

import dna
import qstyle
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from qtpy import QtCore, QtWidgets

from ..core import logger
from ..core.settings import SettingsManager
from ..importer import CharacterImporter
from .widgets import FileChooser, ThumbnailWidget

__version__ = "1.0.0"

module = sys.modules[__name__]
module.window = None  # type: ignore

material = qstyle.FontIcons("material")


class CharacterBrowser(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    WINDOW_TITLE = "MetaHuman Character Assembler"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qstyle.install_fonts(silent=True)

        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(400, 400)

        self.controls = {}
        self.thumbnails = {}
        self.selected_character = None

        # Set logger
        self.logger = logger.get_logger()
        self.logger.info(f"Initializing {self.WINDOW_TITLE}")

        # Setup UI
        self.setup_ui()
        self._load_settings()
        self.load_thumbnails()
        self.logger.info("Application initialized...")

        qstyle.set_style(self)
        self.resize(600, 740)

    def is_viable_dna_version(self):
        return (
            dna.VersionInfo.getMajorVersion() >= 9
            and dna.VersionInfo.getMinorVersion() >= 4
            and dna.VersionInfo.getPatchVersion() >= 3
        )

    def setup_ui(self):
        directory_fc = FileChooser("MetaHumans Directory:", dialog_caption="Select MetaHuman directory", mode=0)
        directory_fc.chosen.connect(self.load_thumbnails)
        self.controls["directory_fc"] = directory_fc

        mh_browse_layout = QtWidgets.QHBoxLayout()
        mh_browse_layout.addWidget(directory_fc)

        self.thumbs_list_widget = QtWidgets.QListWidget()
        self.thumbs_list_widget.itemSelectionChanged.connect(self.check_assemble_button_enabled)
        self.thumbs_list_widget.setViewMode(QtWidgets.QListWidget.IconMode)
        self.thumbs_list_widget.setIconSize(QtCore.QSize(120, 100))
        self.thumbs_list_widget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.thumbs_list_widget.setMovement(QtWidgets.QListWidget.Static)  # disable drag and drop
        self.thumbs_list_widget.setGridSize(QtCore.QSize(120, 120))
        self.thumbs_list_widget.setStyleSheet("QListWidget::item:selected { border: 3px solid #3586b8 }")
        self.thumbs_list_widget.itemClicked.connect(self.thumbnail_clicked)

        assemble_button = QtWidgets.QPushButton("Assemble")
        assemble_button.setEnabled(False)
        assemble_button.clicked.connect(self.assemble)
        self.controls["assemble_button"] = assemble_button

        f_label = QtWidgets.QLabel("Filter:")
        f_input = QtWidgets.QLineEdit()
        f_input.textChanged.connect(self._filter_thumbnail_list)
        self.controls["f_input"] = f_input

        refresh_button = QtWidgets.QPushButton()
        refresh_button.setIcon(material.icon("refresh"))
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.load_thumbnails)

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(f_label)
        filter_layout.addWidget(f_input)
        filter_layout.addWidget(refresh_button)

        options_label = QtWidgets.QLabel("Import:")
        options_layout = QtWidgets.QHBoxLayout()
        should_import_head = QtWidgets.QCheckBox("Head")
        should_import_head.setChecked(True)
        should_import_head.stateChanged.connect(self.check_assemble_button_enabled)

        should_import_body = QtWidgets.QCheckBox("Body")
        should_import_body.setChecked(True)
        should_import_body.stateChanged.connect(self.check_assemble_button_enabled)

        should_import_textures = QtWidgets.QCheckBox("Textures")
        should_import_textures.setChecked(True)

        should_combine_skeletons = QtWidgets.QCheckBox("Combine Skeletons")
        should_combine_skeletons.setChecked(False)

        options_layout.addWidget(options_label)
        options_layout.addWidget(should_import_head)
        options_layout.addWidget(should_import_body)
        options_layout.addWidget(should_import_textures)
        options_layout.addWidget(should_combine_skeletons)

        # Button group
        up_axis_label = QtWidgets.QLabel("Up Axis:")
        # Radio buttons
        from_dna_up = QtWidgets.QRadioButton("From MH DNA")
        from_dna_up.setChecked(True)

        y_up = QtWidgets.QRadioButton("Y")
        z_up = QtWidgets.QRadioButton("Z")

        # create button group
        scene_orient_group = QtWidgets.QButtonGroup()
        scene_orient_group.addButton(from_dna_up)
        scene_orient_group.addButton(y_up)
        scene_orient_group.addButton(z_up)

        # add buttons to horizontal layout
        scene_orient_layout = QtWidgets.QHBoxLayout()
        scene_orient_layout.addWidget(up_axis_label)
        scene_orient_layout.addWidget(from_dna_up)
        scene_orient_layout.addWidget(y_up)
        scene_orient_layout.addWidget(z_up)

        self.controls["should_import_head"] = should_import_head
        self.controls["should_import_body"] = should_import_body
        self.controls["should_import_textures"] = should_import_textures
        self.controls["should_combine_skeletons"] = should_combine_skeletons
        self.controls["scene_orientation"] = scene_orient_group

        wrapper_layout = QtWidgets.QVBoxLayout()
        if not self.is_viable_dna_version():
            info_message = QtWidgets.QLabel(
                f"Loaded DNA plugin ({dna.VersionInfo.getVersionString()}) is not supported! "
                f"Please make sure you are using 9.4.4 or higher!"
            )

            info_message.setStyleSheet("QLabel { border: 1px solid #bf3c1f; padding: 3px; background: #822c1d }")
            wrapper_layout.addWidget(info_message)

        wrapper_layout.addLayout(mh_browse_layout)
        wrapper_layout.addLayout(filter_layout)
        wrapper_layout.addWidget(self.thumbs_list_widget)
        wrapper_layout.addLayout(options_layout)
        wrapper_layout.addLayout(scene_orient_layout)
        wrapper_layout.addWidget(assemble_button)

        central_widget = QtWidgets.QWidget(self)
        central_widget.setLayout(wrapper_layout)
        self.setCentralWidget(central_widget)

    def check_assemble_button_enabled(self):
        assemble_button_enabled = (
            self.is_viable_dna_version()
            and (len(self.thumbs_list_widget.selectedItems()) > 0)
            and (self.controls["should_import_head"].isChecked() or self.controls["should_import_body"].isChecked())
        )

        self.controls["assemble_button"].setEnabled(assemble_button_enabled)

    def open_file(self, file_path):
        with open(file_path) as f:
            d = json.load(f)
            return d

    def load_thumbnails(self):
        """
        Load thumbnails from a directory and add them to thumbnails_list_widget.
        :return:
        """
        directory = self.controls["directory_fc"].get_value()
        self.thumbs_list_widget.clear()
        self.thumbnails = {}

        if directory and os.path.exists(directory):
            for dir_entry in os.listdir(directory):
                mh_path = os.path.join(directory, dir_entry)

                head_dna = os.path.join(mh_path, "head.dna")
                body_dna = os.path.join(mh_path, "body.dna")
                manifest_path = os.path.join(mh_path, "ExportManifest.json")

                if (
                    os.path.isdir(mh_path)
                    and os.path.exists(head_dna)
                    and os.path.exists(body_dna)
                    and os.path.exists(manifest_path)
                ):
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        name = manifest["metaHumanName"]
                        thumbnail_path = os.path.join(mh_path, f"{name}.png")

                        self.thumbnails[name] = {
                            "name": name,
                            "preview": thumbnail_path,
                            "path": mh_path,
                            "config": {
                                "bodyDnaPath": f"{mh_path}\\body.dna",
                                "mapsDirPath": f"{mh_path}\\Maps\\",
                                "headDnaPath": f"{mh_path}\\head.dna",
                            },
                        }

        sorted_thumbnails = dict(sorted(self.thumbnails.items()))

        # add thumbnails to list widget
        for t in sorted_thumbnails:
            thumb_file = sorted_thumbnails[t]["preview"]
            item = QtWidgets.QListWidgetItem(self.thumbs_list_widget)
            item.setSizeHint(QtCore.QSize(120, 120))
            file_name = Path(thumb_file).stem
            item_widget = ThumbnailWidget(thumb_file, height=100, width=100, label=sorted_thumbnails[t]["name"])
            item_widget.file_name = file_name
            self.thumbs_list_widget.addItem(item)
            self.thumbs_list_widget.setItemWidget(item, item_widget)

    def thumbnail_clicked(self, item):
        item.setSelected(True)
        self.thumbs_list_widget.setFocus()
        selected_item = item.listWidget().itemWidget(item)
        self.selected_character = self.thumbnails[selected_item.get_value()]["config"]

    def assemble(self):
        options = {
            "import_head": self.controls["should_import_head"].isChecked(),
            "import_body": self.controls["should_import_body"].isChecked(),
            "import_textures": self.controls["should_import_textures"].isChecked(),
            "scene_orientation": self.controls["scene_orientation"].checkedButton().text(),
            "combine_skeletons": self.controls["should_combine_skeletons"].isChecked(),
        }
        self._save_settings()
        CharacterImporter().execute(self.selected_character, options)

    def _filter_thumbnail_list(self):
        for i in range(self.thumbs_list_widget.count()):
            item = self.thumbs_list_widget.item(i)
            current = item.listWidget().itemWidget(item).get_value().lower()
            if self.controls["f_input"].text() in current:
                self.thumbs_list_widget.item(i).setHidden(False)
            else:
                self.thumbs_list_widget.item(i).setHidden(True)

    def _load_settings(self) -> None:
        SettingsManager()
        if SettingsManager.QSETTINGS:
            should_import_head = SettingsManager.get_setting("mh_character_assembler:should_import_head")

            if should_import_head is not None:
                self.controls["should_import_head"].setChecked(bool(int(should_import_head)))

            should_import_body = SettingsManager.get_setting("mh_character_assembler:should_import_body")
            if should_import_body is not None:
                self.controls["should_import_body"].setChecked(bool(int(should_import_body)))

            should_import_textures = SettingsManager.get_setting("mh_character_assembler:should_import_textures")
            if should_import_textures is not None:
                self.controls["should_import_textures"].setChecked(bool(int(should_import_textures)))

            should_combine_skeletons = SettingsManager.get_setting("mh_character_assembler:should_combine_skeletons")
            if should_combine_skeletons is not None:
                self.controls["should_combine_skeletons"].setChecked(bool(int(should_combine_skeletons)))

            scene_orientation = SettingsManager.get_setting("mh_character_assembler:scene_orientation")
            if scene_orientation is not None:
                for button in self.controls["scene_orientation"].buttons():
                    if button.text() == scene_orientation:
                        button.setChecked(True)
                        break

            current_directory = SettingsManager.get_setting("mh_character_assembler:current_directory")
            if current_directory is not None:
                self.controls["directory_fc"].set_value(current_directory)

    def _save_settings(self) -> None:
        if not SettingsManager.QSETTINGS:
            SettingsManager()
        SettingsManager.set_setting(
            "mh_character_assembler:current_directory",
            self.controls["directory_fc"].get_value(),
        )
        SettingsManager.set_setting(
            "mh_character_assembler:should_import_head",
            int(self.controls["should_import_head"].isChecked()),
        )
        SettingsManager.set_setting(
            "mh_character_assembler:should_import_body",
            int(self.controls["should_import_body"].isChecked()),
        )
        SettingsManager.set_setting(
            "mh_character_assembler:should_import_textures",
            int(self.controls["should_import_textures"].isChecked()),
        )
        SettingsManager.set_setting(
            "mh_character_assembler:scene_orientation",
            self.controls["scene_orientation"].checkedButton().text(),
        )
        SettingsManager.set_setting(
            "mh_character_assembler:should_combine_skeletons",
            int(self.controls["should_combine_skeletons"].isChecked()),
        )


def on_destroyed():
    module.window = None


def show(parent=None):
    # create if it doesn't exist
    if module.window is None:
        module.window = CharacterBrowser(parent)
        module.window.destroyed.connect(on_destroyed)

    # If the window is minimized, raise it
    if module.window.windowState() & QtCore.Qt.WindowMinimized:
        module.window.setWindowState(QtCore.Qt.WindowActive)

    # show and make active
    module.window.show(dockable=True)
    module.window.activateWindow()

    return module.window
