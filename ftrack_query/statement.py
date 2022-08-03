# pylint: disable=consider-using-f-string
"""Adapt the query syntax to become more like SQLAlchemy.
The advantage of this is that it doesn't require a session to work.
These are designed to be passed to `FTrackQuery.execute`, and it won't
auto commit any changes.

See `select`/`create`/`update`/`delete` functions for the syntax.

Example:
    >>> stmt = delete('Task').where(entity.parent.name == 'Shot 1').limit(2)
    >>> session.execute(stmt)
    2
    >>> session.commit()
"""

__all__ = ['select', 'create', 'update', 'delete']

from types import GeneratorType

from ftrack_api.query import QueryResult

from .abstract import AbstractStatement
from .query import Query, Comparison
from .utils import clone_instance, copy_doc


class Select(AbstractStatement, Query):
    """Select entities."""

    def __str__(self):
        """Show a preview of what the statement is."""
        query = super(Select, self).__str__()
        if query.startswith('select '):
            return query
        return 'select from ' + query

    def execute(self, session=None):
        """Execute the select statement."""
        if session is None:
            session = self._session
        return session.query(self.as_str())

    def __iter__(self):
        """Iterate through the results."""
        return self.execute().__iter__()

    @copy_doc(QueryResult.one)
    def one(self):
        return self.execute().one()

    @copy_doc(QueryResult.first)
    def first(self):
        return self.execute().first()

    @copy_doc(QueryResult.all)
    def all(self):
        return self.execute().all()


class Create(AbstractStatement):
    """Create entities.

    Since this works a bit differently to Query, a few methods have
    been replicated instead of inheriting everything.
    """

    def __init__(self, entity):
        self._entity = entity
        self._values = {}
        self._session = None

    def __str__(self):
        """Show a preview of what the statement is."""
        return 'create {}({})'.format(
            self._entity,
            ', '.join('{}={!r}'.format(key, value) for key, value in self._values.items()),
        )

    def copy(self):
        """Create a new copy of the class."""
        # pylint: disable=protected-access
        new = type(self)(entity=self._entity)
        new._values = self._values
        new._session = self._session
        return new

    @clone_instance
    def values(self, **kwargs):
        """Set creation values."""
        for k, v in kwargs.items():
            if isinstance(v, GeneratorType):
                kwargs[k] = list(v)
        self._values.update(kwargs)
        return self

    @clone_instance
    def with_session(self, session):
        """Attach a new session to the query."""
        self._session = session
        return self

    def execute(self, session=None):
        """Execute the update statement.
        This does not commit changes.
        """
        if session is None:
            session = self._session
        return session.create(self._entity, self._values)


class Update(AbstractStatement, Query):
    """Update entities."""

    def __init__(self, *args, **kwargs):
        self._values = {}
        super(Update, self).__init__(*args, **kwargs)

    def populate(self, *args, **kwargs):
        """Disable projections."""
        raise AttributeError('projections not supported')

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
        if session is None:
            session = self._session

        count = 0
        with session.auto_populating(False):
            for entity in session.query(self.as_str()):
                for key, value in self._values.items():
                    entity[key] = value
                count += 1
        return count


class Delete(AbstractStatement, Query):
    """Delete entities."""

    def __init__(self, *args, **kwargs):
        self._remove_components = False
        super(Delete, self).__init__(*args, **kwargs)

    def __str__(self):
        """Show a preview of what the statement is."""
        return 'delete ' + super(Delete, self).__str__()

    def populate(self, *args, **kwargs):
        """Disable projections."""
        raise AttributeError('projections not supported')

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

    def copy(self):
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        new = super(Delete, self).copy()
        new._remove_components = self._remove_components
        return new

    def execute(self, session=None):
        """Execute the select statement."""
        if session is None:
            session = self._session

        count = 0

        # Preload options if needed
        if self._remove_components:
            query = super(Delete, self).populate('component_locations.location').as_str()
        else:
            query = self.as_str()

        # Delete each matching entity
        with session.auto_populating(False):
            for entity in session.query(query):

                # Remove components from locations
                if self._remove_components:
                    for component_location in entity['component_locations']:
                        component_location['location'].remove_component(entity)

                session.delete(entity)
                count += 1

        return count


def select(*items):
    """Generate a select statement.

    Returns:
        QueryResult object.

    Example:
        >>> stmt = select('Task.children').where(name='Test').order_by('id desc').limit(1)
        >>> str(stmt)
        'select parent, children from Task where x is 5 order by id descending limit 1'

        >>> session.execute(stmt).one()
        <Task>
    """
    entity_type = None
    populate = []
    for item in items:
        split = item.split('.', 1)
        if entity_type is None:
            entity_type = split[0]
        elif entity_type != split[0]:
            raise ValueError('selecting multiple base types is not supported')
        populate.extend(split[1:])

    return Select(None, entity_type).populate(*populate)


def create(entity_type):
    """Generate a create statement.

    Returns:
        Created entity.

    Example:
        >>> stmt = create('Task').values(name='Test', parent_id=123)
        >>> session.execute(stmt)
        <Task>
    """
    return Create(entity_type)


def update(entity_type):
    """Generate an update statement.

    Returns:
        Number of rows updated.

    Example:
        >>> stmt = update('Task').where(name='Test').order_by('id desc').limit(1)
        >>> session.execute(stmt)
        1
    """
    return Update(None, entity_type)


def delete(entity_type):
    """Generate a delete statement.

    Returns:
        Number of rows deleted.

    Example:
        >>> stmt = delete('Task').where(name='Test').order_by('id desc').limit(1)
        >>> session.execute(stmt)
        1
    """
    return Delete(None, entity_type)


def attr(item):
    """Easily access comparisons.

    Example:
        >>> attr('parent.version') > 0
    """
    return Comparison(item)
