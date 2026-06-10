# Copyright Epic Games, Inc. All Rights Reserved.

from maya import mel, cmds

from .publisher import ProgressEnd, ProgressStart, ProgressUpdate


class ProgressBar:
    def __init__(self, title=None, status=None, min_value=0, max_value=100):
        ProgressStart.subscribe(self.start)
        ProgressUpdate.subscribe(self.update)
        ProgressEnd.subscribe(self.end)

        self.title = title or "Progress"
        self.status = status or "Please wait..."
        self.bar = mel.eval("$tmp = $gMainProgressBar")

        cmds.progressBar(self.bar, edit=True, minValue=min_value)
        cmds.progressBar(self.bar, edit=True, maxValue=max_value)

    @property
    def current(self):
        return cmds.progressBar(self.bar, query=True, progress=True)

    @property
    def min_value(self):
        return cmds.progressBar(self.bar, query=True, minValue=True)

    @min_value.setter
    def min_value(self, value):
        cmds.progressBar(self.bar, edit=True, minValue=value)

    @property
    def max_value(self):
        return cmds.progressBar(self.bar, query=True, maxValue=True)

    @max_value.setter
    def max_value(self, value):
        cmds.progressBar(self.bar, edit=True, maxValue=value)

    @property
    def in_progress(self):
        if cmds.progressBar(self.bar, query=True, isCancelled=True):
            return False
        return self.current < self.max_value

    def start(self, max_value=None):
        params = {
            "edit": True,
            "beginProgress": True,
            "minValue": self.min_value,
            "maxValue": max_value or self.max_value,
        }
        cmds.progressBar(self.bar, **params)

    def update(self, status=None, hold=False):
        params = {"edit": True, "status": status or self.status}
        if not hold:
            params["step"] = True
        cmds.progressBar(self.bar, **params)

    def end(self):
        cmds.progressBar(self.bar, edit=True, endProgress=True)
