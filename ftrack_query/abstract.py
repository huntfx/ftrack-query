# pylint: disable=consider-using-f-string, useless-object-inheritance
"""Base classes for both the query and event syntax."""

from collections import defaultdict
from types import GeneratorType

import ftrack_api  # type: ignore

from .type_hints import TYPE_CHECKING
from .utils import convert_output_value, reverse_value

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, Iterator, Tuple, Union


class Comparison(object):
    """Abstract class for attribute comparisons."""

    Operators = defaultdict(dict)  # type: Dict[type, Dict[str, Callable]]

    def __init__(self, value):
        # type: (str) -> None
        self.value = value

    def __repr__(self):
        # type: () -> str
        return '{}({!r})>'.format(type(self).__name__, self.value)

    def __str__(self):
        # type: () -> str
        return self.value

    def __invert__(self):
        # type: () -> Comparison
        """Reverse the current query."""
        return type(self)(reverse_value(self.value))

    def __contains__(self, value):
        """Disable the use of `x in obj`, since it can only return a boolean."""
        raise TypeError("'in' cannot be overloaded")

    def is_(self, value):
        # type: (Any) -> Comparison
        """Setup .is() as an alias to equals."""
        return self == value

    def is_not(self, value):
        # type: (Any) -> Comparison
        """Setup .is_not() as an alias to not equals."""
        return self != value

    @classmethod
    def register_operator(cls, name, brackets):
        # type: (str, bool) -> Callable
        """Create a new operator such as "and"/"or".
        This is specific to the calling class, so that an inherited
        class gets its own operators.

        Parameters:
            name: What to use as the joining string.
                "and" and "or" are examples.
            brackets: If multiple values need to be parenthesized.
        """
        def operator(*args, **kwargs):
            # type: (*Any, **Any) -> Comparison
            """Create a comparison object containing all the inputs."""
            query_parts = list(cls.parser(*(arg for arg in args if arg is not None), **kwargs))
            query = ' {} '.format(name).join(map(str, query_parts))
            if brackets and len(query_parts) > 1:
                return cls('({})'.format(query))
            return cls(query)

        cls.Operators[cls][name] = operator
        return operator

    @classmethod
    def operator(cls, operator):
        # type: (str) -> Callable
        """Get an existing operator."""
        try:
            return cls.Operators[cls][operator]
        except KeyError:
            raise AttributeError('no operator named "{}"'.format(operator))  # pylint: disable=raise-missing-from

    def __and__(self, other):
        # type: (Any) -> Comparison
        """Join two comparisons."""
        return self.operator('and')(self, other)

    def __rand__(self, other):
        # type: (Any) -> Comparison
        """Join two comparisons."""
        return self.operator('and')(other, self)

    def __or__(self, other):
        # type: (Any) -> Comparison
        """Join two comparisons."""
        return self.operator('or')(self, other)

    def __ror__(self, other):
        # type: (Any) -> Comparison
        """Join two comparisons."""
        return self.operator('or')(other, self)

    @classmethod
    def parser(cls, *args, **kwargs):
        # type: (*Any, **Any) -> Iterator[Union[Comparison, str]]
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

    def _get_value_base(self, value):
        # type: (Any) -> Tuple[str, str]
        """Use the input value to get the base and actual value required.

        For example with "a=b", then the base is "a" and value is "b".
        However if "project=<ProjectEntity>", then the base should be
        "project.id", and the value "<ProjectEntity>['id']".
        """
        base = self.value
        if isinstance(value, ftrack_api.entity.base.Entity):
            base += '.id'
        return base, convert_output_value(value)
