# Copyright Epic Games, Inc. All Rights Reserved.
"""
DNA units wrapper enumerations.
"""
from enum import Enum

from dna import (
    TranslationUnit_m,
    TranslationUnit_cm,
    RotationUnit_degrees,
    RotationUnit_radians,
)


class TranslationUnit(Enum):
    cm = TranslationUnit_cm
    m = TranslationUnit_m


class RotationUnit(Enum):
    degree = RotationUnit_degrees
    radian = RotationUnit_radians
