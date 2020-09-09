"""Core functions to reuse."""

__all__ = [
    'logger', 'not_', 'clone_instance', 'dict_to_str', 'parse_operators',
    'convert_output_value', 'BaseQuery', 'BaseComparison', 'Join',
]

import logging
from functools import wraps

import ftrack_api


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
                v = v.__repr__()
            yield '{}={}'.format(k, v)
    return ', '.join(convert(dct))


def parse_operators(func):
    """Parse the value when an operator is used."""
    @wraps(func)
    def wrapper(self, value):
        # If an entity is passed in, use the ID
        if isinstance(value, ftrack_api.entity.base.Entity):
            return func(self, convert_output_value(value['id']), base=self.value+'.id')
        return func(self, convert_output_value(value), base=self.value)
    return wrapper


def convert_output_value(value):
    """Convert the output value to something that FTrack understands.
    As of right now, this is adding speech marks.
    """
    if value is None:
        return 'none'
    elif isinstance(value, (float, int)):
        return value
    return '"' + str(value).replace('"', r'\"') + '"'


class BaseQuery(object):
    """Empty base class to use for inheritance checks."""


class BaseComparison(object):
    """Deal with individual query comparisons."""

    def __init__(self, value):
        self.value = value

    def __getattr__(self, attr):
        """Get sub-attributes of the entity attributes.
        Example: session.Entity.attr.<subattr>.<subattr>...
        """
        return self.__class__(self.value+'.'+attr)

    def __repr__(self):
        return '{}({!r})>'.format(self.__class__.__name__, self.value)

    def __str__(self):
        return self.value

    def __invert__(self):
        if self.value[:4] == 'not ':
            return self.__class__(self.value[4:])

        # Figure out if brackets need to be added
        # If there are no connectors, then it's likely to be fine
        if ' and ' not in self.value and ' or ' not in self.value:
            return self.__class__('not '+self.value)

        # If there are brackets, then check the depth remains above 0,
        # otherwise ~and(or(), or()) will be wrong
        # TODO: Optimise with regex or something
        if self.value[0] == '(' and self.value[-1] == ')':
            depth = 0
            pause = False
            for c in self.value[1:-1]:
                if c == '(':
                    if not pause:
                        depth += 1
                elif c == ')':
                    if not pause:
                        depth -= 1
                elif c == '"':
                    pause = not pause
                if depth < 0:
                    return self.__class__('not ({})'.format(self.value))
            return self.__class__('not '+self.value)

        return self.__class__('not ({})'.format(self.value))

    def __call__(self, *args, **kwargs):
        return self.__eq__(*args, **kwargs)
        #raise TypeError("'{}' object is not callable".format(self.__class__.__name__))

    def is_(self, *args, **kwargs):
        return self.__eq__(*args, **kwargs)

    def is_not(self, *args, **kwargs):
        return self.__ne__(*args, **kwargs)

    @classmethod
    def parser(cls, *args, **kwargs):
        """Convert multiple inputs into Comparison objects.
        Different types of arguments are allowed.

        args:
            Query: An unexecuted query object.
                This is not recommended, but an attempt will be made
                to execute it for a single result.
                It will raise an exception if multiple or none are
                found.

            dict: Like kargs, but with relationships allowed.
                A relationship like "parent.name" is not compatible
                with **kwargs, so there needed to be an alternative
                way to set it without constructing a new Query object.

            Entity: FTrack API object.
                Every entity has a unique ID, so this can be safely
                relied upon when building the query.

            Anything else passed in will get converted to strings.
            The comparison class has been designed to evaluate when
            __str__ is called, but any custom class could be used.

        kwargs:
            Search for attributes of an entity.
            This is the recommended way to query if possible.
        """
        for arg in args:
            # The query has not been performed, attempt to execute
            # This shouldn't really be used, so don't catch any errors
            if isinstance(arg, BaseQuery):
                arg = arg.one()

            if isinstance(arg, dict):
                for key, value in arg.items():
                    yield cls(key)==value

            elif isinstance(arg, ftrack_api.entity.base.Entity):
                raise TypeError("keyword required for {}".format(arg))

            # The object is likely a comparison object, so convert to str
            # If an actual string is input, then assume it's valid syntax
            else:
                yield arg

        for key, value in kwargs.items():
            if isinstance(value, BaseQuery):
                value = value.one()
            yield cls(key)==value


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
        query_parts = list(self.comparison.parser(*args, **kwargs))
        query = ' {} '.format(self.operator).join(map(str, query_parts))
        if self.brackets and len(query_parts) > 1:
            return self.comparison('({})'.format(query))
        return self.comparison(query)
