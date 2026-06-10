# Copyright Epic Games, Inc. All Rights Reserved.

from enum import Enum
from collections import deque, namedtuple

from qtpy import QtGui, QtSvg, QtCore, QtWidgets

from ..model import NodeModel, SceneModel
from ..utils import general
from ..control import Controller
from .settings import Settings

logger = general.get_logger()

Size = namedtuple("Size", ["w", "h"])

NODE_HEIGHT = 69
NODE_WIDTH = NODE_HEIGHT * 2 * 1.618  # golden ratio
NODE_RADIUS = NODE_HEIGHT * 0.16 * 1.618  # NODE_HEIGHT * 0.05
VERTICAL_SPACING = NODE_HEIGHT * 1.618
HORIZONTAL_SPACING = NODE_WIDTH * 1.618
VERTICAL_GRID_SPACING = VERTICAL_SPACING / 4
HORIZONTAL_GRID_SPACING = HORIZONTAL_SPACING / 8


class Color(Enum):
    BACKGROUND_DEFAULT = "#141414"
    BACKGROUND_PAPER = "#272727"
    DEFAULT = "#3A3A3A"
    LINE = "#616161"
    TEXT = "#fff"
    PRIMARY = "#0074E4"  # ,BLUE
    PRIMARY_LIGHT = "#339BFF"  # ,BLUE
    SUCCESSS = "#0B873A"  # ,GREEN
    SUCCESSS_LIGHT = "#11CF59"  # ,GREEN
    WARNING = "#FFA640"  # ,YELLOW
    WARNING_LIGHT = "#FFCB8F"  # ,YELLOW
    ERROR = "#DE3341"  # ,RED
    ERROR_LIGHT = "#E97780"  # ,RED
    INFO = "#6C5BB7"  # ,VIOLATE
    INFO_LIGHT = "#9D91CF"  # ,VIOLATE


class IconPaths(Enum):
    paint = general.resource("icon", "paint.svg")
    receive = general.resource("icon", "receive.svg")
    disabled = general.resource("icon", "disabled.svg")
    fill = general.resource("icon", "fill.svg")
    locked = general.resource("icon", "locked.svg")
    unlocked = general.resource("icon", "unlocked.svg")


class Node(QtWidgets.QGraphicsItem):
    def __init__(self, name, layer=0, parent=None):
        super().__init__()
        self._parent = parent
        self._size = Size(NODE_WIDTH, NODE_HEIGHT)

        self.name = name
        self.display_name = name.replace("_", " ")
        self.inputs = []
        self.outputs = []
        self.layer = layer

        # states
        self.downstream = False
        self.upstream = False
        self._active = False
        self._disabled = False
        self._locked = False
        self.position = (0.0, 0.0)

        self._custom_color = QtGui.QColor(Color.DEFAULT.value)
        self._background_color = QtGui.QColor(Color.DEFAULT.value)

        self.lock_btn = LockBtn(self)
        self.color_btn = ColorBtn(self)
        self.position_lock_color()

        # config
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

        self.model = None
        self.setToolTip(self.name)
        self.controller: Controller = Controller()
        self.graph_view: GraphView = parent.views()[0]

        self._analyzed_color = QtGui.QColor(Color.DEFAULT.value)
        self.analyzed = False

        self.icon_renderer = QtSvg.QSvgRenderer()

    def set_model(self, model: NodeModel):
        self.model = model

    def load_from_model(self, skip_position=False):
        self.name = self.model.name
        self.layer = self.model.layer
        if not skip_position:
            self.setPos(*self.model.position)
        self._active = self.model._active
        self.downstream = self.model.downstream
        self.upstream = self.model.upstream
        self._disabled = self.model._disabled
        self.lock_btn.set_locked(self.model._locked)
        self._custom_color = QtGui.QColor(self.model._custom_color)

    def reset_highlight(self):
        self.downstream = False
        self.upstream = False
        self._active = False

    def reset_color(self):
        self._custom_color = QtGui.QColor(Color.DEFAULT.value)
        self.color_btn.set_color(self._custom_color)

    def reset_lock(self):
        self.lock_btn.set_locked(False)
        self._disabled = False

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if self._parent.snap_to_grid:
                value.setX(round(value.x() / HORIZONTAL_GRID_SPACING) * HORIZONTAL_GRID_SPACING)
                value.setY(round(value.y() / VERTICAL_GRID_SPACING) * VERTICAL_GRID_SPACING)
        return super().itemChange(change, value)

    def boundingRect(self):
        return QtCore.QRectF(0, 0, self._size.w, self._size.h)

    def paint(self, painter, option, widget):
        self._border_color = QtGui.QColor(Color.WARNING_LIGHT.value)
        self._background_color = self._custom_color
        _border_radius = 1
        _opacity = 0.4 if self._parent.get_active_node() else 0.7

        if self.isSelected():
            self._border_color = QtGui.QColor(Color.WARNING.value)
            _border_radius = 3
            _opacity = 1
        elif self.upstream:
            self._border_color = QtGui.QColor(Color.INFO_LIGHT.value)
            _border_radius = 3
            _opacity = 0.7
        elif self.downstream:
            if self.lock_btn.is_locked() or self._disabled:
                self._border_color = QtGui.QColor(Color.ERROR.value)
                _border_radius = 3
                _opacity = 0.7
            else:
                self._border_color = QtGui.QColor(Color.PRIMARY_LIGHT.value)
                _border_radius = 3
                _opacity = 1
        elif not self.isSelected() and not self.upstream and not self.downstream:
            self._border_color = QtGui.QColor(Color.LINE.value)
            _border_radius = 1

        if self._active:
            self._border_color = QtGui.QColor(Color.SUCCESSS.value)
            _border_radius = 4
            _opacity = 1

        self.setOpacity(_opacity)

        # border and fill
        pen = QtGui.QPen(self._border_color, _border_radius)
        pen.setJoinStyle(QtCore.Qt.MiterJoin)

        painter.setPen(pen)
        painter.setBrush(self._background_color)

        painter.drawRoundedRect(0, 0, self._size.w, self._size.h, NODE_RADIUS, NODE_RADIUS)

        if self._active and self.isSelected():
            dash_pen = QtGui.QPen(
                QtGui.QColor(Color.WARNING.value), 4, QtCore.Qt.DashLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin
            )
            dash_pen.setDashPattern([2, 4])
            painter.setPen(dash_pen)
            painter.setBrush(QtCore.Qt.transparent)
            painter.drawRoundedRect(self.boundingRect(), NODE_RADIUS, NODE_RADIUS)

        if self.analyzed:
            analyzed_pen = QtGui.QPen()
            analyzed_pen.setStyle(QtCore.Qt.NoPen)
            painter.setPen(analyzed_pen)
            painter.setBrush(self._analyzed_color)
            painter.drawRoundedRect(0, 0, NODE_WIDTH / 6, NODE_HEIGHT, NODE_RADIUS, NODE_RADIUS)

        pen.setColor(QtGui.QColor(Color.TEXT.value))
        painter.setPen(pen)
        painter.drawText(
            QtCore.QRectF(0, self._size.h / 2, self._size.w, self._size.h / 2),
            QtCore.Qt.AlignCenter,
            self.display_name,
        )
        icon_rect = QtCore.QRectF(16, 16, 16, 16)
        if self._active and self.controller.editing_expression:
            self.icon_renderer.load(IconPaths.paint.value)
            self.icon_renderer.render(painter, icon_rect)
        elif self.downstream and not self.lock_btn.is_locked() and not self._disabled:
            self.icon_renderer.load(IconPaths.receive.value)
            self.icon_renderer.render(painter, icon_rect)
        elif self.downstream and not self.lock_btn.is_locked() and self._disabled:
            self.icon_renderer.load(IconPaths.disabled.value)
            self.icon_renderer.render(painter, icon_rect)

    def start_point(self):
        return QtCore.QPointF(self.scenePos().x() + self._size.w, self.scenePos().y() + self._size.h / 2)

    def end_point(self):
        return QtCore.QPointF(self.scenePos().x(), self.scenePos().y() + self._size.h / 2)

    def position_lock_color(self):
        self.lock_btn.setPos(self.scenePos().x() + self._size.w / 2 - 32, self.scenePos().y() + 8)
        self.color_btn.setPos(self.scenePos().x() + self._size.w / 2, self.scenePos().y() + 8)

    def mouseDoubleClickEvent(self, event):
        self.activate()
        self.controller.double_click_editing(self)

    def activate(self):
        self.update_children_state()
        self._active = True
        self.update()
        self.update_children_disabled_state()

    def mousePressEvent(self, event):
        if not self.controller.editing_expression:
            if self.graph_view.highlight_last_selected_action.isChecked():
                self.activate()
            if self.graph_view.expression_preview_action.isChecked():
                self.controller.preview_selection(self, True)
        super().mousePressEvent(event)

    def update_children_disabled_state(self, skip=False):
        nodes_to_process = deque([self])
        # Disable the current node if its lock button is locked
        self.set_disabled(self.lock_btn.is_locked())
        # If all active or downstream inputs are locked, disable current node
        active_down_locked = [inp.lock_btn.is_locked() for inp in self.inputs if inp.downstream]
        if all(active_down_locked) and active_down_locked:
            self.set_disabled(True)
        while nodes_to_process:
            current = nodes_to_process.popleft()
            for output in current.outputs:
                if output._active:
                    continue
                if not output.lock_btn.is_locked():
                    if any([inp for inp in output.inputs if inp._active]):
                        output.set_disabled(False)
                    else:
                        output.set_disabled(
                            all([inp.is_disabled() for inp in output.inputs if inp.downstream or inp._active])
                        )
                nodes_to_process.append(output)

        if self.controller.editing_expression and not skip and Settings().get_setting("advanced_propagation"):
            self._parent.modeling_state()

    def update_children_state(self):
        self._parent.reset_highlight_state(update=True)
        queue_down = deque([self])
        while queue_down:
            current = queue_down.popleft()
            for output in current.outputs:
                output.downstream = True
                output.update()
                queue_down.append(output)
        queue_up = deque([self])
        while queue_up:
            current = queue_up.popleft()
            for inp in current.inputs:
                inp.upstream = True
                inp.update()
                queue_up.append(inp)

    def is_disabled(self):
        return self._disabled

    def is_locked(self):
        return self.lock_btn.is_locked()

    def set_disabled(self, disabled: bool):
        self._disabled = disabled

    def update_color(self):
        self._custom_color = self.color_btn.color()
        self.update()

    def set_analyzed(self, color):
        self._analyzed_color = QtGui.QColor(*color)
        self.analyzed = True
        self.update()

    def __repr__(self) -> str:
        return f"{self.name}"


class Connection(QtWidgets.QGraphicsLineItem):
    def __init__(self, source: Node, target: Node):
        super().__init__()

        self.source = source
        self.target = target
        self._color = QtGui.QColor(Color.LINE.value)

        self.setZValue(-1)

    def boundingRect(self):
        return QtCore.QRectF(self._source_point(), self._target_point()).normalized().adjusted(-20, -20, 20, 20)

    def paint(self, painter, option, widget):
        if self.source.lock_btn.is_locked() or self.target.lock_btn.is_locked() or self.source._disabled:
            pen = QtGui.QPen(
                QtGui.QColor(Color.ERROR.value), 0.5, QtCore.Qt.DashLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin
            )
        elif self.source.downstream or self.source._active:
            pen = QtGui.QPen(
                QtGui.QColor(Color.PRIMARY_LIGHT.value),
                1,
                QtCore.Qt.SolidLine,
                QtCore.Qt.RoundCap,
                QtCore.Qt.RoundJoin,
            )
        elif self.target.upstream or self.target._active:
            pen = QtGui.QPen(
                QtGui.QColor(Color.INFO_LIGHT.value),
                1,
                QtCore.Qt.SolidLine,
                QtCore.Qt.RoundCap,
                QtCore.Qt.RoundJoin,
            )
        else:
            pen = QtGui.QPen(self._color, 0.2, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            self.setOpacity(0.5)

        painter.setPen(pen)

        path = QtGui.QPainterPath()
        path.moveTo(self._source_point())
        path.cubicTo(self._cp1(), self._cp2(), self._target_point())
        painter.drawPath(path)

    def _source_point(self):
        return self.source.start_point()

    def _target_point(self):
        return self.target.end_point()

    def _cp1(self):
        source = self._source_point()
        dest = self._target_point()
        return QtCore.QPointF(source.x() + (dest.x() - source.x()) * 0.5, source.y())

    def _cp2(self):
        source = self._source_point()
        dest = self._target_point()
        return QtCore.QPointF(dest.x() - (dest.x() - source.x()) * 0.5, dest.y())


class GraphView(QtWidgets.QGraphicsView):
    VIEW_STATE_SELECT = 0
    VIEW_STATE_PAN = 1
    VIEW_STATE_ZOOM = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        # state
        self.view_mode = GraphView.VIEW_STATE_SELECT
        self._last_mouse_position = QtCore.QPointF()
        self.editing = False

        # config
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setOptimizationFlag(QtWidgets.QGraphicsView.DontAdjustForAntialiasing)
        self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemShape)

        # model
        self.setScene(GraphScene(self))
        self.model = None
        self.controller: Controller = Controller()

        # context menu
        self._create_actions()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.custom_context_menu)

        # status_legend
        self.status = GraphStatus(self)
        self.update_status_text()

    @property
    def control_preview_state(self):
        return self.control_preview_action.isChecked()

    @property
    def expression_preview_state(self):
        return self.expression_preview_action.isChecked()

    @property
    def highlight_last_selected_state(self):
        return self.highlight_last_selected_action.isChecked()

    def update_status_text(self):
        controller_color = "green" if self.controller.editing_expression else "red"
        advanced_propagation_color = "green" if Settings().get_setting("advanced_propagation") else "red"
        expression_preview_color = "green" if self.expression_preview_action.isChecked() else "red"
        highlight_color = "green" if self.highlight_last_selected_action.isChecked() else "red"
        self.status.update_text(
            f"\
            State:<br>Editing: <font color={controller_color}>{bool(self.controller.editing_expression)}</font>\
            <br>Advanced Propagation: <font color='{advanced_propagation_color}'>{str(Settings().get_setting('advanced_propagation'))}</font>\
            <br>Expression Preview: <font color='{expression_preview_color}'>{self.expression_preview_action.isChecked()}</font>\
            <br>Highlight Last Selected: <font color='{highlight_color}'>{self.highlight_last_selected_action.isChecked()}</font>\
            "
        )

    def eventFilter(self, source, event):
        self.status.update_position(self)
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.status.update_position(self)

    def _create_actions(self):
        # Control Expression Preview
        self.control_preview_action = QtWidgets.QAction("Update Analysis on Control Selection", self)
        self.control_preview_action.setCheckable(True)
        self.control_preview_action.setChecked(Settings().get_setting("update_analysis_on_control_selection"))
        self.control_preview_action.triggered.connect(self.on_control_preview)
        # Expression Preview
        self.expression_preview_action = QtWidgets.QAction("Preview Selected Node", self)
        self.expression_preview_action.setCheckable(True)
        self.expression_preview_action.setChecked(Settings().get_setting("preview_selected_node"))
        self.expression_preview_action.triggered.connect(self.on_expression_preview)

        self.highlight_last_selected_action = QtWidgets.QAction("Highlight Last Selected", self)
        self.highlight_last_selected_action.setCheckable(True)
        self.highlight_last_selected_action.setChecked(Settings().get_setting("highlight_last_selected"))
        self.highlight_last_selected_action.triggered.connect(self.on_highlight_last_selected)
        # Locking
        self.lock_selected_action = QtWidgets.QAction("Toggle Lock", self)
        self.lock_selected_action.triggered.connect(self.on_lock_selected)
        # Color
        self.color_selected_action = QtWidgets.QAction("Change Color", self)
        self.color_selected_action.triggered.connect(self.on_color_selected)
        # Reset Color
        self.reset_color_selected_action = QtWidgets.QAction("Reset Color", self)
        self.reset_color_selected_action.triggered.connect(self.on_reset_color_selected)
        # Copy Joints
        self.copy_joints_action = QtWidgets.QAction("Copy Expression Joints", self)
        self.copy_joints_action.triggered.connect(self.on_copy_joints_selected)
        # Reset graph
        self.reset_graph_action = QtWidgets.QAction("Reset Graph", self)
        self.reset_graph_action.triggered.connect(self.on_reset_graph)
        # Move to editing
        self.move_to_editing_action = QtWidgets.QAction("Move to Editable Elements", self)
        self.move_to_editing_action.triggered.connect(self.on_move_to_editing)
        # Move to preview
        self.move_to_preview_action = QtWidgets.QAction("Move to Selected Preview Shape", self)
        self.move_to_preview_action.triggered.connect(self.on_move_to_preview)

        # Subview
        self.isolate_branch_action = QtWidgets.QAction("Isolate Selected Branches", self)
        self.isolate_branch_action.triggered.connect(self.on_isolate_selected_branches)
        self.isolate_highlighted_action = QtWidgets.QAction("Isolate Highlighted ", self)
        self.isolate_highlighted_action.triggered.connect(self.on_isolate_highlighted)

        # selection
        self.select_upstream_action = QtWidgets.QAction("Select Upstream Nodes", self)
        self.select_upstream_action.triggered.connect(lambda: self.on_select_action(True, False))
        self.select_downstream_action = QtWidgets.QAction("Select Downstream Nodes", self)
        self.select_downstream_action.triggered.connect(lambda: self.on_select_action(False, True))
        self.select_branch_action = QtWidgets.QAction("Select Upstream and Downstream Nodes", self)
        self.select_branch_action.triggered.connect(lambda: self.on_select_action())

    def on_select_action(self, select_downstream=True, select_upstream=True):
        selected = self.scene().selectedItems()
        if not selected:
            return

        for sel in selected:
            if select_downstream:
                queue_inputs = deque([sel])
                while queue_inputs:
                    current = queue_inputs.popleft()
                    for inp in current.inputs:
                        inp.setSelected(True)
                        queue_inputs.append(inp)

            if select_upstream:
                queue_outputs = deque([sel])
                while queue_outputs:
                    current = queue_outputs.popleft()
                    for out in current.outputs:
                        out.setSelected(True)
                        queue_outputs.append(out)

    def on_control_preview(self):
        self.controller.update_control_preview(self.control_preview_action.isChecked())

    def update_control_preview_state(self, state):
        self.control_preview_action.setChecked(state)
        Settings().set_setting("update_analysis_on_control_selection", state)

    def on_expression_preview(self):
        if not self.expression_preview_action.isChecked():
            self.controller.reset_controls()
        self.controller.update_expression_preview(self.expression_preview_action.isChecked())

    def update_expression_preview_state(self, state):
        self.expression_preview_action.setChecked(state)
        Settings().set_setting("preview_selected_node", state)
        self.update_status_text()

    def on_highlight_last_selected(self):
        self.controller.update_highlight_selected(self.highlight_last_selected_action.isChecked())

    def update_highlight_last_selected_state(self, state):
        self.highlight_last_selected_action.setChecked(state)
        Settings().set_setting("highlight_last_selected", state)
        self.update_status_text()

    def custom_context_menu(self):
        menu = QtWidgets.QMenu(parent=self)
        if self.scene().selectedItems() and not self.controller.editing_expression:
            selected_expression_name = self.scene().selectedItems()[-1].name
            number_of_phases = Controller().get_phase_count(selected_expression_name)
            if number_of_phases > 1:
                menu.addSection("Phases Preview")
                for phase in range(number_of_phases):
                    phase_action = QtWidgets.QAction(f"Preview {selected_expression_name}, phase {phase + 1}", self)
                    menu.addAction(phase_action)
                    phase_action.triggered.connect(
                        lambda checked=None, expression_name=selected_expression_name, phase_number=phase + 1: self.on_preview_phase_expression(
                            expression_name, phase_number
                        )
                    )

        menu.addSection("Selection")
        menu.addAction(self.select_upstream_action)
        menu.addAction(self.select_downstream_action)
        menu.addAction(self.select_branch_action)
        if self.controller.editing_expression:
            menu.addSeparator()
            menu.addAction(self.move_to_editing_action)
            menu.addAction(self.move_to_preview_action)
        menu.addSeparator()
        menu.addAction(self.lock_selected_action)
        menu.addAction(self.color_selected_action)
        menu.addAction(self.reset_color_selected_action)
        menu.addSeparator()
        menu.addAction(self.copy_joints_action)
        if not self.controller.editing_expression:
            menu.addSeparator()
            menu.addAction(self.control_preview_action)
            menu.addAction(self.expression_preview_action)
            menu.addAction(self.highlight_last_selected_action)
            menu.addSeparator()
            menu.addAction(self.isolate_branch_action)
            menu.addAction(self.isolate_highlighted_action)
            menu.addSeparator()
            menu.addAction(self.reset_graph_action)
        menu.exec_(QtGui.QCursor.pos())

    def on_reset_graph(self):
        self.scene().rearrange_scene()
        self.scene().reset_everything()

    def on_move_to_editing(self):
        Controller().move_to_editing()

    def on_move_to_preview(self):
        if Controller().node_exists():
            logger.warning("The rig editing scene needs to be assembled previewing expressions.")
            return
        if not self.scene().selectedItems():
            logger.warning("An expression needs to be selected for it to be previewed.")
            return
        if len(self.scene().selectedItems()) > 1:
            logger.warning("Select a single expression preview to move to.")
            return
        Controller().move_to_preview(self.scene().selectedItems()[0].name)

    def on_lock_selected(self):
        selected = self.scene().selectedItems()
        if not selected:
            return

        for item in selected:
            if isinstance(item, Node):
                item.lock_btn.context_lock()

    def on_color_selected(self):
        selected = self.scene().selectedItems()
        if not selected:
            return
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            for item in selected:
                if isinstance(item, Node):
                    item.color_btn.set_color(color)
                    item.update_color()

    def on_reset_color_selected(self):
        for item in self.scene().selectedItems():
            if isinstance(item, Node):
                item.color_btn.set_color(QtGui.QColor(Color.DEFAULT.value))
                item.update_color()

    def on_copy_joints_selected(self):
        if Controller().node_exists():
            logger.warning("The rig editing scene needs to be assembled before expression joints can be copied.")
            return
        if not self.scene().selectedItems():
            logger.warning("An expression needs to be selected to copy expression joints.")
            return
        if len(self.scene().selectedItems()) > 1:
            logger.warning("Expression joints can be copied from a single expression.")
            return
        try:
            Controller().copy_joints_from_graph(self._parent.rig, self.scene().selectedItems()[0].name)
        except RuntimeWarning as e:
            logger.warning(e)
        else:
            logger.info(f"Expression joints copied from {self.scene().selectedItems()[0].name}.")

    def on_isolate_highlighted(self):
        selected = [item for item in self.scene().nodes if item._active or item.downstream or item.upstream]
        if not selected:
            return

        name = selected[0].name
        scene_model = SceneModel()
        for item in selected:
            if isinstance(item, Node):
                if item._active:
                    name = item.name
                node_model = NodeModel().copy(item)
                scene_model.nodes[item.name] = node_model
        self._parent.add_view(scene_model, name, preset=True)

    def on_isolate_selected_branches(self):
        selected = self.scene().selectedItems()
        if not selected:
            return

        new_selected = []
        for node in selected:
            node.activate()
            new_selected.extend([item for item in self.scene().nodes if item._active or item.downstream])
        new_selected.sort(key=lambda x: x.layer)

        name = selected[0].name if len(selected) == 1 else "Multiple Root Nodes"
        scene_model = SceneModel()
        for item in new_selected:
            if isinstance(item, Node):
                node_model = NodeModel().copy(item)
                scene_model.nodes[item.name] = node_model
        self._parent.add_view(scene_model, name, preset=True)

    def set_model(self, model: SceneModel):
        self.model = model

    def update_model(self):
        for node in self.scene().nodes:
            node: Node
            node_model = NodeModel(
                name=node.name,
                layer=node.layer,
                inputs=[inp.name for inp in node.inputs],
                outputs=[out.name for out in node.outputs],
                position=(node.scenePos().x(), node.scenePos().y()),
                _active=node._active,
                downstream=node.downstream,
                upstream=node.upstream,
                _disabled=node._disabled,
                _locked=node._locked,
                _custom_color=node._custom_color.name(),
            )
            self.model.nodes[node.name] = node_model

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        # Save the scene pos
        old_pos = self.mapToScene(event.pos())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

        # Get the new position
        new_pos = self.mapToScene(event.pos())

        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def check_scene_bonds(self):
        self._base_padding = 50
        scale_factor = self.transform().m11()
        dynamic_padding = self._base_padding / scale_factor

        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        scene_rect = self.sceneRect()

        expand = False
        new_scene_rect = scene_rect

        # Check if we need to expand the scene rect
        if view_rect.left() < scene_rect.left() + dynamic_padding:
            new_scene_rect.setLeft(scene_rect.left() - dynamic_padding)
            expand = True
        if view_rect.right() > scene_rect.right() - dynamic_padding:
            new_scene_rect.setRight(scene_rect.right() + dynamic_padding)
            expand = True
        if view_rect.top() < scene_rect.top() + dynamic_padding:
            new_scene_rect.setTop(scene_rect.top() - dynamic_padding)
            expand = True
        if view_rect.bottom() > scene_rect.bottom() - dynamic_padding:
            new_scene_rect.setBottom(scene_rect.bottom() + dynamic_padding)
            expand = True

        if expand:
            self.setSceneRect(new_scene_rect)

    def mouseMoveEvent(self, event):
        if self.view_mode == self.VIEW_STATE_PAN:
            delta = self.mapToScene(event.pos()) - self.mapToScene(self._last_mouse_position)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.translate(delta.x(), delta.y())
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.check_scene_bonds()
            self._last_mouse_position = event.pos()
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self._last_mouse_position = event.pos()
        if event.button() == QtCore.Qt.MidButton:
            self.view_mode = self.VIEW_STATE_PAN
        elif event.button() == QtCore.Qt.LeftButton:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.view_mode != self.VIEW_STATE_SELECT:
            self.view_mode = self.VIEW_STATE_SELECT
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        items = self.items(event.pos())
        for item in items:
            if any([isinstance(item, LockBtn) for item in items]) or any(
                [isinstance(item, ColorBtn) for item in items]
            ):
                break
            if isinstance(item, Node) and item.contains(item.mapFromScene(self.mapToScene(event.pos()))):
                item: Node
                self.controller.double_click_editing(item)
                if self.controller.editing_expression:
                    event.accept()
                    return
                if not item._active:
                    return super().mouseDoubleClickEvent(event)

        if not items and not self.controller.editing_expression:
            self.controller.reset_controls()
            self.scene().reset_highlight_state(update=True)
            return super().mouseDoubleClickEvent(event)

    def focus_modeling_items(self):
        selected_items = self.scene().get_all_modeling_nodes()
        if not selected_items:
            return
        self.fit_to_view(selected_items)

    def focus(self):
        resize = False
        selected_items = self.scene().selectedItems()
        if not selected_items:
            selected_items = self.scene().get_all_modeling_nodes()

        if not selected_items:
            resize = True
            selected_items = self.scene().nodes

        self.fit_to_view(selected_items, resize_rect=resize)

    def fit_to_view(self, items, resize_rect=False, ensure_visible=False):
        bounds = QtCore.QRectF()
        for item in items:
            bounds = bounds.united(item.sceneBoundingRect())

        margin = 20
        bounds.adjust(-margin, -margin, margin, margin)

        if resize_rect:
            self.scene().setSceneRect(bounds)

        if ensure_visible:
            self.ensure_selection_visible(items[0])
            return

        self.fitInView(bounds, QtCore.Qt.KeepAspectRatio)
        self.centerOn(bounds.center())

    def ensure_selection_visible(self, item):
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        item_rect = item.sceneBoundingRect()

        if not view_rect.contains(item_rect):
            self.ensureVisible(item)

    def swap_node_selection(self, node_index):
        self.scene().reset_selection()
        node = self.scene().nodes[node_index]
        node.setSelected(True)
        self.fit_to_view([node], ensure_visible=True)
        self.controller.preview_selection(node, self.expression_preview_action.isChecked())
        if Settings().get_setting("highlight_last_selected"):
            node.activate()

    def keyPressEvent(self, event):
        arrow_keys = [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]
        if event.key() == QtCore.Qt.Key_F:
            self.focus()
            return
        if event.key() in arrow_keys and not self.controller.editing_expression:
            if len(self.scene().selectedItems()) == 0:
                self.swap_node_selection(0)
            else:
                if event.key() == QtCore.Qt.Key_Up or event.key() == QtCore.Qt.Key_Down:
                    for i, node in enumerate(self.scene().nodes):
                        if node.isSelected():
                            if event.key() == QtCore.Qt.Key_Up and i - 1 >= 0:
                                self.swap_node_selection(i - 1)
                            elif event.key() == QtCore.Qt.Key_Down and i + 1 < len(self.scene().nodes):
                                self.swap_node_selection(i + 1)
                            break
                elif event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_Right:
                    selected_node = None
                    max_layer = 0

                    for item in self.scene().nodes:
                        if max_layer < item.layer:
                            max_layer = item.layer

                    for i, node in enumerate(self.scene().nodes):
                        if node.isSelected():
                            selected_node = node
                            break
                    closest_node_index = None
                    minimal_difference = None
                    target_layer = None
                    if selected_node.layer < max_layer and event.key() == QtCore.Qt.Key_Right:  # Right
                        target_layer = selected_node.layer + 1
                    elif selected_node.layer > 0 and event.key() == QtCore.Qt.Key_Left:  # Left
                        target_layer = selected_node.layer - 1
                    for j, node in enumerate(self.scene().nodes):
                        if node.layer == target_layer:
                            if minimal_difference is None:
                                minimal_difference = abs(selected_node.pos().y() - node.pos().y())
                                closest_node_index = j
                            if abs(selected_node.pos().y() - node.pos().y()) <= minimal_difference:
                                minimal_difference = abs(selected_node.pos().y() - node.pos().y())
                                closest_node_index = j
                    if closest_node_index is not None:
                        self.swap_node_selection(closest_node_index)
        else:
            super().keyPressEvent(event)

    def on_preview_phase_expression(self, expression_name, phase_number):
        Controller().update_phase_controls(expression_name, phase_number)


class GraphScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        # config
        self.setBackgroundBrush(QtGui.QColor(Color.BACKGROUND_DEFAULT.value))

        # internal
        self.nodes = []
        self.snap_to_grid = True

        self.prev_modeling_state = {}

    def add_node(self, node: Node):
        self.nodes.append(node)
        self.addItem(node)

    def add_connection(self, connection: Connection):
        self.addItem(connection)

    def rearrange_scene(self):
        max_layer = max([node.layer for node in self.nodes])

        layer_items = {layer: [] for layer in range(max_layer + 1)}
        for node in self.nodes:
            layer_items[node.layer].append(node)

        for layer, nodes in layer_items.items():
            offset = (max_layer - len(nodes)) * VERTICAL_SPACING / 2
            for i, node in enumerate(nodes):
                node.setPos(layer * HORIZONTAL_SPACING, i * VERTICAL_SPACING + offset)

    def get_node_by_name(self, name):
        for node in self.nodes:
            node: Node
            if node.name == name:
                return node
        return None

    def get_all_modeling_nodes(self):
        result = []
        for node in self.nodes:
            node: Node
            if node._active or node.downstream:
                result.append(node)
        return result

    def get_active_node(self):
        for node in self.nodes:
            node: Node
            if node._active:
                return node
        return None

    def reset_highlight_state(self, update=False):
        for node in self.nodes:
            node: Node
            node.reset_highlight()
            if update:
                node.update()

    def reset_everything(self):
        for node in self.nodes:
            node: Node
            node.reset_highlight()
            node.reset_color()
            node.reset_lock()
            node.analyzed = False
            node.update()

    def reset_selection(self):
        for node in self.nodes:
            node.setSelected(False)

    def reset_editing(self):
        for node in self.nodes:
            node.reset_highlight()

    def reset_modeling_state(self):
        self.prev_modeling_state = {}

    def modeling_state(self):
        modeling = self.get_all_modeling_nodes()
        current_state = {}
        for node in modeling:
            current_state[node.name] = node.is_disabled()

        if self.prev_modeling_state == {}:
            self.prev_modeling_state = current_state

        for expression_name in current_state:
            prev_value = self.prev_modeling_state[expression_name]
            curr_value = current_state[expression_name]
            if prev_value != curr_value:
                if curr_value:
                    self._parent.controller.send_locked_expression(expression_name)
                else:
                    self._parent.controller.send_unlocked_expression(expression_name)

        self.prev_modeling_state = current_state


class ColorBtn(QtWidgets.QGraphicsItem):
    colorStateChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._parent = parent
        self._color = QtGui.QColor(Color.DEFAULT.value)
        self.zValue = 10
        self.icon_renderer = QtSvg.QSvgRenderer(IconPaths.fill.value)

    def boundingRect(self):
        return QtCore.QRectF(0, 0, 32, 32)

    def paint(self, painter, options, widget):
        item_rect = self.boundingRect()
        icon_rect = QtCore.QRectF(item_rect.center().x() / 2, item_rect.center().y() / 2, 16, 16)
        self.icon_renderer.render(painter, icon_rect)

    def mousePressEvent(self, event):
        color = QtWidgets.QColorDialog.getColor(self._color)
        if color.isValid():
            self.set_color(color)
            self._parent.update_color()
        event.accept()
        return

    def set_color(self, color):
        self._color = color
        self.update()

    def color(self):
        return self._color


class LockBtn(QtWidgets.QGraphicsItem):
    lockStateChanged = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._parent = parent
        self._locked = False
        self.setAcceptHoverEvents(True)
        self.zValue = 10
        self.icon_renderer = QtSvg.QSvgRenderer()

    def boundingRect(self):
        return QtCore.QRectF(0, 0, 32, 32)

    def paint(self, painter, options, widget):
        if self._locked:
            painter.setPen(QtGui.QColor(Color.ERROR.value))  # Stroke
            painter.setBrush(QtGui.QColor(Color.ERROR.value))  # Fill for currentColor
            self.icon_renderer.load(IconPaths.locked.value)
        else:
            painter.setPen(QtGui.QColor(Color.DEFAULT.value))  # Stroke
            painter.setBrush(QtGui.QColor(Color.DEFAULT.value))  # Fill for currentColor
            self.icon_renderer.load(IconPaths.unlocked.value)
        item_rect = self.boundingRect()
        icon_rect = QtCore.QRectF(item_rect.center().x() / 2, item_rect.center().y() / 2, 16, 16)
        self.icon_renderer.render(painter, icon_rect)

    def mousePressEvent(self, event):
        self.set_locked(not self._locked)
        self._parent.update_children_disabled_state()
        self.update()
        event.accept()
        self._parent.controller.propagate_lock_to_views(self._parent)
        return

    def context_lock(self):
        self.set_locked(not self._locked)
        self._parent.update_children_disabled_state()
        self.update()
        self._parent.controller.propagate_lock_to_views(self._parent)

    def is_locked(self):
        return self._locked

    def set_locked(self, locked: bool, disabled: bool = False):
        self._locked = locked
        self.parentItem()._locked = locked


class GraphStatus(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.label = QtWidgets.QLabel()
        self.label.setTextFormat(QtCore.Qt.TextFormat.RichText)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        opacity_color_effect = QtWidgets.QGraphicsOpacityEffect(self)
        opacity_color_effect.setOpacity(0.7)
        self.setGraphicsEffect(opacity_color_effect)
        self.update_position(parent)

    def update_text(self, text):
        self.label.setText(text)
        self.update_position(self._parent)

    def update_position(self, view):
        rect = view.viewport().rect()
        self.move(rect.left(), rect.bottom() - self.sizeHint().height())
