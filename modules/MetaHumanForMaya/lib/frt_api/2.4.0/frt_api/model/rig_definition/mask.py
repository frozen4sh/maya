# Copyright Epic Games, Inc. All Rights Reserved.


class Mask:
    """
    Mask class.
    """

    def __init__(self):
        self.name: str = ""  # (string)
        self.file_path: str = ""  # (string)
        self.file_exists: bool = False  # (boolean)

    def __str__(self):
        return self.name
