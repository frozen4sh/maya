# Copyright Epic Games, Inc. All Rights Reserved.

from __future__ import annotations

import copy
from typing import Tuple
from dataclasses import field, dataclass


def default_field(obj):
    return field(default_factory=lambda: copy.copy(obj))


@dataclass
class NodeModel:
    # basic
    name: str = "Node"
    layer: int = 0
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    position: Tuple[int, int] = default_field((0, 0))

    _active: bool = False
    downstream: bool = False
    upstream: bool = False
    _disabled: bool = False
    _locked: bool = False

    _custom_color: str = "#3A3A3A"

    def copy(self, node) -> NodeModel:
        return NodeModel(
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
            _custom_color=node._custom_color,
        )


@dataclass
class SceneModel:
    nodes: dict = field(default_factory=dict)

    def get_node(self, name: str) -> NodeModel:
        return self.nodes[name]
