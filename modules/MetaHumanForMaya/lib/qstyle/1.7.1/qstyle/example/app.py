# Copyright Epic Games, Inc. All Rights Reserved.
import os
import sys
import logging
import contextlib

from qtpy import QtGui, QtCore, QtWidgets

import qstyle

from ..lib import resource
from .data import multiline_text

module = sys.modules[__name__]
module.window = None  # type: ignore

app_css = os.path.join(os.path.dirname(__file__), "app.css")
app_icon = resource("image", "qstyle.png")

material = qstyle.FontIcons("material")
epic = qstyle.FontIcons("epic")


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        yield app
    else:
        yield app
    app.exec_()


def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    root.setLevel(level)


class Window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Widget Gallery")
        self.resize(1200, 800)
        self.setWindowIcon(QtGui.QIcon(app_icon))
        self.current_value = 0

        setup_logging(logging.INFO)

        # NOTE: It's important to do this before you start creating any widgets.
        qstyle.install_fonts(silent=True)
        qstyle.set_style(self, app_css, with_main=True)

        # ------------------------------------------------------------------------------------------
        # UI

        central_widget = QtWidgets.QWidget(self)
        central_layout = QtWidgets.QVBoxLayout(central_widget)

        menubar = QtWidgets.QMenuBar(self)

        file_menu = QtWidgets.QMenu("File", parent=self)
        file_menu.setToolTipsVisible(True)
        load_action = file_menu.addAction("Load", lambda: print("Load"))
        load_action.setIcon(material.icon("folder"))
        save_action = file_menu.addAction("Save", lambda: print("Save"))
        save_action.setIcon(material.icon("save"))
        file_menu.addSeparator()
        file_menu.addAction("Settings", lambda: print("Settings"))
        file_menu.addSeparator()
        file_menu.addAction("Close", lambda: print("Close"))

        help_menu = QtWidgets.QMenu("Help", parent=self)
        quick_guide_action = help_menu.addAction("Quick Guide", lambda: print("Quick Guide"))
        quick_guide_action.setEnabled(False)
        help_menu.addAction("Support", lambda: print("Support"))
        help_menu.addSeparator()
        about = help_menu.addAction("About", lambda: print("About"))
        about.setIcon(material.icon("help_center"))

        menubar.addMenu(file_menu)
        menubar.addMenu(help_menu)
        central_layout.setMenuBar(menubar)

        # ------------------------------------------------------------------------------------------

        tabs = QtWidgets.QTabWidget()
        tabs_layout = QtWidgets.QHBoxLayout(tabs)

        # ------------------------------------------------------------------------------------------

        tab_one = QtWidgets.QWidget(self)
        tab_one_layout = QtWidgets.QFormLayout(tab_one)

        tool_button_frame = QtWidgets.QFrame(self)
        tools_layout = QtWidgets.QHBoxLayout(tool_button_frame)

        home_button = QtWidgets.QToolButton()
        home_button.setText(material.get("home"))

        arrow_button = QtWidgets.QToolButton()
        arrow_button.setText(material.get("keyboard_double_arrow_right"))

        save_button = QtWidgets.QToolButton()
        save_button.setText(material.get("save"))

        load_button = QtWidgets.QToolButton()
        load_button.setText(material.get("file_download"))

        metahuman_button = QtWidgets.QToolButton()
        metahuman_button.setIcon(epic.icon("metahuman_16", color="#FFCF4C"))
        metahuman_button.setObjectName("MetaHumanButton")

        python_button = QtWidgets.QToolButton()
        python_button.setIcon(epic.icon("python_execute", color="#4788D3"))
        python_button.setObjectName("PythonButton")

        tools_layout.addWidget(home_button)
        tools_layout.addWidget(arrow_button)
        tools_layout.addWidget(save_button)
        tools_layout.addWidget(load_button)
        tools_layout.addStretch()
        tools_layout.addWidget(metahuman_button)
        tools_layout.addWidget(python_button)
        tools_layout.setContentsMargins(0, 0, 0, 0)

        combobox = QtWidgets.QComboBox()
        combobox.insertItems(0, [f"Select {i}" for i in range(10)])

        self.click_me = QtWidgets.QPushButton("Click Me")

        tab_one_layout.addRow("Label", QtWidgets.QLabel("This is a QLabel"))
        tab_one_layout.addRow("PushButton", self.click_me)
        tab_one_layout.addRow("ToolButton", tool_button_frame)
        tab_one_layout.addRow("CheckBox", QtWidgets.QCheckBox("Check me"))
        tab_one_layout.addRow("RadioButton", QtWidgets.QRadioButton("Select me"))
        tab_one_layout.addRow("LineEdit", QtWidgets.QLineEdit("Default text"))
        tab_one_layout.addRow("ComboBox", combobox)
        tab_one_layout.addRow("TextEdit", QtWidgets.QTextEdit(multiline_text))
        # ------------------------------------------------------------------------------------------

        tab_two = QtWidgets.QWidget(self)
        tab_two_layout = QtWidgets.QFormLayout(tab_two)

        progress_bar_start = QtWidgets.QPushButton("Start", self)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_progress)

        tab_two_layout.addRow("SpinBox", QtWidgets.QSpinBox())
        tab_two_layout.addRow("DoubleSpinBox", QtWidgets.QDoubleSpinBox())
        tab_two_layout.addRow("Slider", QtWidgets.QSlider(QtCore.Qt.Horizontal))
        tab_two_layout.addRow("Dial", QtWidgets.QDial())
        tab_two_layout.addRow(progress_bar_start, self.progress_bar)
        tab_two_layout.addRow("DateEdit", QtWidgets.QDateEdit())
        tab_two_layout.addRow("TimeEdit", QtWidgets.QTimeEdit())
        tab_two_layout.addRow("DateTimeEdit", QtWidgets.QDateTimeEdit())

        # ------------------------------------------------------------------------------------------

        tab_three = QtWidgets.QWidget(self)
        tab_three_layout = QtWidgets.QFormLayout(tab_three)

        # ListWidget
        list_widget = QtWidgets.QListWidget()
        list_widget.addItems(["Item 1", "Item 2", "Item 3"])

        # ListView
        list_view_model = QtGui.QStandardItemModel()
        for i in range(3):
            item = QtGui.QStandardItem(f"ListView Item {i+1}")
            list_view_model.appendRow(item)
        list_view = QtWidgets.QListView()
        list_view.setModel(list_view_model)

        # TableWidget
        table_widget = QtWidgets.QTableWidget(3, 3)
        for row in range(3):
            for col in range(3):
                table_widget.setItem(row, col, QtWidgets.QTableWidgetItem(f"{row+1},{col+1}"))

        # TableView
        table_model = QtGui.QStandardItemModel(3, 3)
        for row in range(3):
            for col in range(3):
                item = QtGui.QStandardItem(f"{row+1},{col+1}")
                table_model.setItem(row, col, item)
        table_view = QtWidgets.QTableView()
        table_view.setModel(table_model)

        # TreeWidget
        tree_widget = QtWidgets.QTreeWidget()
        tree_widget.setHeaderLabels(["Column 1", "Column 2"])
        for i in range(3):
            parent = QtWidgets.QTreeWidgetItem([f"Parent {i+1}", "Value"])
            for j in range(2):
                child = QtWidgets.QTreeWidgetItem([f"Child {i+1}.{j+1}", "Value"])
                parent.addChild(child)
            tree_widget.addTopLevelItem(parent)

        # TreeView
        tree_model = QtGui.QStandardItemModel()
        tree_model.setHorizontalHeaderLabels(["Column 1", "Column 2"])
        for i in range(3):
            parent = QtGui.QStandardItem(f"Parent {i+1}")
            for j in range(2):
                child = QtGui.QStandardItem(f"Child {i+1}.{j+1}")
                parent.appendRow([child, QtGui.QStandardItem("Value")])
            tree_model.appendRow([parent, QtGui.QStandardItem("Value")])
        tree_view = QtWidgets.QTreeView()
        tree_view.setModel(tree_model)

        tab_three_layout.addRow("ListWidget", list_widget)
        tab_three_layout.addRow("ListView", list_view)
        tab_three_layout.addRow("TableWidget", table_widget)
        tab_three_layout.addRow("TableView", table_view)
        tab_three_layout.addRow("TreeWidget", tree_widget)
        tab_three_layout.addRow("TreeView", tree_view)

        # ------------------------------------------------------------------------------------------

        tabs.addTab(tab_one, "Tab One")
        tabs.addTab(tab_two, "Tab Two")
        tabs.addTab(tab_three, "Tab Three")

        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs.setLayout(tabs_layout)

        central_layout.addWidget(tabs)
        self.setCentralWidget(central_widget)

        self.click_me.clicked.connect(self._on_click_me)
        progress_bar_start.clicked.connect(self.start_progress)

    def _on_click_me(self):
        print("-" * 60)
        print("Click me")
        print("-" * 60)

    def start_progress(self):
        self.current_value = 0
        self.progress_bar.setValue(self.current_value)
        self.timer.start(100)

    def update_progress(self):
        self.current_value += 1
        self.progress_bar.setValue(self.current_value)
        if self.current_value >= 100:
            self.timer.stop()


def on_destroyed():
    module.window = None


def show(parent=None):
    with application():
        # create if it doesn't exist
        if module.window is None:
            module.window = Window(parent)
            module.window.destroyed.connect(on_destroyed)

        # If the window is minimized, raise it
        if module.window.windowState() & QtCore.Qt.WindowMinimized:
            module.window.setWindowState(QtCore.Qt.WindowActive)

        # show and make active
        module.window.show()
        module.window.activateWindow()

        return module.window
