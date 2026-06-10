# Copyright Epic Games, Inc. All Rights Reserved.

# Internal
from mh_pose_editor.log import LOG


class PoseEditorException(Exception):
    """
    Base Exception for PoseEditor related errors
    """

    def __init__(self, message: str):
        super().__init__(message)
        # Log the message as an error
        LOG.error(message)


class InvalidPoseEditorPlugin(PoseEditorException, RuntimeError):
    """
    Exception raised when no valid plugins could be loaded
    """


class PoseEditorSettingsError(PoseEditorException):
    """
    Raised when a setting is invalid
    """


class InvalidSkeletonConfig(PoseEditorSettingsError):
    """
    Raised when the skeleton config is incorrect
    """


class InvalidMirrorMapping(PoseEditorSettingsError):
    """
    Raised when the mirror mapping is incorrect
    """


class PoseEditorIOError(PoseEditorException):
    """
    Raised when issues with serialization/deserialization arise
    """


class PoseEditorFunctionalityNotImplemented(PoseEditorException):
    """
    Raised when pose editor functionality hasn't been implemented yet
    """


class MessageConnectionError(PoseEditorException):
    """
    Raised when message connections fail.
    """


class InvalidSolverError(PoseEditorException):
    """
    Raised when the incorrect solver type is specified
    """


class InvalidNodeType(PoseEditorException, TypeError):
    """
    Raised when the incorrect node type is specified
    """


class PoseEditorAttributeError(PoseEditorException, AttributeError):
    """
    Raised when there is an issue getting/setting an attribute
    """


class PoseBlenderPoseError(PoseEditorException):
    """
    Generic error for issues with poses
    """


class InvalidPose(PoseEditorException):
    """
    Generic error for incorrect poses
    """


class InvalidPoseIndex(PoseEditorException):
    """
    Raised when issues arise surrounding the poses index
    """
