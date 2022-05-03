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

from .query import Query
from .utils import clone_instance


class Statement(object):
    """Base class for statements to use for inheritance checks."""

    @property
    def raw_query(self):
        """Return the actual query string, since __str__ is overridden."""
        return super(Statement, self).__str__()


class Select(Statement, Query):
    """Select entities."""

    def __str__(self):
        """Show a preview of what the statement is."""
        query = super(Select, self).__str__()
        if query.startswith('select '):
            return query
        return 'select ' + query

    def execute(self, session):
        """Execute the select statement."""
        return session.query(self.raw_query)


class Create(Statement):
    """Create entities.

    Since this works a bit differently to Query, a few methods have
    been replicated instead of inheriting everything.
    """

    def __init__(self, entity):
        self._entity = entity
        self._values = {}

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
        return new

    @clone_instance
    def values(self, **kwargs):
        """Set creation values."""
        self._values.update(kwargs)
        return self

    def execute(self, session):
        """Execute the update statement.
        This does not commit changes.
        """
        return session.create(self._entity, self._values)


class Update(Statement, Query):
    """Update entities."""

    def __init__(self, *args, **kwargs):
        self._values = {}
        super(Update, self).__init__(*args, **kwargs)

    def populate(self, *args, **kwargs):
        """Disable projections."""
        raise ValueError('unable to use projections during updates')

    def __str__(self):
        """Show a preview of what the statement is."""
        return 'update ' + super(Update, self).__str__()

    @clone_instance
    def values(self, **kwargs):
        """Set new values."""
        self._values.update(kwargs)
        return self

    def execute(self, session):
        """Execute the update statement.
        This does not commit changes.
        """
        count = 0
        with session.auto_populating(False):
            for entity in session.query(self.raw_query):
                for key, value in self._values.items():
                    entity[key] = value
                count += 1
        return count


class Delete(Statement, Query):
    """Delete entities."""

    def __str__(self):
        """Show a preview of what the statement is."""
        return 'delete ' + super(Delete, self).__str__()

    def populate(self, *args, **kwargs):
        """Disable projections."""
        raise ValueError('unable to use projections during deletes')

    def execute(self, session):
        """Execute the select statement."""
        count = 0
        with session.auto_populating(False):
            for entity in session.query(self.raw_query):
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
        split = item.split('.')
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
