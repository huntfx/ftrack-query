# pylint: disable=consider-using-f-string
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

__all__ = ['entity', 'and_', 'or_', 'not_']

from types import GeneratorType

import ftrack_api
from ftrack_api.symbol import NOT_SET

from . import abstract
from .exception import UnboundSessionError
from .utils import clone_instance, convert_output_value, parse_operators, dict_to_str

if str is not bytes: unicode = str


class Comparison(abstract.Comparison):
    # pylint: disable=unexpected-special-method-signature
    """Comparisons for the query syntax."""

    def descending(self):
        return '{} descending'.format(self.value)
    desc = descending

    def ascending(self):
        return '{} ascending'.format(self.value)
    asc = ascending

    @parse_operators
    def __contains__(self, value, base):
        """Provide an alternative suggestion when using `x in obj`."""
        raise TypeError("'in' cannot be overloaded, use {!r} instead".format(
            str(self.__class__('{} like {}'.format(base, value))),
        ))

    @parse_operators
    def __eq__(self, value, base):
        """If a value is exactly equal."""
        return self.__class__('{} is {}'.format(base, value))

    @parse_operators
    def __ne__(self, value, base):
        """If a value is not exactly equal."""
        return self.__class__('{} is_not {}'.format(base, value))

    @parse_operators
    def __gt__(self, value, base):
        """If a value is greater than."""
        return self.__class__('{} > {}'.format(base, value))

    @parse_operators
    def __ge__(self, value, base):
        """If a value is greater than or equal."""
        return self.__class__('{} >= {}'.format(base, value))

    @parse_operators
    def __lt__(self, value, base):
        """If a value is less than."""
        return self.__class__('{} < {}'.format(base, value))

    @parse_operators
    def __le__(self, value, base):
        """If a value is less than or equal."""
        return self.__class__('{} <= {}'.format(base, value))

    @parse_operators
    def like(self, value, base):
        """If a value matches a pattern.
        The percent symbol (%) is used as a wildcard.
        """
        return self.__class__('{} like {}'.format(base, value))

    @parse_operators
    def not_like(self, value, base):
        """If a value does not match a pattern.
        The percent symbol (%) sign is used as a wildcard.
        """
        return self.__class__('{} not_like {}'.format(base, value))

    @parse_operators
    def after(self, value, base):
        """If a date is after."""
        return self.__class__('{} after {}'.format(base, value))

    @parse_operators
    def before(self, value, base):
        """If a date is before."""
        return self.__class__('{} before {}'.format(base, value))

    def has(self, *args, **kwargs):
        """Test a scalar relationship for values."""
        return self.__class__('{} has ({})'.format(self.value, and_(*args, **kwargs)))

    def any(self, *args, **kwargs):
        """Test a collection relationship for values."""
        return self.__class__('{} any ({})'.format(self.value, and_(*args, **kwargs)))

    def _prepare_in_subquery(self, values=None):
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
        if isinstance(values, (str, unicode)):
            return '', values

        # Handle FTrack entity instances
        ftrack_entities = [isinstance(value, ftrack_api.entity.base.Entity) for value in values]
        if all(ftrack_entities):
            return '.id', ', '.join(convert_output_value(entity['id']) for entity in values)
        elif any(ftrack_entities):
            raise ValueError('values cannot be a mix of types when entities are used')

        # Correctly format a list of arguments based on their type
        return '', ', '.join(map(convert_output_value, values))

    def in_(self, values=None):
        """One of these values.
        See _prepare_in_subquery() for implementation details.
        """
        attr, subquery = self._prepare_in_subquery(values)
        return self.__class__('{}{} in ({})'.format(self.value, attr, subquery))

    def not_in(self, values=None):
        """Not one of these values.
        See _prepare_in_subquery() for implementation details.
        """
        attr, subquery = self._prepare_in_subquery(values)
        return self.__class__('{}{} not_in ({})'.format(self.value, attr, subquery))

    def startswith(self, value):
        """If a value starts with this."""
        return self.like(value.replace('%', '\\%') + '%')  # pylint: disable=no-value-for-parameter

    def endswith(self, value):
        """If a value ends with this."""
        return self.like('%' + value.replace('%', '\\%'))  # pylint: disable=no-value-for-parameter

    def contains(self, value):
        """If a value contains this."""
        return self.like('%' + value.replace('%', '\\%') + '%')  # pylint: disable=no-value-for-parameter


class SessionInstance(object):
    """Base class to hold the session and entity."""

    def __init__(self, entity_type):
        self._entity = entity_type
        self._session = None

    def copy(self):
        """Create a new copy of the class."""
        # pylint: disable=protected-access
        new = type(self)(entity_type=self._entity)
        new._session = self._session
        return new

    @clone_instance
    def options(self, session=NOT_SET):
        """Set new query options.

        Parameters:
            session (FTrackQuery): New session instance.
        """
        if session is not NOT_SET:
            self._session = session
        return self

    def _get_session(self, session=None, raise_=True):
        """Return the session instance or raise an UnboundSessionError."""
        if session is not None:
            return session
        if self._session is not None:
            return self._session
        if raise_:
            raise UnboundSessionError
        return None


class Select(SessionInstance):
    """Construct a select query.

    Example:
        >>> stmt = Select('Task').where(name='Test').limit(1).populate('parent', 'children').order_by('id desc')
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
        self._limit = None
        self._page_size = None
        self._where = []
        self._group_by = []

    def __len__(self):
        """Get the number of results.
        This executes the query so should not be used lightly.
        """
        return len(self.all())

    def __bool__(self):
        return self._entity is not None
    __nonzero__ = __bool__

    def __str__(self):
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
        if self._limit is not None:
            query += ['limit', str(self._limit)]
        return ' '.join(filter(bool, query))

    def __iter__(self):
        """Iterate through results without executing the full query."""
        return iter(self.execute())

    def copy(self):
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Select, self).copy()
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
        """Execute the current query.

        Raises:
            UnboundSessionError: If the session hasn't been set.
        """
        session = self._get_session(session)

        # Special case for aggregated results
        if self._group_by:
            res = session.call([dict(action='query', expression=str(self))])
            return res[0]['data']

        return session.query(str(self), page_size=self._page_size)

    def one(self):
        """Returns and expects a single query result.

        Raises:
            ftrack_api.exception.MultipleResultsFoundError:
                If more than one result was available.
            ftrack_api.exception.NoResultFoundError:
                If no results were available.
        """
        return self.execute().one()

    def first(self):
        """Returns the first available query result, or None.

        Raises:
            ValueError: If a limit has already been set.
        """
        return self.execute().first()

    def all(self):
        """Returns every query result."""
        return self.execute().all()

    @clone_instance
    def where(self, *args, **kwargs):
        """Filter the result."""
        self._where.append(and_(*args, **kwargs))
        return self

    @clone_instance
    def populate(self, *args):
        """Prefetch attributes as part of the query."""
        # Allow empty string or None without breaking
        if not args or (len(args) == 1 and not args[0]):
            return self
        self._populate.extend(map(str, args))
        return self

    @clone_instance
    def sort(self, attr=None):
        """Sort the query results."""
        desc = False

        # Grab the sorting method from the string if provided
        if attr is not None:
            attr = str(attr)
            if ' ' in attr:
                attr, method = attr.split(' ')
                if method in ('desc', 'descending'):
                    desc = True
                elif method not in ('asc', 'ascending'):
                    raise NotImplementedError('unknown sorting method: {!r}'.format(method))

        if attr is None:
            self._sort = []
        else:
            self._sort.append((attr, desc))
        return self
    order = order_by = sort

    @clone_instance
    def group_by(self, *args):
        """Group the results when aggregating data.
        The following functions are supported: `sum`, `avg`, `min`,
        `max`, `count`.

        The `strict_api` parameter must be enabled on the session or
        the query will fail.
        https://ftrack-python-api.readthedocs.io/en/stable/example/group_by.html
        """
        self._group_by.extend(args)
        return self

    @clone_instance
    def offset(self, value=None):
        """Offset the results when a limit is used."""
        self._offset = value
        return self

    @clone_instance
    def limit(self, value=None):
        """Limit the total number of results."""
        self._limit = value
        return self

    @clone_instance
    def __reversed__(self):
        """Reverse the order of results.
        This is designed to only work on previous sorts, so will not
        have any effect if no sorts have been performed. Any future
        sorts are not affected.
        """
        self._sort = [(attr, not order) for attr, order in self._sort]
        return self
    reverse = __reversed__

    @clone_instance
    def options(self, page_size=NOT_SET, **kwargs):
        """Set new query options.

        Parameters:
            page_size (int): Number of results to fetch at once.
        """
        if page_size is not NOT_SET:
            self._page_size = page_size
        return super(Select, self).options(**kwargs)

    @clone_instance
    def subquery(self, attribute=None):
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
        self._entity = entity_type
        self._values = {}

    def __str__(self):
        """Show a preview of what the statement is."""
        return 'create {}({})'.format(self._entity, dict_to_str(self._values))

    def copy(self):
        """Create a new copy of the class."""
        # pylint: disable=protected-access
        new = type(self)(entity_type=self._entity)
        new._values = self._values.copy()
        return new

    @clone_instance
    def values(self, **kwargs):
        """Set creation values."""
        for k, v in kwargs.items():
            if isinstance(v, GeneratorType):
                kwargs[k] = list(v)
        self._values.update(kwargs)
        return self

    def execute(self, session=None):
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
        self._values = {}
        super(Update, self).__init__(entity_type=entity_type)

    def copy(self):
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Update, self).copy()
        new._values = self._values.copy()
        return new

    def populate(self, *args):
        """Disable projections."""
        raise AttributeError('projections not supported')

    def group_by(self, *args):
        """Disable group by."""
        raise AttributeError('group_by not supported')

    def __str__(self):
        """Show a preview of what the statement is."""
        return 'update {} set ({})'.format(
            super(Update, self).__str__(),
            ', '.join('{}={!r}'.format(key, value) for key, value in self._values.items()),
        )

    @clone_instance
    def values(self, **kwargs):
        """Set new values."""
        for k, v in kwargs.items():
            if isinstance(v, GeneratorType):
                kwargs[k] = list(v)
        self._values.update(kwargs)
        return self

    def execute(self, session=None):
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
        self._remove_components = False
        super(Delete, self).__init__(entity_type=entity_type)

    def __str__(self):
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
    def options(self, remove_components=NOT_SET, **kwargs):
        """Set new query options.

        Parameters:
            remove_components (bool): Remove components from locations.
                Warning: This is not a transation, and any changes are
                permanent. Performing a rollback will not undo this.
        """
        if remove_components is not NOT_SET:
            self._remove_components = remove_components
        return super(Delete, self).options(**kwargs)

    def copy(self):
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Delete, self).copy()
        new._remove_components = self._remove_components
        return new

    def execute(self, session=None):
        """Execute the select statement."""
        count = 0

        # Preload options if needed
        if self._remove_components:
            self = super(Delete, self).populate('component_locations.location')

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


def not_(*args, **kwargs):
    """Reverse a comparison object."""
    return ~or_(*args, **kwargs)


and_ = Comparison.register_operator('and', brackets=False)

or_ = Comparison.register_operator('or', brackets=True)

attr = Comparison
