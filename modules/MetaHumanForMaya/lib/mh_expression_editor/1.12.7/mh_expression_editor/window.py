# Copyright Epic Games, Inc. All Rights Reserved.

import os
import sys
import contextlib
from functools import partial

import qstyle
from qtpy import QtCore, QtWidgets
from frt_api import FRTApiError, ProgressBar, ProgressEnd, ProgressStart, ProgressUpdate
from frt_api.rig import RigDataHandler
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from . import lib, roles, control
from .model import SceneModel
from .utils import ui, dcc, general
from .resource import Resources
from .widgets.tab import TabWidget
from .widgets.file import FileChooser
from .widgets.tree import TreeWidget
from .widgets.graph import Node, GraphView, Connection
from .widgets.stack import Toolbar, BusyIndicatorFrame, SlidingStackedWidget
from .widgets.common import (
    QHLine,
    Section,
    Question,
    NamedSlider,
    LowerLODQuestion,
    SearchableComboBox,
    CustomPropQComboBox,
)
from .widgets.upgrade import UpgradeTool
from .widgets.bookmark import BookmarkMenu
from .widgets.settings import Settings, SettingsPanel
from .widgets.terminal import StatusObject, StatusHandler

module = sys.modules[__name__]
module.window = None  # type: ignore

logger = general.get_logger()


MODE_TITLE = {
    "main": "MetaHuman Expression Editor",
    "neutral": "Neutral Pose Editing",
    "rig": "Expression Poses Editing",
    "skin": "Skin Weights Editing",
    "settings": "Settings",
}

INI_FILE_PATH = "/maya/mhe/settings.ini"
BOOKMARKS_PATH = "/maya/mhe/bookmarks"


class CustomProgressBar(ProgressBar):
    def __init__(self, busy_frame, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.busy_frame = busy_frame

    def start(self, *args, **kwargs):
        self.busy_frame.start()
        super().start(*args, **kwargs)

    def update(self, *args, **kwargs):
        msg = f"{self.current}/{self.max_value}"
        if "status" in kwargs:
            msg += " | " + kwargs["status"]
        self.busy_frame.set_message(msg)
        super().update(*args, **kwargs)

    def end(self, *args, **kwargs):
        self.busy_frame.end()
        super().end(*args, **kwargs)


class Window(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    WINDOW_NAME = "epicmhexpressioneditor"
    WINDOW_TITLE = "MetaHuman Expression Editor"
    WINDOW_SIZE = 730, 950
    MIN_WINDOW_SIZE = 730, 950

    def __init__(self, parent=None, parent_name=None):
        dcc.delete_workspace_control(self.WINDOW_NAME + "WorkspaceControl")
        parent = parent or ui.get_main_qt_window(parent_name)
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(*self.MIN_WINDOW_SIZE)
        qstyle.install_fonts()

        self.ui = {}
        self.rig = None
        self.up_axis = None
        self.global_up_axis_rotation = [0.0, 0.0, 0.0]
        self._expression_controls_mapping = None
        self._expression_joints_mapping = None
        self._raw_to_gui = None
        SettingsPanel()
        self.controller = control.Controller()
        self.controller.set_window(self)
        self.rig_editing_active = False

        self.create_ui()
        self.resize(*self.WINDOW_SIZE)

        self.progress_bar = CustomProgressBar(self.ui["widget"]["busy_frame"])

        self.config = {}
        self.initialize()
        self.set_stylesheet()

    def keyPressEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if event.key() == QtCore.Qt.Key_F and modifiers & QtCore.Qt.ControlModifier:
            self.ui["widget"]["node_filter"].setFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    @property
    def expression_controls_mapping(self):
        if not self._expression_controls_mapping:
            self._expression_controls_mapping = lib.get_expression_analysis_mapping(
                self.rig, self.config["control_renaming"], self.config["head_turns_data"]
            )
        return self._expression_controls_mapping

    @property
    def expression_joints_mapping(self):
        if not self._expression_joints_mapping:
            self._expression_joints_mapping = lib.get_expression_joints_mapping(
                self.rig, self.config["control_renaming"], self.config["head_turns_data"]
            )
        return self._expression_joints_mapping

    @property
    def raw_to_gui(self):
        if not self._raw_to_gui:
            self._raw_to_gui = lib.get_raw_to_gui(
                self.rig, self.config["control_renaming"], self.config["head_turns_data"]
            )
            additional_gui_controls = self.config["additional_gui_controls"]
            self._raw_to_gui["gui_ctrl_names"].extend(additional_gui_controls)
        return self._raw_to_gui

    def create_ui(self):
        # ----------------------------------------------------------------------
        # Main

        main_widget = QtWidgets.QFrame(self)
        main_layout = QtWidgets.QVBoxLayout(main_widget)

        # ----------------------------------------------------------------------
        # Menu Bar
        menubar = QtWidgets.QMenuBar(parent=self)

        file_menu = QtWidgets.QMenu("File", parent=self)
        file_menu.setToolTipsVisible(True)

        save_action = file_menu.addAction("Save MetaHuman DNA", self.on_save_action)
        save_action.setToolTip("Store the MetaHuman DNA file as it is in memory")
        save_action.setEnabled(False)

        settings = file_menu.addAction("Settings", self.on_settings_action)
        settings.setToolTip("Additional Settings for the MetaHuman Expression Editor.")

        file_menu.addSeparator()
        file_menu.addAction("Close", self.on_close_action)

        tools_menu = QtWidgets.QMenu("Tools", parent=self)

        upgrade_action = tools_menu.addAction("Upgrade MetaHuman DNA", self.on_upgrade_action)
        upgrade_action.setToolTip("Run a tool to upgrade a MetaHuman DNA to the latest definition.")

        menubar.addMenu(file_menu)
        menubar.addMenu(tools_menu)
        main_layout.setMenuBar(menubar)

        # ----------------------------------------------------------------------
        # Header
        header_layout = QtWidgets.QVBoxLayout()
        header_content = QtWidgets.QHBoxLayout()

        back_btn = QtWidgets.QToolButton(self)
        back_btn.setEnabled(False)
        ui.set_icon(back_btn, "back.png")

        toolbar = Toolbar(self)
        toolbar.wrap = True

        header_content.addWidget(back_btn)
        header_content.addWidget(toolbar)

        header_layout.addLayout(header_content)
        header_layout.setSpacing(4)
        header_layout.setContentsMargins(2, 2, 2, 2)

        # ----------------------------------------------------------------------
        # Body
        body_stack = SlidingStackedWidget(self)
        body_stack.wrap = True

        load_dna_page = QtWidgets.QWidget(self)
        load_dna_page_layout = QtWidgets.QVBoxLayout(load_dna_page)

        neutral_editing_page = QtWidgets.QWidget(self)
        neutral_editing_page_layout = QtWidgets.QVBoxLayout(neutral_editing_page)

        rig_editing_page = QtWidgets.QWidget(self)
        rig_editing_page_layout = QtWidgets.QVBoxLayout(rig_editing_page)
        rig_editing_page_layout.setSpacing(0)
        rig_editing_page_layout.setContentsMargins(0, 0, 0, 0)

        skin_editing_page = QtWidgets.QWidget(self)
        skin_editing_page_main_layout = QtWidgets.QHBoxLayout(skin_editing_page)
        skin_editing_page_outline_layout = QtWidgets.QVBoxLayout(skin_editing_page)
        skin_editing_page_toolbar_layout = QtWidgets.QVBoxLayout(skin_editing_page)

        settings_page = QtWidgets.QWidget(self)
        settings_page_layout = QtWidgets.QVBoxLayout(settings_page)

        body_stack.addWidget(load_dna_page)
        body_stack.addWidget(neutral_editing_page)
        body_stack.addWidget(rig_editing_page)
        body_stack.addWidget(skin_editing_page)
        body_stack.addWidget(settings_page)

        # ----------------------------------------------------------------------
        # Main Page

        dna_file_path = FileChooser(
            "MetaHuman DNA:",
            dialog_caption="Select MetaHuman DNA file",
            dialog_filter="*.dna",
            on_changed=self.on_load_btn_clicked,
        )
        dna_file_path.fc_text_field.setDisabled(True)

        editing_modes_label = QtWidgets.QLabel("Editing modes")
        editing_modes_layout = QtWidgets.QHBoxLayout()
        neutral_editing_btn = QtWidgets.QPushButton("Neutral Pose", self)
        neutral_editing_btn.setDisabled(True)
        skin_editing_btn = QtWidgets.QPushButton("Skin Weights", self)
        skin_editing_btn.setDisabled(True)
        rig_editing_btn = QtWidgets.QPushButton("Expression Poses", self)
        rig_editing_btn.setDisabled(True)
        editing_modes_layout.addWidget(neutral_editing_btn)
        editing_modes_layout.addWidget(skin_editing_btn)
        editing_modes_layout.addWidget(rig_editing_btn)

        export_layout = QtWidgets.QVBoxLayout()
        export_label = QtWidgets.QLabel("Export FBX")
        export_body_type_layout = QtWidgets.QHBoxLayout()
        body_type_label = QtWidgets.QLabel("Body file selection:")
        export_combo_box = QtWidgets.QComboBox()
        custom_body_path = QtWidgets.QLineEdit("")
        custom_body_path.setReadOnly(True)
        custom_body_path.setVisible(False)
        export_combo_box.setDisabled(True)
        export_up_axis_layout = QtWidgets.QHBoxLayout()
        up_axis_label = QtWidgets.QLabel("Export up axis:")
        settings_export_up_axis_setting = Settings().get_setting("export_up_axis")
        z_up_axis_radio_btn = QtWidgets.QRadioButton("Z-up")
        z_up_axis_radio_btn.setDisabled(True)
        if settings_export_up_axis_setting == "z":
            z_up_axis_radio_btn.setChecked(True)
        z_up_axis_radio_btn.setProperty("axis", "z")
        y_up_axis_radio_btn = QtWidgets.QRadioButton("Y-up")
        y_up_axis_radio_btn.setDisabled(True)
        if settings_export_up_axis_setting == "y":
            y_up_axis_radio_btn.setChecked(True)
        y_up_axis_radio_btn.setProperty("axis", "y")
        export_radio_button_layout = QtWidgets.QHBoxLayout()
        export_radio_button_layout.addWidget(y_up_axis_radio_btn)
        export_radio_button_layout.addWidget(z_up_axis_radio_btn)
        export_radio_button_group = QtWidgets.QButtonGroup()
        export_radio_button_group.addButton(y_up_axis_radio_btn)
        export_radio_button_group.addButton(z_up_axis_radio_btn)
        export_radio_button_group.buttonPressed.connect(self.export_up_axis_button_pressed)
        export_up_axis_layout.addWidget(up_axis_label)
        export_up_axis_layout.addLayout(export_radio_button_layout)
        export_up_axis_layout.setStretch(0, 1)
        export_up_axis_layout.setStretch(1, 2)
        export_btn = QtWidgets.QPushButton("Export All", self)
        export_btn.setDisabled(True)
        export_body_type_layout.addWidget(body_type_label)
        export_body_type_layout.addWidget(export_combo_box)
        export_body_type_layout.setStretch(0, 1)
        export_body_type_layout.setStretch(1, 2)
        export_layout.addWidget(export_label)
        export_layout.addLayout(export_body_type_layout)
        export_layout.addLayout(export_up_axis_layout)
        export_layout.addWidget(custom_body_path)
        export_layout.addWidget(export_btn)

        load_dna_page_layout.addWidget(dna_file_path)
        load_dna_page_layout.addWidget(QHLine())
        load_dna_page_layout.addWidget(editing_modes_label)
        load_dna_page_layout.addLayout(editing_modes_layout)
        load_dna_page_layout.addWidget(QHLine())
        load_dna_page_layout.addLayout(export_layout)
        load_dna_page_layout.setAlignment(QtCore.Qt.AlignTop)
        load_dna_page_layout.setSpacing(4)
        load_dna_page_layout.setContentsMargins(2, 2, 2, 2)

        # ----------------------------------------------------------------------
        # Neutral Pose Editing Mode

        # Geometry
        neutral_geo_section = Section(self, "Geometry", collapsed=False)
        neutral_geo_view = TreeWidget(self)
        neutral_geo_section.addWidget(neutral_geo_view)

        # Joints
        neutral_jnt_section = Section(self, "Joints", collapsed=False)
        neutral_jnt_view = TreeWidget(self)
        neutral_jnt_section.addWidget(neutral_jnt_view)

        # Layout
        neutral_editing_page_layout.addWidget(neutral_geo_section)
        neutral_editing_page_layout.addWidget(neutral_jnt_section)
        neutral_editing_page_layout.setAlignment(QtCore.Qt.AlignTop)
        neutral_editing_page_layout.setSpacing(4)
        neutral_editing_page_layout.setContentsMargins(2, 2, 2, 2)

        # Tools
        load_assemble_btn = toolbar.add_tool(
            "AssembleSelectedLODs",
            "assemble_lods.svg",
            "Assemble selected LODs",
            page=1,
        )
        toolbar.add_separator(page=1)
        transfer_vtx_pos_btn = toolbar.add_tool(
            "TransferVertexPos",
            "transfer_vertex_positions.svg",
            "Transfer vertex positions",
            page=1,
        )
        update_neutral_meshes_btn = toolbar.add_tool("UpdateVertices", "update_vertices.svg", "Update vertices", page=1)
        update_neutral_joints_btn = toolbar.add_tool("UpdateJoints", "update_joints.svg", "Update joints", page=1)
        toolbar.add_separator(page=1)
        save_dna_btn = toolbar.add_tool("SaveMHDNA", "save_dna.svg", "Save MetaHuman DNA", page=1, highlight=True)

        # ----------------------------------------------------------------------
        # Skin Weights Editing Mode

        # Geometry
        skin_geo_section = Section(self, "Geometry", collapsed=False)
        skin_geo_view = TreeWidget(self)
        skin_geo_section.addWidget(skin_geo_view)

        # Joints
        skin_jnt_section = Section(self, "Joints", collapsed=False)
        skin_jnt_view = TreeWidget(self)
        skin_jnt_section.addWidget(skin_jnt_view)

        skin_editing_side_toolbar = Toolbar(self, vertical_mode=True)
        skin_editing_side_toolbar.wrap = True

        # Layout
        skin_editing_page_outline_layout.addWidget(skin_geo_section)
        skin_editing_page_outline_layout.addWidget(skin_jnt_section)
        skin_editing_page_outline_layout.setAlignment(QtCore.Qt.AlignTop)
        skin_editing_page_outline_layout.setSpacing(0)
        skin_editing_page_outline_layout.setContentsMargins(0, 0, 0, 0)

        skin_editing_page_main_layout.addLayout(skin_editing_page_outline_layout)
        skin_editing_page_main_layout.addLayout(skin_editing_page_toolbar_layout)
        skin_editing_page_main_layout.setAlignment(QtCore.Qt.AlignTop)
        skin_editing_page_main_layout.setSpacing(4)
        skin_editing_page_main_layout.setContentsMargins(2, 2, 2, 2)

        # Tools
        load_assemble_skin_btn = toolbar.add_tool(
            "AssembleSelectedLODsSkin",
            "assemble_lods.svg",
            "Assemble selected LODs",
            page=3,
        )
        toolbar.add_separator(page=3)

        mirror_skin_direction_btn = skin_editing_side_toolbar.add_tool(
            "ChooseDirectionSkinWeights",
            "direction_LtoR.svg",
            "Choose direction for the mirror, left to right or right to left.",
        )
        mirror_skin_direction_btn.setProperty("direction", general.Direction.LEFT_TO_RIGHT)

        mirror_skin_btn = skin_editing_side_toolbar.add_tool(
            "MirrorSkinWeights",
            "mirror_skin_LtoR.svg",
            "Mirror skinning on selected mesh or vertices. The user needs to choose which mesh symmetry data should be used to mirror the skin weights.",
        )

        mirror_skin_menu = QtWidgets.QMenu(parent=self)
        mirror_skin_btn.setMenu(mirror_skin_menu)
        mirror_skin_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        mirror_skin_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click
        mirror_skin_btn.clicked.connect(
            lambda: mirror_skin_menu.exec_(mirror_skin_btn.mapToGlobal(QtCore.QPoint(0, mirror_skin_btn.height())))
        )

        mirror_skin_direction_btn.setProperty(
            "dependent_buttons",
            {
                mirror_skin_btn: {
                    "LtoR": "mirror_skin_LtoR.svg",
                    "RtoL": "mirror_skin_RtoL.svg",
                }
            },
        )

        skin_editing_side_toolbar.add_separator(page=0)

        analyze_skin_mirroring_btn = skin_editing_side_toolbar.add_tool(
            "AnalyzeSkinMirroring",
            "analyze_skin.svg",
            "Analyze skin mirroring data.",
        )
        analyze_skin_mirroring_menu = QtWidgets.QMenu(parent=self)
        analyze_skin_mirroring_btn.setMenu(analyze_skin_mirroring_menu)
        analyze_skin_mirroring_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        analyze_skin_mirroring_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click
        analyze_skin_mirroring_btn.clicked.connect(
            lambda: analyze_skin_mirroring_menu.exec_(
                analyze_skin_mirroring_btn.mapToGlobal(QtCore.QPoint(0, analyze_skin_mirroring_btn.height()))
            )
        )

        toggle_vertex_shading_btn = skin_editing_side_toolbar.add_tool(
            "ToggleVertexShading",
            "disable_vertex_shading.svg",
            "Toggles vertex shading for a selected mesh.",
        )

        save_dna_skin_btn = toolbar.add_tool(
            "SaveDNASkin",
            "save_dna.svg",
            "Update from scene contents then save MetaHuman DNA file",
            page=3,
            highlight=True,
        )

        skin_editing_page_toolbar_layout.addWidget(skin_editing_side_toolbar)
        skin_editing_page_toolbar_layout.setAlignment(QtCore.Qt.AlignTop)
        skin_editing_page_toolbar_layout.setSpacing(0)
        skin_editing_page_toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # ----------------------------------------------------------------------
        # Expression Poses Editing Mode

        # Side toolbar
        side_toolbar = Toolbar(self, vertical_mode=True)
        side_toolbar.wrap = True

        # side tools
        direction_btn = side_toolbar.add_tool(
            "ChooseDirection",
            "direction_LtoR.svg",
            "Choose direction for mirror functionalities, left to right or right to left.",
        )
        direction_btn.setProperty("direction", general.Direction.LEFT_TO_RIGHT)

        mirror_mesh_btn = side_toolbar.add_tool(
            "MirrorMesh", "mirror_vertices_LtoR.svg", "Mirror selected sculpt mesh in the Geometry tree."
        )
        mirror_mesh_menu = QtWidgets.QMenu(parent=self)
        mirror_mesh_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        mirror_mesh_btn.setMenu(mirror_mesh_menu)
        mirror_mesh_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click
        mirror_mesh_btn.clicked.connect(
            lambda: mirror_mesh_menu.exec_(mirror_mesh_btn.mapToGlobal(QtCore.QPoint(0, mirror_mesh_btn.height())))
        )

        mirror_jnt_btn = side_toolbar.add_tool(
            "MirrorJnt",
            "mirror_joints_LtoR.svg",
            "Mirror selected editable joints. If no editable joints are selected, all editable joints are mirrored.",
        )

        direction_btn.setProperty(
            "dependent_buttons",
            {
                mirror_mesh_btn: {
                    "LtoR": "mirror_vertices_LtoR.svg",
                    "RtoL": "mirror_vertices_RtoL.svg",
                },
                mirror_jnt_btn: {
                    "LtoR": "mirror_joints_LtoR.svg",
                    "RtoL": "mirror_joints_RtoL.svg",
                },
            },
        )

        side_toolbar.add_separator(0)

        flip_mesh_btn = side_toolbar.add_tool(
            "FlipMesh", "flip_vertices.svg", "Flip selected sculpt mesh in the Geometry tree."
        )
        flip_mesh_menu = QtWidgets.QMenu(parent=self)
        flip_mesh_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        flip_mesh_btn.setMenu(flip_mesh_menu)
        flip_mesh_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click
        flip_mesh_btn.clicked.connect(
            lambda: flip_mesh_menu.exec_(flip_mesh_btn.mapToGlobal(QtCore.QPoint(0, flip_mesh_btn.height())))
        )

        side_toolbar.add_tool(
            "FlipJnt",
            "flip_joints.svg",
            "Flip selected editable joints. If no editable joints are selected, all editable joints are flipped.",
        )
        side_toolbar.add_separator(0)
        side_toolbar.add_tool(
            "TransferVtx",
            "transfer_vertex_positions.svg",
            "Transfer vertex positions from a mesh in the scene to a sculpt mesh in the Geometry tree.",
        )
        side_toolbar.add_tool(
            "DeleteHistory",
            "delete_history.png",
            "Delete history on the selected sculpt mesh in the Geometry tree. If no sculpt is selected, history is deleted on all sculpt meshes.",
        )
        side_toolbar.add_separator(0)
        neutralize_mesh_btn = side_toolbar.add_tool(
            "SetMeshToNeutral",
            "reset_vertices_to_neutral.svg",
            "Reset selected editable mesh to neutral. If vertices are selected, only those vertices will be reset.",
        )
        neutralize_mesh_menu = QtWidgets.QMenu(parent=self)
        neutralize_mesh_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        neutralize_mesh_btn.setMenu(neutralize_mesh_menu)
        neutralize_mesh_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click
        neutralize_mesh_btn.clicked.connect(
            lambda: neutralize_mesh_menu.exec_(
                neutralize_mesh_btn.mapToGlobal(QtCore.QPoint(0, neutralize_mesh_btn.height()))
            )
        )
        side_toolbar.add_tool(
            "SetJointsToNeutral",
            "reset_joints.svg",
            "Reset selected editable joints to the bind pose. If no editable joints are selected, all editable joints are reset to the bind pose.",
        )
        side_toolbar.add_separator(0)
        reset_mesh_to_dna_btn = side_toolbar.add_tool(
            "SetMeshToDNA",
            "reset_vertices_to_dna.svg",
            "Reset selected editable mesh to the original pose in the MetaHuman DNA. If vertices are selected, only those vertices will be reset.",
        )
        reset_mesh_to_dna_menu = QtWidgets.QMenu(parent=self)
        reset_mesh_to_dna_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        reset_mesh_to_dna_btn.setMenu(reset_mesh_to_dna_menu)
        reset_mesh_to_dna_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click
        reset_mesh_to_dna_btn.clicked.connect(
            lambda: reset_mesh_to_dna_menu.exec_(
                reset_mesh_to_dna_btn.mapToGlobal(QtCore.QPoint(0, reset_mesh_to_dna_btn.height()))
            )
        )
        side_toolbar.add_tool(
            "SetJointsToDNA",
            "reset_joints_to_dna.svg",
            "Reset selected editable joints to the original pose in the MetaHuman DNA. If no editable joints are selected, all editable joints are reset to the pose in the MetaHuman DNA.",
        )
        side_toolbar.add_separator(0)
        side_toolbar.add_tool(
            "CopyJoints",
            "copy_joints.svg",
            "Copy joint state from the edit group.",
        )
        side_toolbar.add_tool(
            "PasteJoints",
            "paste_joints.svg",
            "Paste copied joint state from the edit group. If no editable joints are selected, all editable joints will get the copied values.",
        )
        side_toolbar.add_separator(0)
        side_toolbar.add_tool(
            "RunMLJointsMatchingInScene",
            "run_ml_joints_matching.svg",
            "Run ML Joints Matching and update joints in scene. First execution needs to load the model and this can take a few minutes.",
        )
        side_toolbar.setVisible(False)

        # JM part
        jm_section = QtWidgets.QGroupBox("Joints Matching")
        jm_layout = QtWidgets.QHBoxLayout()
        jm_layout.setContentsMargins(0, 0, 0, 0)
        jm_preset_list = CustomPropQComboBox(self)
        run_jm_btn = QtWidgets.QPushButton("Run NLS Joints Matching")
        jm_layout.addWidget(jm_preset_list)
        jm_layout.addWidget(run_jm_btn)
        jm_main_layout = QtWidgets.QVBoxLayout()
        jm_main_layout.addLayout(jm_layout)
        run_ml_jm_btn = QtWidgets.QPushButton("Run ML Joints Matching")
        jm_main_layout.addWidget(run_ml_jm_btn)
        jm_section.setLayout(jm_main_layout)

        # Graph
        node_filter = SearchableComboBox(self)

        graph_view = TabWidget()
        graph_view.tabCloseRequested.connect(self.delete_subselection)
        graph_view.setTabsClosable(True)
        graph_view.currentChanged.connect(self.on_tab_change)

        # Slider
        expression_controls_section = Section(self, collapsed=True)
        expression_controls_section.setVisible(False)
        global_slider = NamedSlider("Global")
        global_slider.add_phase_buttons(
            self.controller.previous_phase_button_clicked, self.controller.next_phase_button_clicked
        )
        expression_controls_section.addWidget(global_slider)

        # Geometry
        rig_geo_section = Section(self, "Geometry", collapsed=False)
        rig_geo_view = TreeWidget(self)
        rig_geo_section.addWidget(rig_geo_view)
        rig_geo_section.setVisible(False)

        # Joints
        rig_jnt_section = Section(self, "Joints", collapsed=False)
        rig_jnt_view = TreeWidget(self)
        rig_jnt_section.addWidget(rig_jnt_view)
        rig_jnt_section.setVisible(False)

        # bookmarks
        bookmarks_btn = QtWidgets.QToolButton()
        bookmarks_btn.setStyleSheet("::menu-indicator{ image: url(icon:menu_indicator.png); }")
        ui.set_icon(bookmarks_btn, "bookmarks_mid_empty.svg")
        bookmarks_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)  # Show menu instantly on click

        bookmark_menu = BookmarkMenu(self)
        bookmarks_btn.setMenu(bookmark_menu)

        bookmarks_btn.clicked.connect(
            lambda: bookmark_menu.exec_(bookmarks_btn.mapToGlobal(QtCore.QPoint(0, bookmarks_btn.height())))
        )

        # Preview
        preview_btn = QtWidgets.QToolButton()
        ui.set_icon(preview_btn, "preview_selected_nodes.svg")
        preview_btn.clicked.connect(self.on_preview_btn_clicked)
        preview_btn.setVisible(False)
        preview_btn.setToolTip("Create preview sculpt meshes of the selected downstream expressions.")

        # Preview
        preview_unlocked_btn = QtWidgets.QToolButton()
        ui.set_icon(preview_unlocked_btn, "preview_unlocked_nodes.svg")
        preview_unlocked_btn.clicked.connect(self.on_preview_unlocked_btn_clicked)
        preview_unlocked_btn.setVisible(False)
        preview_unlocked_btn.setToolTip("Create preview sculpt meshes of unlocked downstream expressions.")

        # Delete Preview Meshes
        delete_preview_btn = QtWidgets.QToolButton()
        ui.set_icon(delete_preview_btn, "remove_preview_meshes.svg")
        delete_preview_btn.clicked.connect(self.on_delete_preview_btn_clicked)
        delete_preview_btn.setVisible(False)
        delete_preview_btn.setToolTip("Delete preview meshes.")

        # layout
        rig_editing_page_layout.addWidget(jm_section)
        rig_editing_page_layout.addWidget(node_filter)

        graph_view_layout = QtWidgets.QHBoxLayout()
        graph_view_layout.setSpacing(4)
        graph_view_layout.setContentsMargins(2, 2, 2, 2)
        graph_view_layout.setAlignment(QtCore.Qt.AlignTop)

        graph_view_right_layout = QtWidgets.QVBoxLayout()
        graph_view_right_layout.setSpacing(0)
        graph_view_right_layout.setContentsMargins(0, 0, 0, 0)
        graph_view_right_layout.setAlignment(QtCore.Qt.AlignTop)
        graph_view_right_layout.addWidget(bookmarks_btn)
        graph_view_right_layout.addWidget(preview_btn)
        graph_view_right_layout.addWidget(preview_unlocked_btn)
        graph_view_right_layout.addWidget(delete_preview_btn)

        graph_view_layout.addWidget(graph_view)
        graph_view_layout.addLayout(graph_view_right_layout)

        rig_editing_page_layout.addLayout(graph_view_layout)

        expression_poses_editing_editing_layout = QtWidgets.QHBoxLayout()
        expression_poses_editing_editing_layout.setSpacing(0)
        expression_poses_editing_editing_layout.setContentsMargins(0, 0, 0, 0)

        expression_poses_editing_tree_view_layout = QtWidgets.QVBoxLayout()
        expression_poses_editing_tree_view_layout.setSpacing(4)
        expression_poses_editing_tree_view_layout.setContentsMargins(0, 0, 0, 0)
        expression_poses_editing_tree_view_layout.addWidget(expression_controls_section)
        expression_poses_editing_tree_view_layout.addWidget(rig_geo_section)
        expression_poses_editing_tree_view_layout.addWidget(rig_jnt_section)

        expression_poses_editing_toolbar_layout = QtWidgets.QVBoxLayout()
        expression_poses_editing_toolbar_layout.setSpacing(0)
        expression_poses_editing_toolbar_layout.setContentsMargins(2, 2, 2, 2)
        expression_poses_editing_toolbar_layout.addWidget(side_toolbar)

        expression_poses_editing_editing_layout.addLayout(expression_poses_editing_tree_view_layout)
        expression_poses_editing_editing_layout.addLayout(expression_poses_editing_toolbar_layout)

        rig_editing_page_layout.addLayout(expression_poses_editing_editing_layout)
        rig_editing_page_layout.setAlignment(QtCore.Qt.AlignTop)
        rig_editing_page_layout.setSpacing(4)
        rig_editing_page_layout.setContentsMargins(2, 2, 2, 2)

        # Tools
        rig_assemble_btn = toolbar.add_tool("AssembleScene", "assemble_scene.svg", "Assemble scene", page=2)
        toolbar.add_separator(page=2)
        toolbar.add_tool(
            "LoadAnimationGUI",
            "load_faceboard_anim.svg",
            "Load faceboard Animation",
            page=2,
        )
        toolbar.add_tool(
            "LoadAnimationRAW",
            "load_riglogic_anim.svg",
            "Load RigLogic raw animation",
            page=2,
        )
        toolbar.add_tool("AnalyzeCurrentFrame", "analyze_frame.svg", "Analyze current frame", page=2)
        toolbar.add_separator(page=2)
        start_editing_btn = toolbar.add_tool(
            "ToggleEditing", "edit_expr_start.svg", "Edit selected expressions", page=2
        )
        toolbar.add_separator(page=2)
        update_save_dna_rig_btn = toolbar.add_tool(
            "UpdateSaveDNA", "update_dna.svg", "Update MetaHuman DNA from scene", page=2
        )
        save_dna_rig_btn = toolbar.add_tool(
            "SaveMHDNA",
            "save_dna.svg",
            "Save MetaHuman DNA",
            page=2,
            highlight=True,
        )

        # ----------------------------------------------------------------------
        # Settings
        settings_tabs = QtWidgets.QTabWidget()

        # General settings
        general_frame = QtWidgets.QFrame()
        general_layout = QtWidgets.QVBoxLayout(general_frame)
        settings_tabs.addTab(general_frame, "General")
        save_load_group = QtWidgets.QGroupBox("Save/Load Settings")
        general_layout.addWidget(save_load_group)
        save_load_layout = QtWidgets.QVBoxLayout()
        save_load_group.setLayout(save_load_layout)
        auto_load_dna_cb = QtWidgets.QCheckBox("Automatically load a saved MetaHuman DNA.")
        auto_load_dna_cb.setChecked(Settings().get_setting("auto_load_dna"))
        save_load_layout.addWidget(auto_load_dna_cb)
        up_axis_group = QtWidgets.QGroupBox("Up Axis")
        general_layout.addWidget(up_axis_group)
        up_axis_layout = QtWidgets.QVBoxLayout()
        up_axis_button_layout = QtWidgets.QHBoxLayout()
        up_axis_group.setLayout(up_axis_layout)
        up_axis_label = QtWidgets.QLabel("Up Axis:")
        settings_up_axis_value = Settings().get_setting("general_up_axis")
        settings_dna_up_axis_radio_btn = QtWidgets.QRadioButton("From MetaHuman DNA")
        settings_dna_up_axis_radio_btn.setProperty("axis", "dna")
        if settings_up_axis_value == "dna":
            settings_dna_up_axis_radio_btn.setChecked(True)
        settings_y_up_axis_radio_btn = QtWidgets.QRadioButton("Y-up")
        settings_y_up_axis_radio_btn.setProperty("axis", "y")
        if settings_up_axis_value == "y":
            settings_y_up_axis_radio_btn.setChecked(True)
        settings_z_up_axis_radio_btn = QtWidgets.QRadioButton("Z-up")
        settings_z_up_axis_radio_btn.setProperty("axis", "z")
        if settings_up_axis_value == "z":
            settings_z_up_axis_radio_btn.setChecked(True)
        settings_up_axis_button_group = QtWidgets.QButtonGroup()
        settings_up_axis_button_group.addButton(settings_dna_up_axis_radio_btn)
        settings_up_axis_button_group.addButton(settings_y_up_axis_radio_btn)
        settings_up_axis_button_group.addButton(settings_z_up_axis_radio_btn)
        settings_axis_waring_label = QtWidgets.QLabel(
            "Note: Up axis updates require a MetaHuman DNA reload to be applied."
        )
        settings_axis_waring_label.setStyleSheet("color: #FDD77C")

        up_axis_button_layout.addWidget(up_axis_label)
        up_axis_button_layout.addWidget(settings_dna_up_axis_radio_btn)
        up_axis_button_layout.addWidget(settings_y_up_axis_radio_btn)
        up_axis_button_layout.addWidget(settings_z_up_axis_radio_btn)
        up_axis_layout.addLayout(up_axis_button_layout)
        up_axis_layout.addWidget(settings_axis_waring_label)
        general_layout.addStretch()

        # Graph settings
        expression_poses_frame = QtWidgets.QFrame()
        expression_poses_layout = QtWidgets.QVBoxLayout(expression_poses_frame)
        settings_tabs.addTab(expression_poses_frame, "Expression Poses")
        graph_settings_group = QtWidgets.QGroupBox("Graph Settings")
        expression_poses_layout.addWidget(graph_settings_group)
        graph_settings_layout = QtWidgets.QVBoxLayout()
        graph_settings_group.setLayout(graph_settings_layout)
        user_bookmarks_settings = FileChooser(
            "User Bookmarks Directory:", dialog_caption="Select User Bookmarks Directory", dir_selector=True
        )
        user_bookmarks_settings.fc_text_field.setDisabled(True)
        user_bookmarks_settings.set_file_path(Settings().get_setting("bookmarks_directory"))
        graph_settings_layout.addWidget(user_bookmarks_settings)

        graph_advanced_settings_group = QtWidgets.QGroupBox("Advanced Graph Settings")
        expression_poses_layout.addWidget(graph_advanced_settings_group)
        graph_advanced_settings_layout = QtWidgets.QVBoxLayout()
        graph_advanced_settings_group.setLayout(graph_advanced_settings_layout)
        advanced_propagation_settings_cb = QtWidgets.QCheckBox("Enable advanced propagation settings.")
        advanced_propagation_settings_cb.setChecked(Settings().get_setting("advanced_propagation"))
        graph_advanced_settings_layout.addWidget(advanced_propagation_settings_cb)
        expression_poses_layout.addStretch()

        settings_page_layout.addWidget(settings_tabs)
        save_settings_btn = QtWidgets.QPushButton("Save Settings")
        save_settings_btn.clicked.connect(lambda: self.on_save_settings_clicked(self.config))
        settings_page_layout.addWidget(save_settings_btn)
        settings_page_layout.setAlignment(QtCore.Qt.AlignTop)
        settings_page_layout.setSpacing(4)
        settings_page_layout.setContentsMargins(2, 2, 2, 2)

        # ----------------------------------------------------------------------
        # Footer
        footer_layout = QtWidgets.QHBoxLayout()

        status_object = StatusObject()
        self.status_handler = StatusHandler(self, status_object)
        logger.addHandler(self.status_handler)
        status_line = self.status_handler.widget

        mode_title = QtWidgets.QLabel(MODE_TITLE["main"])
        mode_title.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        footer_layout.addWidget(status_line)
        footer_layout.addWidget(mode_title)
        footer_layout.setSpacing(4)
        footer_layout.setContentsMargins(2, 2, 2, 2)

        # ----------------------------------------------------------------------
        # Main layout

        main_layout.addLayout(header_layout)
        main_layout.addWidget(QHLine())
        main_layout.addWidget(body_stack)
        main_layout.addWidget(QHLine())
        main_layout.addLayout(footer_layout)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        self.setAutoFillBackground(True)

        # ----------------------------------------------------------------------
        # App layout

        app_layout = QtWidgets.QStackedLayout()

        # Busy indicator
        busy_frame = BusyIndicatorFrame(self)

        app_layout.addWidget(busy_frame)
        app_layout.addWidget(main_widget)
        app_layout.setStackingMode(QtWidgets.QStackedLayout.StackAll)

        self.setLayout(app_layout)
        busy_frame.end()

        # ----------------------------------------------------------------------
        # Controls

        self.ui = {
            "stack": {
                "body": body_stack,
            },
            "page": {
                "main": load_dna_page,
                "neutral": neutral_editing_page,
                "rig": rig_editing_page,
                "skin": skin_editing_page,
                "settings": settings_page,
            },
            "menu": {
                "file": file_menu,
                "mirror_skin": mirror_skin_menu,
                "analyze_skin_mirroring": analyze_skin_mirroring_menu,
                "mirror_mesh": mirror_mesh_menu,
                "flip_mesh": flip_mesh_menu,
                "neutralize_mesh": neutralize_mesh_menu,
                "reset_mesh_to_dna": reset_mesh_to_dna_menu,
            },
            "widget": {
                "busy_frame": busy_frame,
                "toolbar": toolbar,
                "graph": graph_view,
                "rig_geo_section": rig_geo_section,
                "rig_jnt_section": rig_jnt_section,
                "rig_toolbar": side_toolbar,
                "node_filter": node_filter,
                "mode_title": mode_title,
                "dna_file_path": dna_file_path,
                "neutral_geo_view": neutral_geo_view,
                "neutral_jnt_view": neutral_jnt_view,
                "skin_geo_view": skin_geo_view,
                "skin_jnt_view": skin_jnt_view,
                "rig_geo_view": rig_geo_view,
                "rig_jnt_view": rig_jnt_view,
                "status": status_line,
                "expression_controls_section": expression_controls_section,
                "global_slider": global_slider,
                "export_combo_box": export_combo_box,
                "custom_body_path": custom_body_path,
                "z_up_axis": z_up_axis_radio_btn,
                "y_up_axis": y_up_axis_radio_btn,
                "export_axis_group": export_radio_button_group,
                "jm_preset_list": jm_preset_list,
                "bookmark_menu": bookmark_menu,
            },
            "button": {
                "back": back_btn,
                "neutral": neutral_editing_btn,
                "rig": rig_editing_btn,
                "export": export_btn,
                "skin": skin_editing_btn,
                "load_assemble": load_assemble_btn,
                "transfer": transfer_vtx_pos_btn,
                "update_neutral_meshes": update_neutral_meshes_btn,
                "update_neutral_joints": update_neutral_joints_btn,
                "save_dna": save_dna_btn,
                "rig_assemble": rig_assemble_btn,
                "start_editing": start_editing_btn,
                "save_mh_dna": save_dna_rig_btn,
                "update_save_rig": update_save_dna_rig_btn,
                "load_assemble_skin": load_assemble_skin_btn,
                "analyze_skin_mirroring": analyze_skin_mirroring_btn,
                "toggle_vertex_shading": toggle_vertex_shading_btn,
                "save_dna_skin": save_dna_skin_btn,
                "run_jm": run_jm_btn,
                "run_ml_jm": run_ml_jm_btn,
                "choose_direction": direction_btn,
                "choose_direction_skin": mirror_skin_direction_btn,
                "bookmark": bookmarks_btn,
                "preview": preview_btn,
                "preview_unlocked": preview_unlocked_btn,
                "delete_preview": delete_preview_btn,
                "mirror_mesh": mirror_mesh_btn,
                "flip_mesh": flip_mesh_btn,
                "mirror_skin": mirror_skin_btn,
                "neutralize_mesh": neutralize_mesh_btn,
                "reset_mesh_to_dna": reset_mesh_to_dna_btn,
            },
            "settings": {
                "auto_load_dna": auto_load_dna_cb,
                "bookmarks_dir": user_bookmarks_settings,
                "advanced_propagation": advanced_propagation_settings_cb,
                "up_axis": settings_up_axis_button_group,
            },
            "layout": {"export_layout": export_layout, "bookmark_layout": graph_view_right_layout},
        }
        # ----------------------------------------------------------------------
        # Signals

        self.ui["stack"]["body"].currentChanged.connect(self.on_page_changed)
        self.ui["stack"]["body"].animationFinished.connect(self.on_page_animation_finished)

        self.ui["button"]["back"].clicked.connect(self.on_back_clicked)
        self.ui["button"]["neutral"].clicked.connect(self.on_neutral_editing_clicked)
        self.ui["button"]["rig"].clicked.connect(self.on_rig_editing_clicked)
        self.ui["button"]["skin"].clicked.connect(self.on_skin_editing_clicked)
        self.ui["button"]["export"].clicked.connect(self.on_export_clicked)
        self.ui["button"]["load_assemble"].clicked.connect(self.on_load_assemble_btn_clicked)
        self.ui["button"]["update_neutral_meshes"].clicked.connect(self.on_update_neutral_meshes_clicked)
        self.ui["button"]["update_neutral_joints"].clicked.connect(self.on_update_neutral_joints_clicked)
        self.ui["button"]["save_dna"].clicked.connect(self.on_save_dna_neutral_clicked)
        self.ui["button"]["transfer"].clicked.connect(
            lambda: self.controller.transfer_vtx(self.ui["widget"]["neutral_geo_view"])
        )
        self.ui["button"]["rig_assemble"].clicked.connect(self.on_rig_assemble_btn_clicked)
        self.ui["button"]["save_mh_dna"].clicked.connect(self.on_save_action)
        self.ui["button"]["run_jm"].clicked.connect(lambda: self.on_run_jm())
        self.ui["button"]["run_ml_jm"].clicked.connect(self.on_run_ml_joints_matching_on_rig)
        self.ui["button"]["update_save_rig"].clicked.connect(lambda: self.on_update_save_rig())
        self.ui["button"]["load_assemble_skin"].clicked.connect(self.on_load_assemble_skin_btn_clicked)
        self.ui["button"]["toggle_vertex_shading"].clicked.connect(self.on_toggle_vertex_shading_btn_clicked)
        self.ui["button"]["save_dna_skin"].clicked.connect(self.on_save_dna_skin_clicked)
        self.ui["button"]["choose_direction_skin"].clicked.connect(
            lambda: self.on_choose_direction_clicked(self.ui["button"]["choose_direction_skin"])
        )

        self.ui["widget"]["node_filter"].textActivated.connect(self.focus_node)

        toolbar.get_button("ToggleEditing").clicked.connect(self.on_toggle_editing_clicked)
        toolbar.get_button("AnalyzeCurrentFrame").clicked.connect(self.on_analyze_frame_clicked)
        toolbar.get_button("LoadAnimationGUI").clicked.connect(lambda: self.animation_dialog("gui"))
        toolbar.get_button("LoadAnimationRAW").clicked.connect(lambda: self.animation_dialog("raw"))

        # side actions
        direction_btn.clicked.connect(lambda: self.on_choose_direction_clicked(self.ui["button"]["choose_direction"]))
        side_toolbar.get_button("TransferVtx").clicked.connect(self.on_transfer_vtx_clicked)
        side_toolbar.get_button("DeleteHistory").clicked.connect(self.on_delete_history_clicked)
        side_toolbar.get_button("MirrorJnt").clicked.connect(self.on_mirror_jnt_clicked)
        side_toolbar.get_button("FlipJnt").clicked.connect(self.on_flip_jnt_clicked)
        side_toolbar.get_button("SetJointsToNeutral").clicked.connect(self.on_neutralize_jnt_clicked)
        side_toolbar.get_button("SetJointsToDNA").clicked.connect(self.on_reset_jnt_to_dna_clicked)
        side_toolbar.get_button("CopyJoints").clicked.connect(self.on_copy_joints_clicked)
        side_toolbar.get_button("PasteJoints").clicked.connect(lambda: self.controller.paste_joints(self.rig))
        side_toolbar.get_button("RunMLJointsMatchingInScene").clicked.connect(
            self.on_run_ml_joints_matching_in_scene_clicked
        )
        global_slider.valueChanged.connect(self.slider_value_changed)

        self.ui["widget"]["export_combo_box"].activated.connect(self.select_custom_body)

        # ----------------------------------------------------------------------
        # Name
        names = {
            "ModeLabel": mode_title,
            "BackButton": back_btn,
        }
        for name, w in names.items():
            w.setObjectName(name)

    # --------------------------------------------------------------------------

    def initialize(self):
        neutral_geo_view = self.ui["widget"]["neutral_geo_view"]
        neutral_geo_view.clear()
        neutral_jnt_view = self.ui["widget"]["neutral_jnt_view"]
        neutral_jnt_view.clear()

        rig_geo_view = self.ui["widget"]["rig_geo_view"]
        rig_geo_view.clear()
        rig_jnt_view = self.ui["widget"]["rig_jnt_view"]
        rig_jnt_view.clear()

        skin_geo_view = self.ui["widget"]["skin_geo_view"]
        skin_geo_view.clear()
        skin_jnt_view = self.ui["widget"]["skin_jnt_view"]
        skin_jnt_view.clear()

        neutral_geo_view.itemClicked.connect(lambda: self.controller.from_tree_select_in_scene(neutral_geo_view))
        neutral_jnt_view.itemClicked.connect(lambda: self.controller.from_tree_select_in_scene(neutral_jnt_view))

        rig_geo_view.itemClicked.connect(lambda: self.controller.from_tree_select_in_scene(rig_geo_view))
        rig_jnt_view.itemClicked.connect(lambda: self.controller.from_tree_select_in_scene(rig_jnt_view))

        skin_geo_view.itemClicked.connect(lambda: self.controller.from_tree_select_in_scene(skin_geo_view))
        skin_jnt_view.itemClicked.connect(lambda: self.controller.from_tree_select_in_scene(skin_jnt_view))

    def _object_hierarchy_to_tree(self, view, data, select_first_item=False):
        root = view.invisibleRootItem()

        def _create_child(parent, key, value):
            child = QtWidgets.QTreeWidgetItem(parent)
            child.setExpanded(True)
            child.setText(0, key.split("|")[-1])
            child.setData(0, roles.ITEM_NAME, key)
            child.setData(0, roles.ITEM_VISIBLE, True)
            child.setData(0, roles.ITEM_LOADED, False)
            child.setData(0, roles.ITEM_SELECTABLE, True)
            if isinstance(value, bool):
                if value:
                    child.setData(0, roles.ITEM_LOADED, True)
                    child.setData(0, roles.ITEM_SELECTABLE, True)
                else:
                    child.setDisabled(True)
                    child.setData(0, roles.ITEM_LOADED, False)
                    child.setData(0, roles.ITEM_SELECTABLE, False)
            if isinstance(value, dict):
                for k, v in value.items():
                    _create_child(child, k, v)

        for _k, _v in data.items():
            _create_child(root, _k, _v)

        view.setColumnWidth(0, 300)

        if select_first_item:
            view.selectionModel().select(view.model().index(0, 0), QtCore.QItemSelectionModel.Select)

        return root

    def _initialize_view(self, view_name, data, select_first_item=False):
        view = self.ui["widget"][view_name]
        view.clear()
        self._object_hierarchy_to_tree(view, data, select_first_item)

    # --------------------------------------------------------------------------

    def slider_value_changed(self, value):
        if self.rig_editing_active:
            value = float(value) / self.ui["widget"]["global_slider"].maximum()
            self.controller.update_preview(value)

    def set_stylesheet(self):
        QtCore.QDir.addSearchPath("icon", general.resource("icon"))
        css_file = os.path.join(os.path.dirname(__file__), "style.css")
        qstyle.set_style(self, css_file)

    def closeEvent(self, event):
        logger.removeHandler(self.status_handler)
        super().closeEvent(event)

    # --------------------------------------------------------------------------

    def select_custom_body(self):
        cb = self.ui["widget"]["export_combo_box"]
        cb_path = self.ui["widget"]["custom_body_path"]
        if cb.currentIndex() == cb.count() - 1:
            path = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Select a Maya ASCII scene containing a body or a MetaHuman Body DNA",
                "",
                "Maya ASCII or MetaHuman Body DNA (*.ma *.MA, *dna, *.DNA)",
            )
            if path[0]:
                cb_path.setText(path[0])
                cb_path.setVisible(True)
            else:
                cb.setCurrentIndex(0)
                cb_path.setText("")
                cb_path.setVisible(False)
        else:
            cb_path.setText("")
            cb_path.setVisible(False)

        return

    def on_close_action(self):
        self.close()

    def on_settings_action(self):
        body_stack = self.ui["stack"]["body"]
        body_stack.slide_widget(self.ui["page"]["settings"], body_stack.RightToLeft)
        self.ui["widget"]["mode_title"].setText(MODE_TITLE["settings"])
        self.ui["button"]["back"].setEnabled(True)

    def export_up_axis_button_pressed(self, button):
        Settings.set_setting("export_up_axis", button.property("axis"))

    def on_upgrade_action(self):
        from mh_upgrade.mh4_to_mh6 import UpgradeHandler

        upgrade_dialog = UpgradeTool(UpgradeHandler, self)
        upgrade_dialog.show()

    def on_page_changed(self, index):
        toolbar = self.ui["widget"]["toolbar"]
        toolbar.set_page(index)

    def on_page_animation_finished(self):
        stack = self.ui["stack"]["body"]
        if stack.currentIndex() == 0:
            self.ui["button"]["back"].setEnabled(False)
        else:
            self.ui["button"]["back"].setEnabled(True)

    def on_back_clicked(self):
        body_stack = self.ui["stack"]["body"]
        body_stack.slide_widget(self.ui["page"]["main"], body_stack.LeftToRight)
        self.ui["widget"]["mode_title"].setText(MODE_TITLE["main"])

    def on_save_settings_clicked(self, config):
        Settings().set_setting("auto_load_dna", self.ui["settings"]["auto_load_dna"].isChecked())
        Settings().set_setting("bookmarks_directory", self.ui["settings"]["bookmarks_dir"].get_file_path())
        Settings().set_setting("advanced_propagation", self.ui["settings"]["advanced_propagation"].isChecked())
        Settings().set_setting("general_up_axis", self.ui["settings"]["up_axis"].checkedButton().property("axis"))
        Settings().set_setting(
            "export_up_axis", self.ui["widget"]["export_axis_group"].checkedButton().property("axis")
        )
        Settings().write()
        logger.info(f"Settings saved to {Settings.QSETTINGS.fileName()}.")
        self.ui["widget"]["bookmark_menu"].populate_bookmarks()
        for j in range(0, self.ui["widget"]["graph"].count()):
            self.ui["widget"]["graph"].widget(j).update_status_text()
        self.on_back_clicked()

    def on_neutral_editing_clicked(self):
        body_stack = self.ui["stack"]["body"]
        body_stack.slide_widget(self.ui["page"]["neutral"], body_stack.RightToLeft)
        self.ui["widget"]["mode_title"].setText(MODE_TITLE["neutral"])

    def on_rig_editing_clicked(self):
        body_stack = self.ui["stack"]["body"]
        body_stack.slide_widget(self.ui["page"]["rig"], body_stack.RightToLeft)
        self.ui["widget"]["mode_title"].setText(MODE_TITLE["rig"])

        jm_files = []
        self.ui["widget"]["jm_preset_list"].clear()

        for dir_path, dir_names, jm_file_names in os.walk(Resources().joints_matching_presets_folder_path):
            for f in sorted(jm_file_names):
                if f.endswith(".py"):
                    jm_files.append(os.path.join(dir_path, f).replace("\\", "/"))
                    self.ui["widget"]["jm_preset_list"].addItem(f.split(".")[0])
            break

        self.ui["widget"]["jm_preset_list"].populate_custom_list(jm_files)
        self.ui["button"]["run_jm"].setDisabled(not self.ui["widget"]["jm_preset_list"].count())
        self.ui["button"]["run_ml_jm"].setDisabled(
            not os.path.isfile(Resources().ml_joints_matching_model_description_path)
        )
        self.ui["widget"]["rig_toolbar"].get_button("RunMLJointsMatchingInScene").setDisabled(
            not os.path.isfile(Resources().ml_joints_matching_model_description_path)
        )

    def on_skin_editing_clicked(self):
        body_stack = self.ui["stack"]["body"]
        body_stack.slide_widget(self.ui["page"]["skin"], body_stack.RightToLeft)
        self.ui["widget"]["mode_title"].setText(MODE_TITLE["skin"])
        self.ui["button"]["back"].setEnabled(True)

    def on_export_clicked(self, force=False):
        if not force:
            question = Question("Export", "Create FBX and MetaHuman DNA files for engine import?", self).ask()
            if question == QtWidgets.QMessageBox.No:
                return

        cb = self.ui["widget"]["export_combo_box"]
        use_custom_body = cb.currentIndex() == cb.count() - 1
        if use_custom_body:
            if not self.ui["widget"]["custom_body_path"].text():
                logger.warning("Body file not provided.")
                return
            body_file_path = self.ui["widget"]["custom_body_path"].text()
        else:
            body_file_path = general.resource(Resources().body_scenes_folder_path, cb.currentText())

        export_folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Export Data")

        if export_folder_path:
            self.controller.export(
                self.rig,
                body_file_path,
                export_folder_path,
                Resources().dna_file_path,
                self.config["neck_joints"],
                self.up_axis,
                self.global_up_axis_rotation,
                self.ui["widget"]["export_axis_group"].checkedButton().property("axis"),
                self.config["export"][self.ui["widget"]["export_axis_group"].checkedButton().property("axis")][
                    "dna_rotation"
                ],
                self.config["export"][self.ui["widget"]["export_axis_group"].checkedButton().property("axis")][
                    "body_scene_orient"
                ],
                self.config["export"]["material_names"],
            )

    def on_load_disable_buttons(self, state):
        self.ui["button"]["neutral"].setDisabled(state)
        self.ui["button"]["rig"].setDisabled(state)
        self.ui["button"]["skin"].setDisabled(state)
        self.ui["button"]["export"].setDisabled(state)
        self.ui["widget"]["export_combo_box"].setDisabled(state)
        self.ui["widget"]["z_up_axis"].setDisabled(state)
        self.ui["widget"]["y_up_axis"].setDisabled(state)
        self.ui["menu"]["file"].actions()[0].setDisabled(state)
        if state:
            self.up_axis = None
            self.global_up_axis_rotation = [0.0, 0.0, 0.0]

    def on_load_clear_cache(self):
        self._raw_to_gui = None
        self._expression_controls_mapping = None
        self._expression_joints_mapping = None
        self.on_load_disable_buttons(False)
        self.ui["widget"]["export_combo_box"].setCurrentIndex(0)
        self.controller.fill_export_combo_box(
            self.ui["widget"]["export_combo_box"], self.ui["button"]["export"], self.rig
        )
        self.controller.clear_copied_joints()

        self.ui["widget"]["custom_body_path"].setText("")
        self.ui["widget"]["custom_body_path"].setVisible(False)

        self.ui["menu"]["analyze_skin_mirroring"].clear()
        self.ui["menu"]["mirror_skin"].clear()
        self.ui["menu"]["mirror_mesh"].clear()
        self.ui["menu"]["flip_mesh"].clear()
        self.ui["menu"]["neutralize_mesh"].clear()
        self.ui["menu"]["reset_mesh_to_dna"].clear()
        for mesh in self.rig.rig_definition.meshes:
            if mesh.name in self.rig.rig_definition.get_dna_mesh_names():
                if mesh.maya_vtx_pairs:
                    mesh_action = self.ui["menu"]["analyze_skin_mirroring"].addAction(mesh.name)
                    mesh_action.triggered.connect(
                        partial(
                            self.controller.analyze_skin_mirroring,
                            self.rig,
                            mesh.name,
                        )
                    )
                    mesh_action = self.ui["menu"]["mirror_skin"].addAction(mesh.name)
                    mesh_action.triggered.connect(
                        partial(
                            self.controller.mirror_skin,
                            self.rig,
                            mesh.name,
                        )
                    )
                    mesh_action = self.ui["menu"]["mirror_mesh"].addAction(mesh.name)
                    mesh_action.triggered.connect(
                        partial(
                            self.controller.mirror_mesh,
                            self.rig,
                            mesh.name,
                        )
                    )
                    mesh_action = self.ui["menu"]["flip_mesh"].addAction(mesh.name)
                    mesh_action.triggered.connect(
                        partial(
                            self.controller.flip_mesh,
                            self.rig,
                            mesh.name,
                        )
                    )
                if mesh.name in lib.get_sculpt_mesh_names(self.rig):
                    mesh_action = self.ui["menu"]["neutralize_mesh"].addAction(mesh.name)
                    mesh_action.triggered.connect(
                        partial(
                            self.controller.neutralize_mesh,
                            self.rig,
                            mesh.name,
                        )
                    )
                    mesh_action = self.ui["menu"]["reset_mesh_to_dna"].addAction(mesh.name)
                    mesh_action.triggered.connect(
                        partial(
                            self.controller.reset_mesh_to_dna,
                            self.rig,
                            mesh.name,
                        )
                    )

        if not self.ui["menu"]["mirror_skin"].actions():
            self.ui["button"]["analyze_skin_mirroring"].setDisabled(True)
            self.ui["button"]["mirror_mesh"].setDisabled(True)
            self.ui["button"]["flip_mesh"].setDisabled(True)
            self.ui["button"]["mirror_skin"].setDisabled(True)
            self.ui["button"]["neutralize_mesh"].setDisabled(True)
            self.ui["button"]["reset_mesh_to_dna"].setDisabled(True)

        # Neutral
        ProgressUpdate.emit(status="Populating geometry data")
        neutral_geo_view = self.ui["widget"]["neutral_geo_view"]
        neutral_geo_view.clear()
        self._object_hierarchy_to_tree(neutral_geo_view, lib.get_dna_lods(self.rig), True)

        ProgressUpdate.emit(status="Populating joins data")
        neutral_jnt_view = self.ui["widget"]["neutral_jnt_view"]
        neutral_jnt_view.clear()
        self._object_hierarchy_to_tree(neutral_jnt_view, lib.get_dna_joints(self.rig))

        # Rig
        ProgressUpdate.emit(status="Creating graph")
        self.clear_tabs()
        name, _ = os.path.splitext(os.path.basename(Resources().dna_file_path))
        self.add_graph(name, self.rig)
        self.ui["widget"]["graph"].tabBar().setTabButton(0, QtWidgets.QTabBar.RightSide, None)

        self.ui["widget"]["bookmark_menu"].populate_bookmarks()

        # Skin
        ProgressUpdate.emit(status="Populating skin data")
        skin_geo_view = self.ui["widget"]["skin_geo_view"]
        skin_geo_view.clear()
        self._object_hierarchy_to_tree(skin_geo_view, lib.get_dna_lods(self.rig), True)

        ProgressUpdate.emit(status="Populating joints data")
        skin_jnt_view = self.ui["widget"]["skin_jnt_view"]
        skin_jnt_view.clear()
        self._object_hierarchy_to_tree(skin_jnt_view, lib.get_dna_joints(self.rig))

    def on_load_btn_clicked(self, dna_file_path=None, clear_cache=True):
        ProgressStart.emit(max_value=7)

        ProgressUpdate.emit(status="Checking path")

        if not dna_file_path:
            dna_file_path = self.ui["widget"]["dna_file_path"].get_file_path()
            if not dna_file_path:
                logger.warning("No path found")
                return

        if not os.path.exists(dna_file_path):
            logger.error("File does not exist")
            ProgressEnd.emit()
            return

        if not Resources().initialize_from_dna_file(dna_file_path):
            logger.error("MetaHuman DNA format not supported.")
            self.on_load_disable_buttons(True)
            ProgressEnd.emit()
            return

        ProgressUpdate.emit(status="Initializing rig data")
        try:
            self.config = general.load_json(Resources().config_file_path)
            lib.validate_rdf_compatibility(Resources().rdf_file_path, Resources().dna_file_path)
            load_dna_file_path, self.up_axis, self.global_up_axis_rotation = lib.orient_dna(
                Resources().dna_file_path, self.ui["settings"]["up_axis"].checkedButton().property("axis")
            )
            self.rig = RigDataHandler(
                Resources().rdf_file_path,
                load_dna_file_path,
                **self.config["pruning_threshold"],
            )
            if dna_file_path != load_dna_file_path:
                self.controller.delete_file(load_dna_file_path)
            lib.add_phase_expression_view_data(self.rig, self.config["phase_expression_views"])
            self.ui["widget"]["dna_file_path"].set_file_path(dna_file_path)
        except lib.RigCompatibilityError as ex:
            error_message = f"Mismatch between the requested rig definition and the provided MetaHuman DNA. Requested rig definition: {lib.get_db_name(dna_file_path)}. Mismatch: {ex}"
            logger.error(error_message)
            self.on_load_disable_buttons(True)
            self.ui["widget"]["dna_file_path"].set_file_path("")
            ProgressEnd.emit()
            return
        except AttributeError:
            logger.error("Could not initialize rig data, MetaHuman DNA file missing geometry data.")
            self.on_load_disable_buttons(True)
            self.ui["widget"]["dna_file_path"].set_file_path("")
            ProgressEnd.emit()
            return
        except (FRTApiError, FileNotFoundError):
            logger.error(
                f"Could not initialize rig data, rig definition {lib.get_db_name(dna_file_path)} not supported."
            )
            self.on_load_disable_buttons(True)
            self.ui["widget"]["dna_file_path"].set_file_path("")
            ProgressEnd.emit()
            return
        with contextlib.suppress(KeyError):
            head_turns_data = self.config["head_turns_data"]
            lib.add_neck_rotations(
                self.rig, head_turns_data["main_expressions"], head_turns_data["neck_joints_animation"]
            )

        if clear_cache:
            self.on_load_clear_cache()
        else:
            name, _ = os.path.splitext(os.path.basename(Resources().dna_file_path))
            self.ui["widget"]["graph"].setTabText(0, name)

        self.controller.initialize_ml_joints_matching_handler(self.rig, self.global_up_axis_rotation)
        ProgressEnd.emit()

    def on_load_assemble_btn_clicked(self, force=False):
        if not force:
            question = Question("New scene", "Create new neutral scene?", self).ask()
            if question == QtWidgets.QMessageBox.No:
                return
        neutral_geo_view = self.ui["widget"]["neutral_geo_view"]
        neutral_jnt_view = self.ui["widget"]["neutral_jnt_view"]
        selected_lods = set()
        for i in neutral_geo_view.selectedIndexes():
            if i.parent().data() is not None:
                selected_lods.add(i.parent().data())
            else:
                selected_lods.add(i.data())

        self.controller.neutral_assemble(self.rig, selected_lods, self.up_axis)
        self.controller.update_views([neutral_geo_view, neutral_jnt_view])

        self._initialize_view("skin_geo_view", lib.get_dna_lods(self.rig), True)
        self._initialize_view("skin_jnt_view", lib.get_dna_joints(self.rig))

    def on_rig_assemble_btn_clicked(self, force=False):
        if not force:
            question = Question("New scene", "Create new rig editing scene?", self).ask()
            if question == QtWidgets.QMessageBox.No:
                return
        joint_pruning_threshold = [
            self.config["pruning_threshold"]["joint_translation_pruning_threshold"],
            self.config["pruning_threshold"]["joint_rotation_pruning_threshold"],
            self.config["pruning_threshold"]["joint_scale_pruning_threshold"],
        ]

        head_turns_main_expressions = self.config["head_turns_data"]["main_expressions"]
        neck_joints = self.config["neck_joints"]
        neck_joints_values = []

        for main_expression in head_turns_main_expressions:
            main_expression_data = self.config["head_turns_data"]["neck_joints_animation"][main_expression]
            for neck_joint in neck_joints:
                neck_joints_values.extend(main_expression_data[neck_joint])

        self.controller.rig_assemble(
            self.rig,
            Resources().dna_file_path,
            self.config["pruning_threshold"]["corrective_blend_shape_pruning_threshold"],
            joint_pruning_threshold,
            head_turns_main_expressions,
            neck_joints,
            neck_joints_values,
            self.up_axis,
            self.global_up_axis_rotation,
            **self.config["gui_positioning"],
        )

    def initialize_views(self, editing_expression_name):
        rig_expression = self.rig.rig_definition.get_expression_by_name(editing_expression_name)
        group_name = "edit_grp" if rig_expression.no_phases() == 1 else "phase_grp"
        rig_geo_view = self.ui["widget"]["rig_geo_view"]
        rig_geo_view.clear()
        visible_meshes = lib.get_sculpt_mesh_names(self.rig, [rig_expression])
        phase_numbers = rig_expression.get_phase_numbers()
        if len(phase_numbers) > 1:
            dcc.set_all_phase_sculpt_visibility(editing_expression_name, phase_numbers, visible_meshes, True)
        rig_geo = lib.get_rig_geo(group_name)
        if len(phase_numbers) > 1:
            dcc.set_all_phase_sculpt_visibility(editing_expression_name, phase_numbers, visible_meshes, False)
        self._object_hierarchy_to_tree(rig_geo_view, rig_geo)

        rig_jnt_view = self.ui["widget"]["rig_jnt_view"]
        rig_jnt_view.clear()
        rig_jnt = lib.get_rig_jnt(group_name)
        self._object_hierarchy_to_tree(rig_jnt_view, rig_jnt)
        self.controller.update_rig_views([rig_geo_view, rig_jnt_view])

        self._initialize_view("neutral_geo_view", lib.get_dna_lods(self.rig), True)
        self._initialize_view("neutral_jnt_view", lib.get_dna_joints(self.rig))
        self._initialize_view("skin_geo_view", lib.get_dna_lods(self.rig), True)
        self._initialize_view("skin_jnt_view", lib.get_dna_joints(self.rig))

    def on_load_assemble_skin_btn_clicked(self, force=False):
        if not force:
            question = Question("New scene", "Create new skin editing scene?", self).ask()
            if question == QtWidgets.QMessageBox.No:
                return
        skin_geo_view = self.ui["widget"]["skin_geo_view"]
        skin_jnt_view = self.ui["widget"]["skin_jnt_view"]
        selected_lods = set()
        for i in skin_geo_view.selectedIndexes():
            if i.parent().data() is not None:
                selected_lods.add(i.parent().data())
            else:
                selected_lods.add(i.data())
        self.controller.skin_assemble(
            self.rig,
            Resources().dna_file_path,
            selected_lods,
            self.up_axis,
            self.global_up_axis_rotation,
            **self.config["gui_positioning"],
        )
        self.controller.update_views([skin_geo_view, skin_jnt_view])

        self._initialize_view("neutral_geo_view", lib.get_dna_lods(self.rig), True)
        self._initialize_view("neutral_jnt_view", lib.get_dna_joints(self.rig))

    def on_save_dna_skin_clicked(self, dna_file_path=None):
        dna_file_path = self.controller.update_skin(
            self.rig,
            self.ui["widget"]["skin_geo_view"],
            self.global_up_axis_rotation,
            dna_file_path=dna_file_path,
        )
        if dna_file_path and Settings().get_setting("auto_load_dna"):
            self.on_load_btn_clicked(dna_file_path=dna_file_path, clear_cache=False)

    def on_toggle_editing_clicked(self):
        if self.controller.node_exists():
            logger.warning("The rig editing scene needs to be assembled before editing can be started.")
            return

        graph = self.ui["widget"]["graph"]
        if not self.rig_editing_active and (
            not graph.currentWidget().scene().selectedItems() or len(graph.currentWidget().scene().selectedItems()) > 1
        ):
            logger.warning("Please select single node to edit.")
            return

        if self.rig_editing_active:
            self.rig_editing_active = False
            self.controller.stop_editing(self.rig, graph.currentWidget())
        else:
            node = graph.currentWidget().scene().selectedItems()[0]
            node.activate()
            self.rig_editing_active = True
            self.controller.start_editing(
                self.rig,
                graph.currentWidget(),
                self.expression_joints_mapping,
                self.config["split_expressions"],
            )
        self.controller.editing_gui_update()

    def on_analyze_frame_clicked(self):
        graph = self.ui["widget"]["graph"].currentWidget()
        node_values = lib.analyze_frame(self.rig, self.expression_controls_mapping, self.config["control_renaming"])
        for node in graph.scene().nodes:
            if node.name in node_values:
                node.set_analyzed(general.linear_interpolate_color(node_values[node.name]))

    def focus_node(self, node_name):
        graph_view = self.ui["widget"]["graph"].currentWidget()
        node = graph_view.scene().get_node_by_name(node_name)
        graph_view.scene().reset_selection()
        node.setSelected(True)
        graph_view.fit_to_view([node], ensure_visible=True)

    def on_update_neutral_meshes_clicked(self):
        meshes_to_update = []
        neutral_geo_view = self.ui["widget"]["neutral_geo_view"]
        root = neutral_geo_view.invisibleRootItem()
        for lod_index in range(root.childCount()):
            lod_item = root.child(lod_index)
            lod = lod_item.text(0)

            for mesh_index in range(lod_item.childCount()):
                mesh_item = lod_item.child(mesh_index)
                mesh_name = mesh_item.text(0)
                if not mesh_item.isDisabled():
                    meshes_to_update.append(f"{lod}|{mesh_name}")

        try:
            lib.update_neutral_meshes(self.rig, meshes_to_update, self.global_up_axis_rotation)
        except RuntimeError as e:
            logger.error(e)
            ProgressEnd.emit()

    def on_update_neutral_joints_clicked(self):
        try:
            lib.update_neutral_joints(self.rig)
        except RuntimeError as e:
            logger.error(e)
            ProgressEnd.emit()

    def on_toggle_vertex_shading_btn_clicked(self):
        self.controller.toggle_vertex_shading()

    def on_choose_direction_clicked(self, button):
        if button.property("direction") == general.Direction.LEFT_TO_RIGHT:
            ui.set_icon(button, "direction_RtoL.svg")
            for dependent_button, icons in button.property("dependent_buttons").items():
                ui.set_icon(dependent_button, icons["RtoL"])
            button.setProperty("direction", general.Direction.RIGHT_TO_LEFT)
        else:
            ui.set_icon(button, "direction_LtoR.svg")
            for dependent_button, icons in button.property("dependent_buttons").items():
                ui.set_icon(dependent_button, icons["LtoR"])
            button.setProperty("direction", general.Direction.LEFT_TO_RIGHT)

    def on_transfer_vtx_clicked(self):
        view = self.ui["widget"]["rig_geo_view"]
        view_selected = view.selectedIndexes()
        if len(view_selected) != 1:
            logger.warning("Please select one sculpt mesh in geometry view.")
            return
        vsm = view_selected[0]
        main_mesh = f"{'|' + vsm.parent().data() if vsm.parent().data() is not None else ''}|{vsm.data()}"
        main_mesh_name_parts = main_mesh.split("|")
        group_name = main_mesh_name_parts[-2]
        mesh_name = main_mesh_name_parts[-1]

        if group_name == "edit_grp" and mesh_name.startswith("sculpt"):
            self.controller.transfer_vtx(self.ui["widget"]["rig_geo_view"])
        else:
            logger.warning("Please select a sculpt mesh from the edit group.")

    def on_mirror_jnt_clicked(self):
        self.controller.mirror_joints(self.rig, self.ui["button"]["choose_direction"].property("direction"))

    def on_flip_jnt_clicked(self):
        self.controller.flip_joints(self.rig, self.ui["button"]["choose_direction"].property("direction"))

    def on_neutralize_jnt_clicked(self):
        self.controller.neutralize_joints(self.rig)

    def on_reset_jnt_to_dna_clicked(self):
        self.controller.reset_joints_to_dna_expression(self.rig, self.controller.editing_expression)

    def on_copy_joints_clicked(self):
        self.controller.copy_joints(self.rig)

    def on_run_ml_joints_matching_in_scene_clicked(self):
        if not self.controller.ml_joints_matching_handler_single_expression.model_loaded:
            question = Question(
                "Run Scene ML Joints Matching",
                "Run ML joints matching in the scene? This will load the model, which can take a few minutes.",
                self,
            ).ask()
            if question == QtWidgets.QMessageBox.No:
                return
        self.controller.run_ml_joints_matching_in_scene(
            self.rig,
            self.expression_joints_mapping,
            self.config["ml_jm_config"]["expressions"],
            self.config["ml_jm_config"]["data"],
            set(self.config["user_defined_joints"]),
        )

    def on_delete_history_clicked(self):
        view = self.ui["widget"]["rig_geo_view"]
        selected_indices = view.selectedIndexes()
        if not selected_indices:
            sculpt_mesh_names = [f"|edit_grp|sculpt_{mesh_name}" for mesh_name in lib.get_sculpt_mesh_names(self.rig)]
        else:
            sculpt_mesh_names = []
            for selected_index in selected_indices:
                long_mesh_name = f"{'|' + selected_index.parent().data() if selected_index.parent().data() is not None else ''}|{selected_index.data()}"
                main_mesh_name_parts = long_mesh_name.split("|")
                group_name = main_mesh_name_parts[-2]
                mesh_name = main_mesh_name_parts[-1]

                if group_name == "edit_grp" and mesh_name.startswith("sculpt"):
                    sculpt_mesh_names.append(long_mesh_name)
        dcc.delete_history(sculpt_mesh_names)
        logger.info(f"History deleted on {sculpt_mesh_names}.")

    def on_save_action(self, dna_file_path=None):
        dna_file_path = self.controller.save_rig_dna(
            self.rig, self.global_up_axis_rotation, dna_file_path=dna_file_path
        )
        if dna_file_path and Settings().get_setting("auto_load_dna"):
            self.on_load_btn_clicked(dna_file_path=dna_file_path, clear_cache=False)

    def on_save_dna_neutral_clicked(self, dna_file_path=None):
        if os.path.exists(Resources().lod_generation_model_description_path):
            message_box = LowerLODQuestion(self.rig.dna_reader.getLODCount(), self)
            response = message_box.show()
            source_lod = message_box.selected_lod if response else None
            if source_lod is not None:
                meshes_to_update = {}
                neutral_geo_view = self.ui["widget"]["neutral_geo_view"]
                root = neutral_geo_view.invisibleRootItem()
                for lod_index in range(root.childCount()):
                    if lod_index > source_lod:
                        lod_item = root.child(lod_index)
                        lod = lod_item.text(0)

                        for mesh_index in range(lod_item.childCount()):
                            mesh_item = lod_item.child(mesh_index)
                            mesh_name = mesh_item.text(0)
                            if not mesh_item.isDisabled():
                                meshes_to_update[mesh_name] = f"{lod}|{mesh_name}"
                self.controller.calculate_lower_lods(self.rig, source_lod)
                self.controller.update_scene_lower_lods(self.rig, meshes_to_update)
        dna_file_path = self.controller.save_rig_dna(
            self.rig, self.global_up_axis_rotation, dna_file_path=dna_file_path
        )
        if dna_file_path and Settings().get_setting("auto_load_dna"):
            self.on_load_btn_clicked(dna_file_path=dna_file_path, clear_cache=False)

    def show(self, dna_file_path=None):
        # If the window is minimized then un-minimize it.
        if self.windowState() & QtCore.Qt.WindowMinimized:
            self.setWindowState(QtCore.Qt.WindowActive)

        # Raise and activate the window
        self.raise_()  # for MacOS
        self.activateWindow()  # for Windows

        if dna_file_path:
            self.ui["widget"]["dna_file_path"].fc_text_field.setText(dna_file_path)

        super().show(dockable=True)

    def animation_dialog(self, anim_type):
        path = QtWidgets.QFileDialog.getOpenFileName(self, f"Select {anim_type} animation file", "", "*.fbx")
        if path[0]:
            self.controller.load_animation(path[0], anim_type)

    def on_preview_btn_clicked(self):
        self.controller.preview_downstream_expressions(self.rig, **self.config["shape_preview_data"])

    def on_preview_unlocked_btn_clicked(self):
        question = Question("Preview Unlocked Nodes", "Create preview shapes for all unlocked nodes?", self).ask()
        if question == QtWidgets.QMessageBox.No:
            return
        self.controller.preview_unlocked_downstream_expressions(self.rig, **self.config["shape_preview_data"])

    def on_delete_preview_btn_clicked(self):
        self.controller.delete_preview_meshes()

    def on_run_jm(self, dna_file_path=None, force=False):
        if not force:
            question = Question(
                "Optimize Rig", "Improve joint animations and reduce MetaHuman DNA file size?", self
            ).ask()

            if question == QtWidgets.QMessageBox.No:
                return

        self.controller.optimize_rig(
            self.rig,
            [self.ui["widget"]["jm_preset_list"].custom_item_list[self.ui["widget"]["jm_preset_list"].currentIndex()]],
        )
        self.on_save_action(dna_file_path=dna_file_path)

    def on_run_ml_joints_matching_on_rig(self):
        question = Question(
            "Optimize Rig",
            "Improve joint animations and reduce MetaHuman DNA file size for all expressions using ML Joints Matching?",
            self,
        ).ask()
        if question == QtWidgets.QMessageBox.No:
            return

        self.controller.run_ml_joints_matching_on_rig(
            self.rig,
            self.expression_joints_mapping,
            set(self.config["user_defined_joints"]),
            self.config["head_turns_data"],
            self.config["ml_jm_config"]["expressions"],
            self.config["ml_jm_config"]["data"],
        )
        self.on_save_action()

    def on_update_save_rig(self, force=False):
        if self.controller.node_exists():
            logger.warning(
                "The expression poses editing scene needs to be assembled to update the rig with data from the scene."
            )
            return

        if not force:
            result = QtWidgets.QMessageBox.information(
                self,
                "Update MetaHuman DNA",
                "This will update the MetaHuman DNA contained in memory with data parsed from the scene.\nUnsaved changes to the MetaHuman DNA that aren't in the scene will be overwritten.\nDo you want to continue?",
                QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No,
            )

            if result == QtWidgets.QMessageBox.No:
                return

        ProgressStart.emit(max_value=2)
        ProgressUpdate.emit(status="Updating MetaHuman DNA")
        temp_dna_file_path = self.controller.save_dna_from_node()
        try:
            updated_rig = RigDataHandler(
                Resources().rdf_file_path,
                temp_dna_file_path,
                **self.config["pruning_threshold"],
            )
            with contextlib.suppress(KeyError):
                head_turns_data = self.config["head_turns_data"]
                lib.add_neck_rotations(
                    self.rig, head_turns_data["main_expressions"], head_turns_data["neck_joints_animation"]
                )

            self.rig = updated_rig
            lib.add_phase_expression_view_data(self.rig, self.config["phase_expression_views"])
            self.controller.initialize_ml_joints_matching_handler(self.rig, self.global_up_axis_rotation)
        except AttributeError:
            logger.error("MetaHuman DNA was not correctly updated.")
        finally:
            ProgressEnd.emit()
            self.controller.delete_file(temp_dna_file_path)
            self.on_save_action()

    # --------------------------------------------------------------------------

    def on_tab_change(self, i):
        # Disable inactive views
        for j in range(0, self.ui["widget"]["graph"].count()):
            if j != i:
                self.ui["widget"]["graph"].widget(j).setVisible(False)
                self.ui["widget"]["graph"].widget(j).setUpdatesEnabled(False)
        # Populate search with current nodes
        if self.ui["widget"]["graph"].currentWidget():
            scene = self.ui["widget"]["graph"].currentWidget().scene()
            nodes = [x.name for x in scene.nodes]
            self.ui["widget"]["node_filter"].addItems(nodes)
            self.ui["widget"]["node_filter"].clearEditText()
        # Enable active view
        if self.ui["widget"]["graph"].widget(i):
            self.ui["widget"]["graph"].widget(i).setVisible(True)
            self.ui["widget"]["graph"].widget(i).setUpdatesEnabled(True)

    def add_view(self, scene_model, name=None, preset=None):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        scene_model = lib.populate_branch(scene_model, self.ui["widget"]["graph"].widget(0).scene())
        if (modifiers and QtCore.Qt.ControlModifier) or preset:
            graph_view = GraphView(self)
            graph_view.set_model(scene_model)
            graph_scene = graph_view.scene()

            for node_model in scene_model.nodes.values():
                node = Node(node_model.name, node_model.layer, parent=graph_scene)
                node.set_model(node_model)
                node.load_from_model()
                graph_scene.add_node(node)

            for node_model in scene_model.nodes.values():
                node = graph_scene.get_node_by_name(node_model.name)
                for inp in node_model.inputs:
                    end = graph_scene.get_node_by_name(node_model.name)
                    start = graph_scene.get_node_by_name(inp)
                    if start and end:
                        graph_scene.add_connection(Connection(start, end))
                        node.inputs.append(start)
                for out in node_model.outputs:
                    start = graph_scene.get_node_by_name(node_model.name)
                    end = graph_scene.get_node_by_name(out)
                    if start and end:
                        graph_scene.add_connection(Connection(start, end))
                        node.outputs.append(end)

            index = self.ui["widget"]["graph"].addTab(graph_view, name)
            self.ui["widget"]["graph"].setCurrentIndex(index)
            if preset:
                graph_view.scene().rearrange_scene()
            graph_view.focus()
        else:
            graph_view = self.ui["widget"]["graph"].currentWidget()
            graph_scene = graph_view.scene()
            graph_view.on_reset_graph()

            for node_model in scene_model.nodes.values():
                node: Node = graph_scene.get_node_by_name(node_model.name)
                if node:
                    node.set_model(node_model)
                    node.load_from_model(skip_position=True)
            graph_view.focus()

        for node_model in scene_model.nodes.values():
            node = graph_scene.get_node_by_name(node_model.name)
            if node and node_model._locked:
                self.controller.propagate_lock_to_views(node)

    def delete_subselection(self, index):
        self.ui["widget"]["graph"].removeTab(index)

    def clear_tabs(self):
        for i in range(0, self.ui["widget"]["graph"].count())[::-1]:
            self.delete_subselection(i)

    def add_graph(self, name, data):
        graph_view = GraphView(self)
        graph_scene = graph_view.scene()

        modeling_expressions = lib.get_modeling_expressions(data, self.config["skip_modeling_expressions"])
        scene_model = SceneModel(modeling_expressions)

        graph_view.set_model(scene_model)

        for expression in modeling_expressions.values():
            node = Node(expression.name, expression.layer, parent=graph_scene)
            node.set_model(expression)
            graph_scene.add_node(node)

        for expression in modeling_expressions.values():
            node = graph_scene.get_node_by_name(expression.name)
            for inp in expression.inputs:
                end = graph_scene.get_node_by_name(expression.name)
                start = graph_scene.get_node_by_name(inp)
                if start and end:
                    graph_scene.add_connection(Connection(start, end))
                    node.inputs.append(start)

            for out in expression.outputs:
                start = graph_scene.get_node_by_name(expression.name)
                end = graph_scene.get_node_by_name(out)
                if start and end:
                    graph_scene.add_connection(Connection(start, end))
                    node.outputs.append(end)

        graph_scene.rearrange_scene()

        self.ui["widget"]["graph"].addTab(graph_view, name)


def on_destroyed():
    module.window = None


def show(parent=None, dna_file_path=None):
    with ui.application():
        # create if it doesn't exist
        if module.window is None:
            module.window = Window(parent=parent)
            module.window.destroyed.connect(on_destroyed)

        # If the window is minimized, raise it
        if module.window.windowState() & QtCore.Qt.WindowMinimized:
            module.window.setWindowState(QtCore.Qt.WindowActive)

        # show and make active
        module.window.show(dna_file_path)
        module.window.activateWindow()
        logger.info(f"MetaHuman Expression Editor initialized with {lib.get_dnacalib2_version_info()}")

        return module.window
