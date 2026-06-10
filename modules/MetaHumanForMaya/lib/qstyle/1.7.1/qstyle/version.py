# Copyright Epic Games, Inc. All Rights Reserved.
VERSION_MAJOR = 1
VERSION_MINOR = 7
VERSION_PATCH = 1

version_info = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
version = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
__version__ = version

__all__ = ["version", "version_info", "__version__"]
