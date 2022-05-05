import logging

import ftrack_api


logger = logging.getLogger('ftrack-query')


class AbstractQuery(object):
    """Class to use for inheritance checks."""


class AbstractComparison(object):
    """Class to generate query comparisons."""

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

    def __call__(self, *args, **kwargs):
        """Setup calls as aliases to equals.
        >>> entity.value('x') == (entity.value == 'x')

        The old error has been left commented out in case it needs to
        be re-added for certain cases in the future.
        """
        return self.__eq__(*args, **kwargs)
        # raise TypeError("'{}' object is not callable".format(self.__class__.__name__))

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
            if isinstance(arg, AbstractQuery):
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
            if isinstance(value, AbstractQuery):
                value = value.one()
            yield cls(key)==value


class AbstractStatement(object):
    """Class to use for inheritance checks."""
