"""Python wrapper over the FTrack event syntax.
It's different to the standard query syntax, so it's been split into a
separate file.

Recommended Usage:
    with FTrackAPI() as session:
        session.event_hub.subscribe(
            str(event.and_(
                event.topic('ftrack.update'),
                event.data.user.name!=getuser(),
            ))
        )
        session.event_hub.wait()
"""

from .base import *


class Comparison(BaseComparison):
    @parse_operators
    def __eq__(self, value, base):
        return self.__class__('{}={}'.format(base, value))

    @parse_operators
    def __ne__(self, value, base):
        return self.__class__('{}!={}'.format(base, value))

    @parse_operators
    def __gt__(self, value, base):
        return self.__class__('{}>{}'.format(base, value))

    @parse_operators
    def __ge__(self, value, base):
        return self.__class__('{}>={}'.format(base, value))

    @parse_operators
    def __lt__(self, value, base):
        return self.__class__('{}<{}'.format(base, value))

    @parse_operators
    def __le__(self, value, base):
        return self.__class__('{}<={}'.format(base, value))


class Event(object):
    """Create a class to mimic the module.
    This allows for both __getattr__ and imports.
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

    def __getattr__(self, attr):
        """Get an event attribute to use for comparisons.
        Example: event.<attr>
        """
        return Comparison(attr)


and_ = Join('and', brackets=False, compare=Comparison)

or_ = Join('or', brackets=True, compare=Comparison)

event = Event()
