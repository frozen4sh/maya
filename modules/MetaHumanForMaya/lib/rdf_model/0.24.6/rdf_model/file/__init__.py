# Copyright Epic Games, Inc. All Rights Reserved.
from typing import Any, Union
from xml.etree.ElementTree import Element


def get_value(obj: Union[dict, Element], key: str) -> Any:
    value = obj.get(key)
    if value is None:
        raise KeyError(f"{obj} has no '{key}' key")
    return value
