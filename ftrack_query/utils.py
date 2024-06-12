# pylint: disable=consider-using-f-string, useless-object-inheritance
"""General purpose functions."""

from functools import wraps

import ftrack_api  # type: ignore

from .type_hints import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, Iterator
    from .query import SessionInstance


class NotSet(object):  # pylint: disable=too-few-public-methods
    """Create a sentinel object for when a value isn't given.

    This is similar to `ftrack_api.symbol.NOT_SET` but works with type
    checking.
    """


NOT_SET = NotSet()


def clone_instance(func):
    # type: (Callable) -> Callable
    """To avoid modifying the current instance, create a new one.
    Requires the class to have a `copy` method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # type: (SessionInstance, *Any, **Any) -> Any
        return func(self.copy(), *args, **kwargs)
    return wrapper


def dict_to_str(dct):
    # type: (Dict[Any, Any]) -> str
    """Convert a dict to a string."""
    def convert(dct):
        # type: (Dict[str, Any]) -> Iterator[str]
        for key, value in dct.items():
            if isinstance(value, ftrack_api.entity.base.Entity):
                value = str(value)
            else:
                value = repr(value)
            yield '{}={}'.format(key, value)
    return ', '.join(convert(dct))


def convert_output_value(value):
    # type: (Any) -> str
    """Convert the output value to something that FTrack understands."""
    if value is None:
        return 'none'
    if isinstance(value, (float, int)):
        return str(value)
    if isinstance(value, ftrack_api.entity.base.Entity):
        return value['id']
    return '"' + str(value).replace('"', r'\"') + '"'


def copy_doc(from_fn):
    # type: (Callable) -> Callable
    """Copy a docstring from one function to another."""
    def decorator(to_fn):
        # type: (Callable) -> Callable
        to_fn.__doc__ = from_fn.__doc__
        return to_fn
    return decorator
