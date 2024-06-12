# pylint: disable=consider-using-f-string
"""Simple wrapper over the FTrack event API.

Example:
    >>> from ftrack_query.event import attr, and_, or_
    >>> session.event_hub.subscribe(str(
    ...     and_(
    ...         attr('topic') == 'ftrack.update',
    ...         attr('data.user.name') != getuser(),
    ...     )
    ... ))
    >>> session.event_hub.wait()
"""

__all__ = ['and_', 'or_', 'not_']

from . import abstract
from .type_hints import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class Comparison(abstract.Comparison):
    """Comparisons for the event syntax."""

    def __eq__(self, value):  # type: ignore
        # type: (Any) -> Comparison
        """If a value is exactly equal."""
        return type(self)('{}={}'.format(*self._get_value_base(value)))

    def __ne__(self, value):  # type: ignore
        # type: (Any) -> Comparison
        """If a value is not exactly equal."""
        return type(self)('{}!={}'.format(*self._get_value_base(value)))

    def __gt__(self, value):
        # type: (Any) -> Comparison
        """If a value is greater than."""
        return type(self)('{}>{}'.format(*self._get_value_base(value)))

    def __ge__(self, value):
        # type: (Any) -> Comparison
        """If a value is greater than or equal."""
        return type(self)('{}>={}'.format(*self._get_value_base(value)))

    def __lt__(self, value):
        # type: (Any) -> Comparison
        """If a value is less than."""
        return type(self)('{}<{}'.format(*self._get_value_base(value)))

    def __le__(self, value):
        # type: (Any) -> Comparison
        """If a value is less than or equal."""
        return type(self)('{}<={}'.format(*self._get_value_base(value)))


def attr(value):
    # type (str) -> Comparison
    """Shortcut to create a Comparison object."""
    return Comparison(value)


def not_(*args, **kwargs):
    # type: (*Any, **Any) -> Comparison
    """Reverse a comparison object."""
    return ~or_(*args, **kwargs)


and_ = Comparison.register_operator('and', brackets=False)

or_ = Comparison.register_operator('or', brackets=True)
