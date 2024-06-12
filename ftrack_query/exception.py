# pylint: disable=super-with-arguments
"""Custom exceptions."""

import ftrack_api  # type: ignore


class Error(ftrack_api.exception.Error):
    """Base class for all FTrackQuery exceptions.
    Inherits the ftrack_api exception base class.
    """


class UnboundSessionError(Error):
    """Raise an error if attempting to execute a statement with no session."""

    def __init__(self):
        # type: () -> None
        super(UnboundSessionError, self).__init__('statement has no session bound to it')
