# Copyright Epic Games, Inc. All Rights Reserved.
"""
Common class definitions that are used from rest of application.
"""


class MHViewerException(Exception):
    """
    Base MHViever exception that all other exceptions inherit from.
    """

    pass


class DNAReaderException(MHViewerException):
    """
    DNA reader exception.
    """

    pass


class MayaException(MHViewerException):
    """
    Maya context exception.
    """

    pass
