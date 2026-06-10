# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations


class RDFModelException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class NotUniqueException(RDFModelException):
    def __init__(self, category: str, identifier: str):
        message = f"Not unique identifier `{identifier}` for category `{category}`."
        super().__init__(message)


class InvalidIndexException(RDFModelException):
    def __init__(self, category: str, index: int):
        message = f"Invalid index `{index}` for category `{category}`."
        super().__init__(message)


class InvalidKeyException(RDFModelException):
    def __init__(self, category: str, key: str):
        message = f"Invalid key `{key}` for category `{category}`."
        super().__init__(message)
