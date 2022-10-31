class UnboundSessionError(Exception):
    """Raise an error if attempting to execute a statement with no session."""

    def __init__(self):
        msg = 'statement has no session bound to it'
        super(UnboundSessionError, self).__init__(msg)
