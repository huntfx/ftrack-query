"""Simple wrapper over the FTrack event API.

Example:
    >>> from ftrack_query import event
    >>> session.event_hub.subscribe(str(
    ...     event.and_(
    ...         event.topic('ftrack.update'),
    ...         event.data.user.name!=getuser(),
    ...     )
    ... ))
    >>> session.event_hub.wait()
"""

__all__ = ['event', 'and_', 'or_', 'not_']

from . import abstract
from .utils import parse_operators


class Comparison(abstract.Comparison):
    # pylint: disable=unexpected-special-method-signature
    """Comparisons for the event syntax."""

    @parse_operators
    def __eq__(self, value, base):
        """If a value is exactly equal."""
        return self.__class__('{}={}'.format(base, value))

    @parse_operators
    def __ne__(self, value, base):
        """If a value is not exactly equal."""
        return self.__class__('{}!={}'.format(base, value))

    @parse_operators
    def __gt__(self, value, base):
        """If a value is greater than."""
        return self.__class__('{}>{}'.format(base, value))

    @parse_operators
    def __ge__(self, value, base):
        """If a value is greater than or equal."""
        return self.__class__('{}>={}'.format(base, value))

    @parse_operators
    def __lt__(self, value, base):
        """If a value is less than."""
        return self.__class__('{}<{}'.format(base, value))

    @parse_operators
    def __le__(self, value, base):
        """If a value is less than or equal."""
        return self.__class__('{}<={}'.format(base, value))


def not_(*args, **kwargs):
    """Reverse a comparison object."""
    return ~or_(*args, **kwargs)


and_ = Comparison.register_operator('and', brackets=False)

or_ = Comparison.register_operator('or', brackets=True)

attr = Comparison
