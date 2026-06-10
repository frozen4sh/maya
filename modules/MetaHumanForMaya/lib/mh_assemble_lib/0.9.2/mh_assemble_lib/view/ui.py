# Copyright Epic Games, Inc. All Rights Reserved.
"""
Mudule containing base UI class and functionality.
"""
import os
import logging
import webbrowser
from typing import Callable

from mh_assemble_lib.common import DNAReaderException
from mh_assemble_lib.version import __version__
from mh_assemble_lib.view.qt import QT_LIB, QtCore, QtWidgets
from mh_assemble_lib.control.form import ProcessForm, ProgressBarForm
from mh_assemble_lib.view.widgets import (
    QHLine,
    QMeshLayut,
    QFileChooser,
    FileChooserForm,
)
from mh_assemble_lib.control.business import Controller


class MHViewer(QtWidgets.QMainWindow):
    """The main UI window element."""

    WIN_OBJECT_NAME = "mhviewer"
    WIN_TITLE = "MH Viewer"
    HELP_URL = "https://epicgames.github.io/MetaHuman-DNA-Calibration/"
    WIN_SIZE_W_MIN = 800
    WIN_SIZE_W_MAX = 1200
    WIN_SIZE_H_MIN = 800
    WIN_SIZE_H_MAX = 1000
    SPACING = 6
    MARGIN_LEFT = 8
    MARGIN_TOP = 8
    MARGIN_RIGHT = 8
    MARGIN_BOTTOM = 8

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self._controller: Controller = None
        self._dna_file_path: str = None
        logging.debug(f"Init UI using {QT_LIB} lib.")

        # WINDOW
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName(MHViewer.WIN_OBJECT_NAME)
        self.setWindowTitle(MHViewer.WIN_TITLE)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # HEADER
        self.ly_header = QtWidgets.QHBoxLayout()
        self.ly_header.setContentsMargins(0, 0, 0, 0)
        self.ly_header.setSpacing(MHViewer.SPACING)
        # label
        self.lbl_header = QtWidgets.QLabel("v" + __version__)
        self.ly_header.addWidget(self.lbl_header)
        self.ly_header.addStretch(1)
        # help
        self.btn_help = QtWidgets.QPushButton(self)
        self.btn_help.setText(" ? ")
        self.btn_help.setToolTip("Help")
        self.btn_help.clicked.connect(self.on_click_help)
        self.ly_header.addWidget(self.btn_help)

        # BODY
        self.ly_body = QtWidgets.QVBoxLayout()
        self.ly_body.setContentsMargins(0, 0, 0, MHViewer.MARGIN_BOTTOM)
        self.ly_body.setSpacing(MHViewer.SPACING)

        # DNA SELECTOR
        self.w_dna = QtWidgets.QWidget()
        self.ly_dna = QtWidgets.QVBoxLayout(self.w_dna)
        self.ly_dna.setContentsMargins(0, 0, 0, 0)
        # file chooser
        self.fc_dna = self.create_file_chooser(
            "DNA path:",
            "DNA file to load. Required by all gui elements",
            "Select a DNA file",
            "DNA files (*.dna)",
            self.on_change_dna_path,
        )
        self.ly_dna.addWidget(self.fc_dna)
        # button load
        self.btn_load = QtWidgets.QPushButton("Load DNA")
        self.btn_load.setEnabled(False)
        self.btn_load.clicked.connect(self.on_click_load_dna)
        self.ly_dna.addWidget(self.btn_load)
        self.ly_body.addWidget(self.w_dna)

        # MESH LAYOUT
        self.w_mesh_layout = QMeshLayut(self, self.on_change_mesh_layout)
        self.ly_body.addWidget(self.w_mesh_layout)

        # BUILD OPTIONS
        # layout
        self.w_options_build = QtWidgets.QWidget()
        self.ly_options_build = QtWidgets.QVBoxLayout(self.w_options_build)
        self.ly_options_build.setContentsMargins(0, 0, 0, MHViewer.MARGIN_BOTTOM)
        # checkbox joints
        self.cb_joints = self.create_checkbox(
            "joints",
            "Add joints to rig. Requires: DNA to be loaded.",
            self.ly_options_build,
            self.on_change_cb_joints,
        )
        # checkbox skin cluster
        self.cb_skin = self.create_checkbox(
            "skin cluster",
            "Add skin cluster to rig. Requires: DNA to be loaded and at least one mesh and joints to be checked.",
            self.ly_options_build,
        )
        # checkbox blend shapes
        self.cb_blend_shapes = self.create_checkbox(
            "blend shapes",
            "Add blend shapes to rig. Requires: DNA to be loaded and at least one mesh to be check.",
            self.ly_options_build,
        )
        # checkbox rig logic
        self.cb_rig_logic = self.create_checkbox(
            "rig logic",
            "Add RigLogic to rig. Requires: DNA to be loaded.",
            self.ly_options_build,
        )
        self.ly_options_build.addStretch()

        # ADDITIONAL OPTIONS
        self.w_options_add = QtWidgets.QWidget()
        self.ly_options_add = QtWidgets.QVBoxLayout(self.w_options_add)
        self.ly_options_add.setContentsMargins(0, 0, 0, MHViewer.MARGIN_BOTTOM)
        # checkbox bs naming
        self.cb_bs_channel_naming = self.create_checkbox(
            "mesh name to blend shape channel name",
            "Add mesh name to blend shape channel name.",
            self.ly_options_add,
            enabled=True,
            checked=False,
        )
        # checkbox ctrl attrs
        self.cb_ctrl_attr = self.create_checkbox(
            "ctrl attributes on root joint",
            "Add raw ctrl attributes on facial root joint.",
            self.ly_options_add,
            enabled=True,
            checked=False,
        )
        # checkbox anim map attrs
        self.cb_anim_map_attr = self.create_checkbox(
            "animated map attributes on root joint",
            "Add animated map attributes on facial root joint.",
            self.ly_options_add,
            enabled=True,
            checked=False,
        )
        # checkbox keyframes
        self.cb_key_frames = self.create_checkbox(
            "key frames",
            "Add keyframes to rig.",
            self.ly_options_add,
            enabled=True,
            checked=False,
        )
        self.ly_options_add.addStretch()

        # OPTIONS
        self.tab_options = QtWidgets.QTabWidget(self)
        self.tab_options.addTab(self.w_options_build, "Build options")
        self.tab_options.addTab(self.w_options_add, "Extra options")
        self.w_options = QtWidgets.QWidget()
        self.ly_options = QtWidgets.QHBoxLayout(self.w_options)
        self.ly_options.addWidget(self.tab_options)
        self.ly_body.addWidget(self.w_options)

        # FILE SELECTORS
        # file chooser gui controls
        self.fc_gui = self.create_file_chooser(
            "GUI controls path:",
            "GUI controls file to load.",
            "Select GUI controls file",
            "gui files (*.ma)",
        )
        # file chooser analog controls
        self.fc_analog = self.create_file_chooser(
            "Analog controls path:",
            "Analog controls file to load.",
            "Select analog controls file",
            "analog files (*.ma)",
        )
        # directory chooser shader
        self.fc_shader = self.create_file_chooser(
            "Shader folder path:",
            "Shader folder to load.",
            "Select shader folder",
            None,
        )
        # file chooser aas
        self.fc_aas = self.create_file_chooser(
            "Additional assemble script path:",
            "Additional assemble script to be run at the end of processing.",
            "Select aas file",
            "python script (*.py)",
        )

        # FOOTER
        # button
        self.btn_process = QtWidgets.QPushButton("Process")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self.on_click_process)
        self.ly_body.addWidget(self.btn_process)
        # progress bar
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("")
        self.ly_body.addWidget(self.progress_bar)

        # MAIN
        self.w_main = QtWidgets.QWidget()
        self.ly_main = QtWidgets.QVBoxLayout(self.w_main)
        self.ly_main.addLayout(self.ly_header)
        self.ly_main.addWidget(QHLine())
        self.ly_main.addLayout(self.ly_body)
        self.ly_main.setContentsMargins(
            MHViewer.MARGIN_LEFT,
            MHViewer.MARGIN_TOP,
            MHViewer.MARGIN_RIGHT,
            MHViewer.MARGIN_BOTTOM,
        )
        self.ly_main.setSpacing(MHViewer.SPACING)
        self.setCentralWidget(self.w_main)
        self.setMaximumSize(MHViewer.WIN_SIZE_W_MAX, MHViewer.WIN_SIZE_H_MAX)
        self.setMinimumSize(MHViewer.WIN_SIZE_W_MIN, MHViewer.WIN_SIZE_H_MIN)
        self.resize(MHViewer.WIN_SIZE_W_MIN, MHViewer.WIN_SIZE_H_MIN)
        self.setStyleSheet(self.load_css())

    # ui helper methods
    def create_file_chooser(
        self,
        label: str,
        hint: str,
        caption: str,
        filter_exp: str,
        on_changed: Callable[[int], None] = None,
    ) -> QFileChooser:
        form = FileChooserForm(label, hint, caption, filter_exp)
        widget = QFileChooser(self, form, on_changed)
        self.ly_body.addWidget(widget)
        return widget

    def create_checkbox(
        self,
        label: str,
        hint: str,
        layout: QtWidgets.QHBoxLayout,
        on_changed: Callable[[int], None] = None,
        checked: bool = False,
        enabled: bool = False,
    ) -> QtWidgets.QCheckBox:
        checkbox = QtWidgets.QCheckBox(label, self)
        checkbox.setChecked(checked)
        checkbox.setEnabled(enabled)
        checkbox.setToolTip(hint)
        if on_changed:
            checkbox.stateChanged.connect(on_changed)
        layout.addWidget(checkbox)
        return checkbox

    def load_css(self) -> str:
        css = os.path.join(os.path.dirname(__file__), "ui.css")
        with open(css, encoding="utf-8") as file:
            return file.read()

    def is_checked(self, checkbox: QtWidgets.QCheckBox) -> bool:
        return checkbox.isEnabled() and checkbox.checkState() == QtCore.Qt.CheckState.Checked

    def set_progress_bar(self, text: str = None, value: int = None) -> None:
        """Setting text and/or value to progress bar"""
        if text is not None:
            self.progress_bar.setFormat(text)
        if value is not None:
            self.progress_bar.setValue(value)

    # setters
    def set_controller(self, controller: Controller) -> None:
        self._controller = controller

    # slots
    def on_click_help(self) -> None:
        webbrowser.open(MHViewer.HELP_URL)

    def on_change_dna_path(self) -> None:
        path = self.fc_dna.get_path()
        enable_load = path is not None
        enable_mesh = enable_load and self._dna_file_path == path
        self.btn_load.setEnabled(enable_load)
        self.w_mesh_layout.btn_select_all.setEnabled(enable_mesh)
        self.w_mesh_layout.btn_deselect_all.setEnabled(enable_mesh)
        self.btn_process.setEnabled(enable_mesh)

    def on_click_load_dna(self) -> None:
        logging.debug("Viewer on_click_load_dna.")
        self.w_main.setEnabled(False)
        QtCore.QCoreApplication.processEvents()
        path = self.fc_dna.get_path()
        if path:
            self._dna_file_path = path
            mesh_layout_form = self._controller.get_mesh_layout_form(path)
            self.w_mesh_layout.set_mesh_layout(mesh_layout_form)
            self.w_mesh_layout.btn_select_all.setEnabled(True)
            self.w_mesh_layout.btn_deselect_all.setEnabled(True)
            self.cb_joints.setEnabled(True)
            self.cb_skin.setEnabled(self.is_checked(self.cb_joints))
            self.cb_blend_shapes.setEnabled(True)
            self.cb_rig_logic.setEnabled(True)
            self.btn_process.setEnabled(True)
        self.w_main.setEnabled(True)

    def on_change_mesh_layout(self) -> None:
        pass

    def on_change_cb_joints(self) -> None:
        self.cb_skin.setEnabled(self.cb_joints.isChecked())

    def on_click_process(self) -> None:
        logging.debug("Viewer on_click_process.")
        self.set_progress_bar(text="Processing in progress...", value=0)
        form = ProcessForm()
        form.dna_path = self._dna_file_path
        form.meshes = self.w_mesh_layout.get_selected_meshes()
        form.add_joints = self.is_checked(self.cb_joints)
        form.add_blend_shapes = self.is_checked(self.cb_blend_shapes)
        form.add_skin_cluster = self.is_checked(self.cb_skin)
        form.add_rig_logic = self.is_checked(self.cb_rig_logic)
        form.add_ctrl_attr = self.is_checked(self.cb_ctrl_attr)
        form.add_anim_map_attr = self.is_checked(self.cb_anim_map_attr)
        form.combine_bs_name = self.is_checked(self.cb_bs_channel_naming)
        form.add_key_frames = self.is_checked(self.cb_key_frames)
        form.gui_ctrls_path = self.fc_gui.get_path()
        form.analog_ctrls_path = self.fc_analog.get_path()
        form.shader_dir = self.fc_shader.get_path()
        form.aas_path = self.fc_aas.get_path()
        form.bar = ProgressBarForm(self.set_progress_bar)

        self.w_main.setEnabled(False)
        try:
            self._controller.build_mh(form)
            self.set_progress_bar(text="Processing completed", value=100)
        except DNAReaderException as e:
            self.set_progress_bar(text="Processing failed. Unable to read DNA.", value=100)
            logging.error(f"DNA Reader Error: {e}")
        except Exception as e:
            self.set_progress_bar(text="Processing failed. Unexpected error.", value=100)
            logging.error(e)
        self.w_main.setEnabled(True)
