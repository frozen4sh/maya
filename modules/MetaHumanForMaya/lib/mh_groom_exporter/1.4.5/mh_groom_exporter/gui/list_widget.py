# Copyright Epic Games, Inc. All Rights Reserved.
from functools import partial

import qstyle
from qtpy import QtGui, QtCore, QtWidgets

icons = qstyle.FontIcons("material")


class ListWidget(QtWidgets.QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)

        self.setObjectName(name)

        self.group_names = [str(index) for index in range(15)]

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Create List
        self.list_layout = QtWidgets.QHBoxLayout()
        self.list_layout.setContentsMargins(0, 0, 0, 0)

        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setHeaderHidden(False)
        self.tree_widget.setColumnCount(2)
        self.tree_widget.setHeaderLabels(["Descriptions", "GroupID", "Guides"])

        # header
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        header.setDefaultAlignment(QtCore.Qt.AlignCenter)
        header.setStretchLastSection(False)

        # signals
        self.tree_widget.itemExpanded.connect(self._edit_names)

        # context menu
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)

        # actions menu
        self.menu_button = QtWidgets.QToolButton()
        self.menu_button.setText(icons.get("menu"))
        self.menu_button.setProperty("action", "true")
        self.menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        menu = QtWidgets.QMenu(parent=self)
        act_enable_guides = QtGui.QAction(
            "Enable guides on selected",
            self,
            triggered=partial(self._check_items, True),
        )
        act_disable_guides = QtGui.QAction(
            "Disable guides on selected",
            self,
            triggered=partial(self._check_items, False),
        )

        menu.addAction(act_enable_guides)
        menu.addAction(act_disable_guides)

        self.menu_button.setMenu(menu)

        self.list_layout.addWidget(self.tree_widget)
        self.list_layout.addWidget(self.menu_button, alignment=QtCore.Qt.AlignTop)

        # Create Buttons
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)

        self.all_button_widget = QtWidgets.QPushButton()
        self.all_button_widget.setText("Select All")
        self.all_button_widget.clicked.connect(partial(self._select_items, True))

        self.none_button_widget = QtWidgets.QPushButton()
        self.none_button_widget.setText("Clear Selection")
        self.none_button_widget.clicked.connect(partial(self._select_items, False))

        self.button_layout.addWidget(self.all_button_widget)
        self.button_layout.addWidget(self.none_button_widget)

        # ------------------------------------------------------------------------------------------

        # layout
        layout.addLayout(self.list_layout)
        layout.addLayout(self.button_layout)

    def _clear(self):
        self.tree_widget.clear()
        self.group_names = [str(index) for index in range(15)]

    def _select_items(self, select=True):
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            item.setSelected(select)

    def _check_items(self, check, *args):
        indices = self.tree_widget.selectedIndexes()
        self.tree_widget.blockSignals(True)
        for i in indices:
            item = self.tree_widget.itemFromIndex(i)
            item.checked = check
        self.tree_widget.blockSignals(False)

    def _edit_names(self, item):
        data = [item.QComboBox.itemText(i) for i in range(item.QComboBox.count())]
        self.group_names = data
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            for index, value in enumerate(data):
                item.QComboBox.setItemText(index, value)

    def _show_context_menu(self, position):
        set_group_id_menu = QtWidgets.QMenu("Set GroupID", None)
        for _id, name in enumerate(self.group_names):
            action = QtWidgets.QAction(f'{_id} -> "{name}"', set_group_id_menu)
            action.triggered.connect(partial(self._set_group_id, _id))
            set_group_id_menu.addAction(action)

        toggle_guides_action = QtWidgets.QAction("Toggle Guide Export", None)
        toggle_guides_action.triggered.connect(self._toggle_guide_export)

        menu = QtWidgets.QMenu(self.tree_widget)
        menu.addMenu(set_group_id_menu)
        menu.addAction(toggle_guides_action)

        if self.tree_widget.selectedItems():
            menu.exec_(self.tree_widget.mapToGlobal(position))

    def _set_group_id(self, _id):
        for item in self.tree_widget.selectedItems():
            data = item.data
            data = (_id, self.group_names[_id], data[2])
            item.data = data

    def _toggle_guide_export(self):
        self.tree_widget.blockSignals(True)
        for item in self.tree_widget.selectedItems():
            data = item.data
            data = (data[0], data[1], not (data[2]))
            item.data = data
        self.tree_widget.blockSignals(False)

    @property
    def selected_indexes(self):
        return self.tree_widget.selectedIndexes()

    @selected_indexes.setter
    def selected_indexes(self, value):
        for each in value:
            self.tree_widget.topLevelItem(each).setSelected(True)

    @property
    def data(self):
        data = dict()
        data["group_names"] = self.group_names
        data["descriptions"] = {}
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            name = item.text(0)
            value = item.data
            selected = item.isSelected()
            data["descriptions"][name] = (value, selected)
        return data

    @data.setter
    def data(self, data):
        self.group_names = data["group_names"]
        for entry in data["descriptions"].items():
            item = self.tree_widget.findItems(entry[0], QtCore.Qt.MatchExactly)
            if item:
                item = item[0]
                self.tree_widget.blockSignals(True)
                for index, value in enumerate(self.group_names):
                    item.QComboBox.setItemText(index, value)
                item.data = entry[1][0]
                item.setSelected(entry[1][1])
                self.tree_widget.blockSignals(False)
