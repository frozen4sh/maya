# Copyright Epic Games, Inc. All Rights Reserved.
from qtpy import QtGui, QtCore

from . import lib

FONT_MAP = {
    "material": {
        "regular": {"family": "Material Icons", "file": "MaterialIcons-Regular"},
        "outlined": {"family": "Material Icons Outlined", "file": "MaterialIconsOutlined-Regular"},
        "round": {"family": "Material Icons Round", "file": "MaterialIconsRound-Regular"},
        "sharp": {"family": "Material Icons Sharp", "file": "MaterialIconsSharp-Regular"},
        "twotone": {"family": "Material Icons TwoTone", "file": "MaterialIconsTwoTone-Regular"},
    },
    "epic": {
        "regular": {"family": "epicdesignsystem", "file": "epicdesignsystem"},
    },
}


class FontIcons:
    def __init__(self, font=None, style=None):
        self._font = font or "material"
        self._style = style or "regular"
        self._codes = self._get_codes()

    @property
    def family(self):
        return FONT_MAP[self.font][self.style]["family"]

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        self._style = value

    def __getitem__(self, code):
        return self._codes.get(code)

    def __len__(self):
        return len(self._codes.items())

    def items(self):
        return self._codes.items()

    def _get_codes(self):
        file = f"{FONT_MAP[self.font][self.style]['file']}.codepoints"
        codepoints_file = lib.resource("font", self.font, file)
        lines = []
        with open(codepoints_file, encoding="utf-8") as f:
            lines = f.readlines()
        strip_list = [line.strip().split(" ") for line in lines if line.strip()]
        codes = {}
        for key, code in strip_list:
            codes[key] = chr(int(code, base=16))
        return codes

    # --------------------------------------------------------------------------

    def has(self, code):
        return code in self._codes.values()

    def get(self, code, default=None):
        return self._codes.get(code, default)

    def icon(self, code, size=64, color="#DDDDDD"):
        return QtGui.QIcon(self.pixmap(code, size, color))

    def pixmap(self, code, size, color):
        text = self._codes.get(code)
        color = QtGui.QColor(color)

        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        font = QtGui.QFont(self.family)
        font.setPixelSize(size)

        painter.setFont(font)
        painter.setPen(color)

        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, text)
        painter.end()
        return pixmap
