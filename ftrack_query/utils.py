# pylint: disable=consider-using-f-string
"""General purpose functions."""

from functools import wraps

import ftrack_api


def clone_instance(func):
    """To avoid modifying the current instance, create a new one.
    Requires the class to have a `copy` method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self.copy(), *args, **kwargs)
    return wrapper


def dict_to_str(dct):
    """Convert a dict to a string."""
    def convert(dct):
        for key, value in dct.items():
            if isinstance(value, ftrack_api.entity.base.Entity):
                value = str(value)
            else:
                value = repr(value)
            yield '{}={}'.format(key, value)
    return ', '.join(convert(dct))


def parse_operators(func):
    """Parse the value when an operator is used."""
    @wraps(func)
    def wrapper(self, value):
        # If the item is an FTrack entity, use the ID
        if isinstance(value, ftrack_api.entity.base.Entity):
            return func(self, convert_output_value(value['id']), base=self.value+'.id')

        return func(self, convert_output_value(value), base=self.value)
    return wrapper


def convert_output_value(value):
    """Convert the output value to something that FTrack understands."""
    if value is None:
        return 'none'
    elif isinstance(value, (float, int)):
        return str(value)
    return '"' + str(value).replace('"', r'\"') + '"'


def copy_doc(from_fn):
    """Copy a docstring from one function to another."""
    def decorator(to_fn):
        to_fn.__doc__ = from_fn.__doc__
        return to_fn
    return decorator
