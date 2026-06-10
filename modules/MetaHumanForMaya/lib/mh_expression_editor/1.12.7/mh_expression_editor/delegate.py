# Copyright Epic Games, Inc. All Rights Reserved.

from qtpy import QtGui, QtCore, QtWidgets

from . import roles
from .utils import general
from .colors import COLORS


class ItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_height = 20

    def paint(self, painter, option, index):
        # Data
        item_name = index.data(QtCore.Qt.DisplayRole)
        item_loaded = index.data(roles.ITEM_LOADED)
        item_visible = index.data(roles.ITEM_VISIBLE)
        item_selectable = index.data(roles.ITEM_SELECTABLE)

        body_rect = QtCore.QRectF(option.rect).adjusted(0, 0, 0, 0)
        body_rect.setHeight(self.item_height)
        content_rect = body_rect.adjusted(0, 0, 0, 0)

        if item_selectable:
            if option.state & QtWidgets.QStyle.State_Selected:
                painter.fillRect(content_rect, COLORS["selected"])

        # Save state
        painter.save()
        padding = 4

        # Fonts
        normal_font = QtGui.QFont("Open Sans", 8)
        QtGui.QFont("Open Sans", 8, QtGui.QFont.Bold)

        # Icon
        image_holder_rect = QtCore.QRectF(body_rect)
        image_holder_rect.setWidth(content_rect.height())
        image_holder_rect.setHeight(content_rect.height())

        image_rect = QtCore.QRectF(image_holder_rect)
        image_rect.setWidth(image_holder_rect.width() - 6)
        image_rect.setHeight(image_holder_rect.height() - 6)

        image_file = "object_loaded.png" if item_loaded else "object_unloaded.png"
        image_data = QtGui.QIcon(general.resource("icon/{}".format(image_file)))
        image_pixmap_scaled = image_data.pixmap(QtCore.QSize(image_rect.width(), image_rect.height()))
        painter.drawPixmap(image_rect.x() + 3, image_rect.y() + 3, image_pixmap_scaled)

        # Data boxes width
        data_width = (content_rect.width() - (2 * content_rect.height())) - (padding + image_rect.width())

        # Code
        painter.setFont(normal_font)
        name_rect = QtCore.QRectF(content_rect)
        name_rect.setRect(
            image_holder_rect.right() + padding,
            content_rect.y(),
            data_width,
            content_rect.height(),
        )
        painter.setPen(COLORS["text"] if item_selectable else COLORS["gray"])
        painter.drawText(name_rect, QtCore.Qt.AlignVCenter, item_name)

        # Status
        status_rect = QtCore.QRectF(content_rect)
        status_rect.setWidth(content_rect.height() - 2)
        status_rect.setHeight(content_rect.height() - 2)
        status_rect.translate(content_rect.width() - content_rect.height() - 1, 1)

        if item_loaded:
            status_image_file = "object_visible.png" if item_visible else "object_invisible.png"
            status_image_data = QtGui.QIcon(general.resource("icon/{}".format(status_image_file)))
            status_image_pixmap_scaled = status_image_data.pixmap(QtCore.QSize(10, 10))
            painter.drawPixmap(
                status_rect.x() + (status_rect.width() / 2 - status_image_pixmap_scaled.width() / 2),
                status_rect.y() + (status_rect.height() / 2 - status_image_pixmap_scaled.height() / 2),
                status_image_pixmap_scaled,
            )

        # Color the border around body rect
        painter.setPen(COLORS["border"])
        painter.setOpacity(0)

        # Body
        painter.drawRect(body_rect)

        # Restore
        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(option.rect.width(), self.item_height)
