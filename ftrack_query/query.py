# pylint: disable=consider-using-f-string, useless-object-inheritance, super-with-arguments
"""Base query syntax.
The classes in this file allow construction of a string to pass to the
`ftrack_api.Session.query` method.

Examples:
    >>> from ftrack_query import attr, create, select
    >>> project = session.select('Project').where(name='Test Project').one()

    >>> stmt = (
    ...     select('Shot')
    ...     .where(
    ...         ~attr('children').any(attr('name').like('%Animation%')),
    ...         name='Shot 1',
    ...     )
    ...     .order_by(attr('created_at').desc())
    ...     .limit(5)
    ... )
    >>> tasks = session.execute(query).all()

    >>> rows_updated = session.execute(
    ...     update('Task')
    ...     .where(name='Old Task Name')
    ...     .values(name='New Task Name')
    ... )

    >>> rows_deleted = session.execute(
    ...     delete('Task').where(
    ...         name='Old Task Name',
    ...     )
    ... )
"""

from types import GeneratorType

import ftrack_api  # type: ignore

from . import abstract
from .exception import UnboundSessionError
from .type_hints import TYPE_CHECKING
from .utils import NotSet, NOT_SET, clone_instance, convert_output_value, dict_to_str

if TYPE_CHECKING:
    from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
    from . import FTrackQuery


class Comparison(abstract.Comparison):
    """Comparisons for the query syntax."""

    def descending(self):
        # type: () -> str
        """Use the current attribute as part of a descending sort."""
        return '{} descending'.format(self.value)
    desc = descending

    def ascending(self):
        # type: () -> str
        """Use the current attribute as part of an ascending sort."""
        return '{} ascending'.format(self.value)
    asc = ascending

    def __contains__(self, value):
        # type: (Any) -> None
        """Provide an alternative suggestion when using `x in obj`."""
        raise TypeError("'in' cannot be overloaded, use {!r} instead".format(
            str(type(self)('{} like {}'.format(*self._get_value_base(value)))),
        ))

    def __eq__(self, value):  # type: ignore
        # type: (Any) -> Comparison
        """If a value is exactly equal."""
        return type(self)('{} is {}'.format(*self._get_value_base(value)))

    def __ne__(self, value):  # type: ignore
        # type: (Any) -> Comparison
        """If a value is not exactly equal."""
        return type(self)('{} is_not {}'.format(*self._get_value_base(value)))

    def __gt__(self, value):
        # type: (Any) -> Comparison
        """If a value is greater than."""
        return type(self)('{} > {}'.format(*self._get_value_base(value)))

    def __ge__(self, value):
        # type: (Any) -> Comparison
        """If a value is greater than or equal."""
        return type(self)('{} >= {}'.format(*self._get_value_base(value)))

    def __lt__(self, value):
        # type: (Any) -> Comparison
        """If a value is less than."""
        return type(self)('{} < {}'.format(*self._get_value_base(value)))

    def __le__(self, value):
        # type: (Any) -> Comparison
        """If a value is less than or equal."""
        return type(self)('{} <= {}'.format(*self._get_value_base(value)))

    def like(self, value):
        # type: (str) -> Comparison
        """If a value matches a pattern.
        The percent symbol (%) is used as a wildcard.
        """
        return type(self)('{} like {}'.format(*self._get_value_base(value)))

    def not_like(self, value):
        # type: (str) -> Comparison
        """If a value does not match a pattern.
        The percent symbol (%) sign is used as a wildcard.
        """
        return type(self)('{} not_like {}'.format(*self._get_value_base(value)))

    def after(self, value):
        # type: (Any) -> Comparison
        """If a date is after."""
        return type(self)('{} after {}'.format(*self._get_value_base(value)))

    def before(self, value):
        # type: (Any) -> Comparison
        """If a date is before."""
        return type(self)('{} before {}'.format(*self._get_value_base(value)))

    def has(self, *args, **kwargs):
        # type: (*Any, **Any) -> Comparison
        """Test a scalar relationship for values."""
        return type(self)('{} has ({})'.format(self.value, and_(*args, **kwargs)))

    def any(self, *args, **kwargs):
        # type: (*Any, **Any) -> Comparison
        """Test a collection relationship for values."""
        return type(self)('{} any ({})'.format(self.value, and_(*args, **kwargs)))

    def _prepare_in_subquery(self, values=None):
        # type: (Any) -> Tuple[str, str]
        """Prepare the subquery text for "in" or "not_in".
        This supports both subqueries (x in (select y from z)), and
        multiple items (x in ("y", "z")).
        Since quotation marks are important in the final query, an
        attempt is made to guess if the input is a subquery or a list
        of possible values.
        """
        # Unpack generators
        if values and isinstance(values, GeneratorType):
            values = list(values)

        if not values:
            return '', convert_output_value('')

        # Args were given as a built query
        # If a single query, then a subquery will work as long as a select is done
        if isinstance(values, Select):
            return '', str(values.subquery())

        # Allow subqueries to be manually written
        if isinstance(values, (str, type(u''))):
            return '', values

        # Handle FTrack entity instances
        ftrack_entities = [isinstance(value, ftrack_api.entity.base.Entity) for value in values]
        if all(ftrack_entities):
            return '.id', ', '.join(convert_output_value(entity['id']) for entity in values)
        if any(ftrack_entities):
            raise ValueError('values cannot be a mix of types when entities are used')

        # Correctly format a list of arguments based on their type
        return '', ', '.join(map(convert_output_value, values))

    def in_(self, values=None):
        # type: (Any) -> Comparison
        """One of these values.
        See _prepare_in_subquery() for implementation details.
        """
        suffix, subquery = self._prepare_in_subquery(values)
        return type(self)('{}{} in ({})'.format(self.value, suffix, subquery))

    def not_in(self, values=None):
        # type: (Any) -> Comparison
        """Not one of these values.
        See _prepare_in_subquery() for implementation details.
        """
        suffix, subquery = self._prepare_in_subquery(values)
        return type(self)('{}{} not_in ({})'.format(self.value, suffix, subquery))

    def startswith(self, value):
        # type: (str) -> Comparison
        """If a value starts with this."""
        return self.like(value.replace('%', '\\%') + '%')

    def endswith(self, value):
        # type: (str) -> Comparison
        """If a value ends with this."""
        return self.like('%' + value.replace('%', '\\%'))

    def contains(self, value):
        # type: (str) -> Comparison
        """If a value contains this."""
        return self.like('%' + value.replace('%', '\\%') + '%')


class SessionInstance(object):
    """Base class to hold the session and entity."""

    def __init__(self, entity_type):
        # type: (str) -> None
        self._entity = entity_type
        self._session = None  # type: Optional[FTrackQuery]

    def copy(self):
        # type: () -> SessionInstance
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = type(self)(entity_type=self._entity)
        new._session = self._session
        return new

    @clone_instance
    def options(self, session=NOT_SET):
        # type: (Union[FTrackQuery, NotSet, None]) -> SessionInstance
        """Set new query options.

        Parameters:
            session: New session instance.
        """
        if not isinstance(session, NotSet):
            self._session = session
        return self

    def execute(self, session=None):
        # type: (Optional[FTrackQuery]) -> Any
        """Placeholder method."""

    def _get_session(self, session=None):
        # type: (Optional[FTrackQuery]) -> FTrackQuery
        """Return the session instance or raise an UnboundSessionError."""
        if session is not None:
            return session
        if self._session is not None:
            return self._session
        raise UnboundSessionError


class Select(SessionInstance):
    """Construct a select query.

    Example:
        >>> stmt = (
        ...     Select('Task')
        ...     .where(name='Test')
        ...     .limit(1)
        ...     .populate('parent', 'children')
        ...     .order_by('id desc')
        ... )
        >>> str(stmt)
        'select parent, children from Task where name is "Test" order by id descending limit 1'

        >>> session.execute(stmt).one()
        <Task>
    """

    def __init__(self, entity_type):
        super(Select, self).__init__(entity_type=entity_type)
        self._populate = []
        self._sort = []
        self._offset = 0
        self._limit = 0
        self._page_size = None
        self._where = []
        self._group_by = []

    def __len__(self):
        # type: () -> int
        """Get the number of results.
        This executes the query so should not be used lightly.
        """
        return len(self.all())

    def __bool__(self):
        # type: () -> bool
        return self._entity is not None
    __nonzero__ = __bool__

    def __str__(self):
        # type: () -> str
        """Generate a string from the query data."""
        query = []
        if self._populate:
            query.append('select')
            query.append(', '.join(self._populate))
            query.append('from')
        query.append(self._entity)
        query.append(str(and_(*self._where)))
        if query[-1]:
            query.insert(-1, 'where')
        if self._group_by:
            query += ['group by', ', '.join(self._group_by)]
        if self._sort:
            query.append('order by')
            sort = ('{}{}'.format(value, ('', ' descending')[descending])
                    for value, descending in self._sort)
            query.append(', '.join(sort))
        if self._offset:
            query += ['offset', str(self._offset)]
        if self._limit:
            query += ['limit', str(self._limit)]
        return ' '.join(filter(bool, query))

    def __iter__(self):
        # type: () -> Iterator[ftrack_api.entity.base.Entity]
        """Iterate through results without executing the full query."""
        return iter(self.execute())

    def copy(self):
        # type: () -> Select
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Select, self).copy()
        if TYPE_CHECKING:
            assert isinstance(new, Select)

        new._entity = self._entity
        new._where = list(self._where)
        new._populate = list(self._populate)
        new._group_by = list(self._group_by)
        new._sort = list(self._sort)
        new._offset = self._offset
        new._limit = self._limit
        new._page_size = self._page_size
        return new

    def execute(self, session=None):
        # type: (Optional[FTrackQuery]) -> ftrack_api.query.QueryResult
        """Execute the current query.

        Raises:
            UnboundSessionError: If the session hasn't been set.
        """
        session = self._get_session(session)

        # Special case for aggregated results
        if self._group_by:
            res = session.call([{'action': 'query', 'expression': str(self)}])
            return res[0]['data']

        return session.query(str(self), page_size=self._page_size)

    def one(self):
        # type: () -> ftrack_api.entity.base.Entity
        """Returns and expects a single query result.

        Raises:
            ftrack_api.exception.MultipleResultsFoundError:
                If more than one result was available.
            ftrack_api.exception.NoResultFoundError:
                If no results were available.
        """
        return self.execute().one()

    def first(self):
        # type: () -> Optional[ftrack_api.entity.base.Entity]
        """Returns the first available query result, or None.

        Raises:
            ValueError: If a limit has already been set.
        """
        return self.execute().first()

    def all(self):
        # type: () -> List[ftrack_api.entity.base.Entity]
        """Returns every query result."""
        return self.execute().all()

    @clone_instance
    def where(self, *args, **kwargs):
        # type: (*Any, **Any) -> Select
        """Filter the result."""
        self._where.append(and_(*args, **kwargs))
        return self

    @clone_instance
    def populate(self, *args):
        # type: (*Optional[str]) -> Select
        """Prefetch attributes as part of the query."""
        self._populate.extend(map(str, filter(bool, args)))
        return self

    @clone_instance
    def sort(self, sort=None):
        # type: (Optional[str]) -> Select
        """Sort the query results."""
        desc = False

        # Grab the sorting method from the string if provided
        if sort is not None:
            sort = str(sort)
            if ' ' in sort:
                sort, method = sort.split(' ')
                if method in ('desc', 'descending'):
                    desc = True
                elif method not in ('asc', 'ascending'):
                    raise NotImplementedError('unknown sorting method: {!r}'.format(method))

        if sort is None:
            self._sort = []
        else:
            self._sort.append((sort, desc))
        return self
    order = order_by = sort

    @clone_instance
    def group_by(self, *args):
        # type: (*Optional[str]) -> Select
        """Group the results when aggregating data.
        The following functions are supported: `sum`, `avg`, `min`,
        `max`, `count`.

        The `strict_api` parameter must be enabled on the session or
        the query will fail.
        https://ftrack-python-api.readthedocs.io/en/stable/example/group_by.html
        """
        self._group_by.extend(map(str, filter(bool, args)))
        return self

    @clone_instance
    def offset(self, value):
        # type: (int) -> Select
        """Offset the results when a limit is used."""
        self._offset = value
        return self

    @clone_instance
    def limit(self, value):
        # type: (int) -> Select
        """Limit the total number of results."""
        self._limit = value
        return self

    @clone_instance
    def __reversed__(self):
        # type: () -> Select
        """Reverse the order of results.
        This is designed to only work on previous sorts, so will not
        have any effect if no sorts have been performed. Any future
        sorts are not affected.
        """
        self._sort = [(attr, not order) for attr, order in self._sort]
        return self
    reverse = __reversed__

    @clone_instance
    def options(self, session=NOT_SET, page_size=NOT_SET):
        # type: (Union[FTrackQuery, NotSet, None], Union[int, NotSet, None]) -> SessionInstance
        """Set new query options.

        Parameters:
            session: See `SessionInstance.options`.
            page_size: Number of results to fetch at once.
        """
        if not isinstance(page_size, NotSet):
            self._page_size = page_size
        return super(Select, self).options(session=session)

    @clone_instance
    def subquery(self, attribute=None):
        # type: (Optional[str]) -> Select
        """Convert the query to a subquery.
        This is to ensure there's always a `select from` included in
        the statement.
        """
        if attribute is not None or not self._populate:
            self._populate[:] = [attribute or 'id']
        return self


class Create(SessionInstance):
    """Generate a create statement.

    Since this works a bit differently to Select, a few methods have
    been replicated instead of inheriting everything.

    Example:
        >>> stmt = Create('Task').values(name='Test', parent_id=123)
        >>> session.execute(stmt)
        <Task>
    """

    def __init__(self, entity_type):
        # type: (str) -> None
        self._values = {}  # type: Dict[str, Any]
        super(Create, self).__init__(entity_type)

    def __str__(self):
        # type: () -> str
        """Show a preview of what the statement is."""
        return 'create {}({})'.format(self._entity, dict_to_str(self._values))

    def copy(self):
        # type: () -> Create
        """Create a new copy of the class."""
        # pylint: disable=protected-access
        new = super(Create, self).copy()
        if TYPE_CHECKING:
            assert isinstance(new, Create)

        new._values = self._values.copy()
        return new

    @clone_instance
    def values(self, **kwargs):
        # type: (**Any) -> Create
        """Set creation values."""
        for key, value in kwargs.items():
            if isinstance(value, GeneratorType):
                kwargs[key] = list(value)
        self._values.update(kwargs)
        return self

    def execute(self, session=None):
        # type: (Optional[FTrackQuery]) -> ftrack_api.entity.base.Entity
        """Execute the update statement.
        This does not commit changes.
        """
        session = self._get_session(session)
        return session.create(self._entity, self._values)


class Update(Select):
    """Generate an update statement.

    Returns:
        Number of rows updated.

    Example:
        >>> stmt = update('Task').where(name='Test').order_by('id desc').limit(1)
        >>> session.execute(stmt)
        1
    """

    def __init__(self, entity_type):
        # type: (str) -> None
        self._values = {}  # type: Dict[str, Any]
        super(Update, self).__init__(entity_type=entity_type)

    def copy(self):
        # type: () -> Update
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Update, self).copy()
        if TYPE_CHECKING:
            assert isinstance(new, Update)

        new._values = self._values.copy()
        return new

    def populate(self, *args):
        """Disable projections."""
        raise AttributeError('projections not supported')

    def group_by(self, *args):
        """Disable group by."""
        raise AttributeError('group_by not supported')

    def __str__(self):
        # type: () -> str
        """Show a preview of what the statement is."""
        return 'update {} set ({})'.format(
            super(Update, self).__str__(),
            ', '.join('{}={!r}'.format(key, value) for key, value in self._values.items()),
        )

    @clone_instance
    def values(self, **kwargs):
        # type: (**Any) -> Update
        """Set new values."""
        for key, value in kwargs.items():
            if isinstance(value, GeneratorType):
                kwargs[key] = list(value)
        self._values.update(kwargs)
        return self

    def execute(self, session=None):
        # type: (Optional[FTrackQuery]) -> int
        """Execute the update statement.
        This does not commit changes.
        """
        count = 0
        session = self._get_session(session)
        with session.auto_populating(False):
            for entity in session.query(super(Update, self).__str__()):
                for key, value in self._values.items():
                    entity[key] = value
                count += 1
        return count


class Delete(Select):
    """Generate a delete statement.

    Returns:
        Number of rows deleted.

    Example:
        >>> stmt = delete('Task').where(name='Test').order_by('id desc').limit(1)
        >>> session.execute(stmt)
        1
    """

    def __init__(self, entity_type):
        # type: (str) -> None
        self._remove_components = False  # type: Optional[bool]
        super(Delete, self).__init__(entity_type=entity_type)

    def __str__(self):
        # type: () -> str
        """Show a preview of what the statement is."""
        return 'delete ' + super(Delete, self).__str__()

    def populate(self, *args):
        """Disable projections."""
        raise AttributeError('projections not supported')

    def group_by(self, *args):
        """Disable group by."""
        raise AttributeError('group_by not supported')

    @clone_instance
    def clean_components(self, remove=True):
        # type: (bool) -> Delete
        """If a Component entity, then choose to delete it from locations.

        Example:
            >>> delete('Component').where(id=123).clean_components()

        Warning:
            The process of removing components from locations is not a
            transaction. That means that even if the session is rolled
            back, the changes will persist.
        """
        self._remove_components = remove
        return self

    @clone_instance
    def options(self,
                session=NOT_SET,  # type: Optional[Union[FTrackQuery, NotSet]]
                page_size=NOT_SET,  # type: Optional[Union[int, NotSet]]
                remove_components=NOT_SET  # type: Optional[Union[bool, NotSet]]
                ):  # type: (...) -> SessionInstance
        """Set new query options.

        Parameters:
            session: See `Select.options`.
            page_size: See `Select.options`.
            remove_components: Remove components from locations.
                Warning: This is not a transaction, and any changes are
                permanent. Performing a rollback will not undo this.
        """
        if not isinstance(remove_components, NotSet):
            self._remove_components = remove_components
        return super(Delete, self).options(session=session, page_size=page_size)

    def copy(self):
        # type: () -> Delete
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Delete, self).copy()
        if TYPE_CHECKING:
            assert isinstance(new, Delete)

        new._remove_components = self._remove_components
        return new

    def execute(self, session=None):
        # type: (Optional[FTrackQuery]) -> int
        """Execute the select statement."""
        count = 0

        # Preload options if needed
        if self._remove_components:
            self = super(Delete, self).populate('component_locations.location')  # pylint: disable=self-cls-assignment

        # Delete each matching entity
        session = self._get_session(session)
        with session.auto_populating(False):
            for entity in session.query(super(Delete, self).__str__()):

                # Remove components from locations
                if self._remove_components:
                    for component_location in entity['component_locations']:
                        component_location['location'].remove_component(entity)

                session.delete(entity)
                count += 1

        return count


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
