"""Custom exceptions."""

import ftrack_api


class Error(ftrack_api.exception.Error):
    """Base class for all FTrackQuery exceptions.
    Inherits the ftrack_api exception base class.
    """


class UnboundSessionError(Error):
    """Raise an error if attempting to execute a statement with no session."""

    def __init__(self):
        msg = 'statement has no session bound to it'
        super(UnboundSessionError, self).__init__(msg)
