from collections import defaultdict
from types import GeneratorType

import ftrack_api


class Comparison(object):
    """Abstract class for attribute comparisons."""

    Operators = defaultdict(dict)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '{}({!r})>'.format(self.__class__.__name__, self.value)

    def __str__(self):
        return self.value

    def __invert__(self):
        """Reverse the current query.

        Ideally the minimum amount of brackets should be used, but this
        is fairly complex to calculate as child items are automatically
        converted to strings. Under no circumstances should the meaning
        of the query change, so if in doubt, add the brackets.
        """
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

    def __contains__(self, value):
        """Disable the use of `x in obj`, since it can only return a boolean."""
        raise TypeError("'in' cannot be overloaded")

    def is_(self, *args, **kwargs):
        """Setup .is() as an alias to equals."""
        return self.__eq__(*args, **kwargs)

    def is_not(self, *args, **kwargs):
        """Setup .is_not() as an alias to not equals."""
        return self.__ne__(*args, **kwargs)

    @classmethod
    def register_operator(cls, operator, brackets):
        """Create a new operator such as "and"/"or".

        Parameters:
            operator (str): What to use as the joining string.
                "and" and "or" are examples.
            brackets (bool): If multiple values need to be parenthesized.
            parse (function): Parse *args and **kwargs to return a list.
        """
        def fn(*args, **kwargs):
            """Create a comparison object containing all the inputs."""
            args = (arg for arg in args if arg is not None)
            query_parts = list(cls.parser(*args, **kwargs))
            query = ' {} '.format(operator).join(map(str, query_parts))
            if brackets and len(query_parts) > 1:
                return cls('({})'.format(query))
            return cls(query)
        cls.Operators[cls][operator] = fn
        return fn

    @classmethod
    def operator(cls, operator):
        try:
            return cls.Operators[cls][operator]
        except KeyError:
            raise AttributeError('no operator named "{}"'.format(operator))

    def __and__(self, other):
        """Join two comparisons."""
        return self.operator('and')(self, other)

    def __rand__(self, other):
        """Join two comparisons."""
        return self.operator('and')(other, self)

    def __or__(self, other):
        """Join two comparisons."""
        return self.operator('or')(self, other)

    def __ror__(self, other):
        """Join two comparisons."""
        return self.operator('or')(other, self)

    @classmethod
    def parser(cls, *args, **kwargs):
        """Convert multiple inputs into `Comparison` objects.
        Different types of arguments are allowed.

        args:
            Query: An unexecuted query object.
                This will be added as a subquery if supported.

            dict: Like kargs, but with relationships allowed.
                A relationship like "parent.name" is not compatible
                with **kwargs, so there needed to be an alternative
                way to set it without constructing a new Query object.

            Entity: FTrack API object.
                Every entity has a unique ID, so this can be safely
                relied upon when building the query.

            Anything else passed in will get converted to strings.

        kwargs:
            Search for attributes of an entity.
            `x=y` is the equivalent of `Comparison('x') == y`.

        Raises:
            TypeError: If entity is given with no keyword.

        Returns:
            List of `Comparison` objects or strings.
        """
        for arg in args:
            if isinstance(arg, dict):
                for key, value in arg.items():
                    yield cls(key) == value

            elif isinstance(arg, ftrack_api.entity.base.Entity):
                raise TypeError('keyword required for {}'.format(arg))

            elif isinstance(arg, GeneratorType) and len(args) == 1:
                for item in arg:
                    yield item

            # The object is likely a `Comparison` object at this point
            # If anything else is input, then assume it's valid syntax
            else:
                yield arg

        for key, value in kwargs.items():
            yield cls(key) == value
