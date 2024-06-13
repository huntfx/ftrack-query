# pylint: disable=consider-using-f-string, useless-object-inheritance
"""General purpose functions."""

import re
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


def _requires_extra_brackets(value):
    # type: (str) -> bool
    """Check if extra brackets are needed to contain sub brackets.
    For example "(a or b) and (y or z)" does need extra brackets,
    whereas "(a and b)" does not.
    """
    if value[0] != '(' or value[-1] != ')':
        return True
    value = re.sub(r'"[^"]*"', '', value)  # Remove quotes
    depth = 0
    for char in value[1:-1]:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth < 0:
                return True
    return False


def reverse_value(value):
    # type: (str) -> str
    """Reverse a string with the `not` keyword.

    Ideally the minimum amount of brackets should be used, but this is
    fairly complex to calculate. Under no circumstances should the
    meaning of the statement change, so if in doubt, add the brackets.

    Examples:
        >>> reverse('not x')
        'x'
        >>> reverse('not (x and not y)')
        'x and not y'
        >>> reverse('x')
        'not x'
        >>> reverse('not x')
        'x'
        >>> reverse('not (x)')
        'x'
        >>> reverse('x and y')
        'not (x and y)'
        >>> reverse('x and (y or z)')
        'not (x and (y or z))'
        >>> reverse('(a or b) and (y or z)')
        'not ((a or b) and (y or z))'
        >>> reverse('(x or y) and z')
        'not ((x or y) and z)'
        >>> reverse('not (a or b) and (y or z)')
        'not (not (a or b) and (y or z))'
        >>> reverse('not ((a or b) and (y or z))')
        '(a or b) and (y or z)'
        >>> reverse('((a or b) and (y or z))')
        'not ((a or b) and (y or z))'
        >>> reverse('("y and x()" and z)')
        'not ("y and x()" and z)'
        >>> reverse('(a and b')
        'not ((a and b)'
    """
    input_value = value = value.strip()
    is_reversed = value[:4] == 'not '
    if is_reversed:
        value = value[4:].lstrip()
    if not value:
        return ''

    if _requires_extra_brackets(value):
        if bool(re.search(r'\b(and|or)\b', value)):
            return 'not ({})'.format(input_value)
        if is_reversed:
            return value
    if is_reversed:
        return value[1:-1]
    return 'not {}'.format(value)
