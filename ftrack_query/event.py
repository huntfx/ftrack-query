__all__ = ['event', 'and_', 'or_', 'not_']

from .abstract import AbstractComparison
from .utils import Join, parse_operators, not_


class Comparison(AbstractComparison):
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


class Event(object):
    """Create a class to mimic event.py.

    The purpose of this is to allow both both imports and getattr.

    # Importing from module
    >>> from ftrack_query.event import *
    >>> and_(event.a=='b', event.x=='y')

    # Importing module directly
    >>> from ftrack_query import event
    >>> event.and_(event.a=='b', event.x=='y')

    Example:
        >>> event = Event()
        >>> session.event_hub.subscribe(str(
        ...     event.and_(
        ...         event.topic('ftrack.update'),
        ...         event.data.user.name!=getuser(),
        ...     )
        ... ))
        >>> session.event_hub.wait()
    """

    @staticmethod
    def and_(*args, **kwargs):
        """Quick access to the and_ function."""
        return and_(*args, **kwargs)

    @staticmethod
    def or_(*args, **kwargs):
        """Quick access to the or_ function."""
        return or_(*args, **kwargs)

    @staticmethod
    def not_(*args, **kwargs):
        """Quick access to the not_ function."""
        return not_(*args, **kwargs)

    @staticmethod
    def __getattr__(attr):
        """Get an event attribute to use for comparisons.
        Example: event.<attr>
        """
        return Comparison(attr)


and_ = Join('and', brackets=False, compare=Comparison)

or_ = Join('or', brackets=True, compare=Comparison)

event = Event()
