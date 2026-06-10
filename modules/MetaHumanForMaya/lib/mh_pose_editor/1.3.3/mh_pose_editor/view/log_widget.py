# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import logging
from typing import Optional
from functools import partial

# External
import qstyle
from qtpy import QtGui, QtCore, QtWidgets

# Internal
from mh_pose_editor.model import settings

icons = qstyle.FontIcons("material")


class LogLevels:
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class LogWidget(logging.Handler):
    """
    Custom Log Handler with embedded QtWidgets.QDockWidget
    """

    def __init__(self):
        super().__init__()
        # Set default formatting
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
        # Create dock
        self._log_dock = QtWidgets.QDockWidget("Output Log")
        self._log_dock.showEvent = self._log_dock_show
        # Only allow it to be parented to the bottom
        self._log_dock.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)

        central_widget = QtWidgets.QWidget()
        central_widget.setContentsMargins(0, 0, 0, 0)
        self._log_dock.setWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)

        toolbar_layout = QtWidgets.QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(toolbar_layout)

        self._output_log = QtWidgets.QListWidget()
        self._output_log.setProperty("Log", True)
        self._output_log.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._output_log.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._output_log.customContextMenuRequested.connect(self._show_context_menu)
        main_layout.addWidget(self._output_log)

    @property
    def log_dock(self):
        return self._log_dock

    def emit(self, record):
        level_colour_map = {
            logging.DEBUG: QtGui.QColor(91, 192, 222),
            logging.INFO: QtGui.QColor(247, 247, 247),
            logging.WARNING: QtGui.QColor(240, 173, 78),
            logging.ERROR: QtGui.QColor(217, 83, 79),
        }
        msg = self.format(record)
        item = QtWidgets.QListWidgetItem(msg)
        item.setData(QtCore.Qt.UserRole, record.levelno)
        item.setForeground(QtGui.QBrush(level_colour_map[record.levelno]))
        self._output_log.addItem(item)
        self._refresh_log()
        self._output_log.scrollToBottom()

    def _refresh_log(self, log_level: Optional[str] = None, checked: Optional[bool] = None):
        if log_level and checked is not None:
            settings.SettingsManager.set_setting(f"log_widget:{log_level}", int(checked))

        level_btn_map = {
            logging.DEBUG: bool(
                int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.debug}", fallback=True))
            ),
            logging.INFO: bool(
                int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.info}", fallback=True))
            ),
            logging.WARNING: bool(
                int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.warning}", fallback=True))
            ),
            logging.ERROR: bool(
                int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.error}", fallback=True))
            ),
        }
        for i in range(0, self._output_log.count()):
            item = self._output_log.item(i)
            data = item.data(QtCore.Qt.UserRole)
            if data in level_btn_map:
                item.setHidden(not level_btn_map[data])

    def _toggle_expandable_log(self, expandable: bool):
        if expandable:
            self._log_dock.setMinimumHeight(0)
            self._log_dock.setMaximumHeight(1000000)
        else:
            temp_item = QtWidgets.QListWidgetItem()
            self._output_log.addItem(temp_item)
            item_rect = self._output_log.visualItemRect(temp_item)
            self._output_log.takeItem(self._output_log.row(temp_item))
            log_height = item_rect.height() * 2
            title_bar_offset = self._log_dock.height() - self._output_log.height()
            self._log_dock.setFixedHeight(log_height + title_bar_offset)

        settings.SettingsManager.set_setting("log_widget:expandable", int(expandable))

    def _log_dock_show(self, event):
        QtWidgets.QDockWidget.showEvent(self._log_dock, event)

        expandable_log = bool(int(settings.SettingsManager.get_setting("log_widget:expandable", fallback=False)))

        self._toggle_expandable_log(expandable_log)

    def _copy_to_clipboard(self):
        clipboard_text = ""
        for item in self._output_log.selectedItems():
            text = item.text()
            clipboard_text += text
            if text:
                clipboard_text += "\n"
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(clipboard_text)

    def _show_context_menu(self, pos):
        menu = QtWidgets.QMenu(parent=self._output_log)

        if self._output_log.selectedItems():
            copy_action = menu.addAction("Copy Selected Message")
            copy_action.triggered.connect(self._copy_to_clipboard)

        clear_action = menu.addAction("Clear")
        clear_action.triggered.connect(self._output_log.clear)

        debug_message_action = menu.addAction("Debug Messages")
        debug_message_action.setCheckable(True)
        debug_message_action.setChecked(
            bool(int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.debug}", fallback=True)))
        )
        debug_message_action.toggled.connect(partial(self._refresh_log, LogLevels.debug))

        info_message_action = menu.addAction("Informational Messages")
        info_message_action.setCheckable(True)
        info_message_action.setChecked(
            bool(int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.info}", fallback=True)))
        )
        info_message_action.toggled.connect(partial(self._refresh_log, LogLevels.info))

        warning_message_action = menu.addAction("Warnings")
        warning_message_action.setCheckable(True)
        warning_message_action.setChecked(
            bool(int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.warning}", fallback=True)))
        )
        warning_message_action.toggled.connect(partial(self._refresh_log, LogLevels.warning))

        error_message_action = menu.addAction("Errors")
        error_message_action.setCheckable(True)
        error_message_action.setChecked(
            bool(int(settings.SettingsManager.get_setting(f"log_widget:{LogLevels.error}", fallback=True)))
        )
        error_message_action.toggled.connect(partial(self._refresh_log, LogLevels.error))

        expandable_log_action = menu.addAction("Toggle Expandable Log")
        expandable_log_action.setCheckable(True)
        expandable_log_action.setChecked(
            bool(int(settings.SettingsManager.get_setting("log_widget:expandable", fallback=False)))
        )
        expandable_log_action.toggled.connect(self._toggle_expandable_log)

        menu.exec_(QtGui.QCursor.pos())
