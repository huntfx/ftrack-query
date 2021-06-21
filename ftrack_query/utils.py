import logging
from functools import wraps

import ftrack_api

from .abstract import AbstractQuery


logger = logging.getLogger('ftrack-query')


def not_(comparison):
    """Reverse a comparison object."""
    return ~comparison


def clone_instance(func):
    """To avoid modifying the current instance, create a new one."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self.copy(), *args, **kwargs)
    return wrapper


def dict_to_str(dct):
    """Convert a dict to a string."""
    def convert(dct):
        for k, v in dct.items():
            if isinstance(v, ftrack_api.entity.base.Entity):
                v = str(v)
            else:
                v = repr(v)
            yield '{}={}'.format(k, v)
    return ', '.join(convert(dct))


def parse_operators(func):
    """Parse the value when an operator is used."""
    @wraps(func)
    def wrapper(self, value):
        # If the item is constructed query, assume it's a single object
        if isinstance(value, AbstractQuery):
            value = value.one()

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
        return value
    return '"' + str(value).replace('"', r'\"') + '"'


class Join(object):
    """Convert multiple arguments into a valid query.

    Parameters:
        operator (str): What to use as the joining string.
            "and" and "or" are examples.
        brackets (bool): If multiple values need to be parenthesized.
        parse (function): Parse *args and **kwargs to return a list.
        compare (function): Construct a comparison object to return.
    """

    __slots__ = ('operator', 'brackets', 'comparison')

    def __init__(self, operator, brackets, compare):
        self.operator = operator
        self.brackets = brackets
        self.comparison = compare

    def __call__(self, *args, **kwargs):
        """Create a comparison object containing all the inputs."""
        args = (arg for arg in args if arg is not None)
        query_parts = list(self.comparison.parser(*args, **kwargs))
        query = ' {} '.format(self.operator).join(map(str, query_parts))
        if self.brackets and len(query_parts) > 1:
            return self.comparison('({})'.format(query))
        return self.comparison(query)
