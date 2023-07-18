# pylint: disable=consider-using-f-string
"""Wrapper over the FTrack API to make it more pythonic to use.
Supports the querying and creation of objects, and a way to build
event listeners.

It's designed to hide the SQL-like syntax in favour of an object
orientated approach. Inspiration was taken from SQLALchemy.
"""

__all__ = ['FTrackQuery', 'exception', 'and_', 'or_', 'not_',
           'select', 'create', 'update', 'delete', 'attr']

__version__ = '2.0.0'

import logging
import os

import ftrack_api

from . import exception, utils
from .query import Select, Create, Update, Delete
from .query import attr, and_, or_, not_
from .utils import copy_doc


def select(entity_type):
    """Generate a select statement.

    Returns:
        QueryResult object.

    Example:
        >>> stmt = select('Task').where(name='Test').populate('type_id', 'status.name').limit(2)
        >>> str(stmt)
        'select type_id, status.name from Task where x is 5 limit 2'

        >>> session.execute(stmt).one()
        <Task>
    """
    return Select(entity_type)


def create(entity_type):
    """Generate a create statement.

    Returns:
        >>> stmt = create('Task').values(name='Test', parent_id=123)
        >>> session.execute(stmt)
        <Task>
    """
    return Create(entity_type)


def update(entity_type):
    """Generate an update statement.

    Example:
        >>> stmt = update('Task').where(name='Test').order_by('id desc').limit(1)
        >>> session.execute(stmt)
        1
    """
    return Update(entity_type)


def delete(entity_type):
    """Generate a delete statement.

    Example:
        >>> stmt = delete('Task').where(name='Test').order_by('id desc').limit(1)
        >>> session.execute(stmt)
        1
    """
    return Delete(entity_type)


class FTrackQuery(ftrack_api.Session):
    # pylint: disable=arguments-differ
    """Expansion of the ftrack_api.Session class."""

    def __init__(self, page_size=None, logger=None, debug=False, **kwargs):
        """Attempt to initialise the connection.
        If the debug argument is set, the connection will be ignored.
        """
        self.debug = debug

        # Override page size
        if page_size is None:
            try:
                page_size = int(os.environ.get('FTRACK_API_PAGE_SIZE', 0)) or None
            except ValueError:
                pass
        self.page_size = page_size

        # Initialise session
        if not self.debug:
            super(FTrackQuery, self).__init__(**kwargs)

        # Setup logger
        elif logger is None:
            self.logger = logging.getLogger(
                ftrack_api.Session.__module__ + '.' + type(self).__name__
            )
        if logger is not None:
            self.logger = logger
        self.logger.info('New session initialised.')

    def close(self, *args, **kwargs):
        """Avoid error when closing session in debug mode."""
        if not self.debug:
            return super(FTrackQuery, self).close(*args, **kwargs)

    def query(self, query, page_size=None, **kwargs):
        """Query FTrack for data.
        This method override adds support for setting page size.
        """
        query = str(query)
        self.logger.info('Query: %s', query)

        # Set page size
        page_size = page_size or self.page_size
        if page_size:
            kwargs['page_size'] = page_size

        return super(FTrackQuery, self).query(query, **kwargs)

    @copy_doc(ftrack_api.Session.create)
    def create(self, entity, data, *args, **kwargs):
        """Create a new entity."""
        if not kwargs.get('reconstructing', False):
            self.logger.info('Create: %s(%s)', entity, utils.dict_to_str(data))
        return super(FTrackQuery, self).create(entity, data, *args, **kwargs)

    @copy_doc(ftrack_api.Session.delete)
    def delete(self, entity, *args, **kwargs):
        """Delete an entity."""
        self.logger.info('Delete: %r', entity)
        return super(FTrackQuery, self).delete(entity, *args, **kwargs)

    @copy_doc(ftrack_api.Session.commit)
    def commit(self, *args, **kwargs):
        """Commit changes."""
        self.logger.info('Changes saved.')
        return super(FTrackQuery, self).commit(*args, **kwargs)

    @copy_doc(ftrack_api.Session.rollback)
    def rollback(self, *args, **kwargs):
        """Rollback changes."""
        self.logger.info('Changes discarded.')
        return super(FTrackQuery, self).rollback(*args, **kwargs)

    @copy_doc(ftrack_api.Session.populate)
    def populate(self, entities, projections):
        """Populate query with new values."""
        if isinstance(projections, (list, tuple, set)):
            projections = ','.join(map(str, projections))
        return super(FTrackQuery, self).populate(entities, projections)

    def execute(self, stmt):
        """Execute a statement.

        Returns:
            QueryResult object if a select statement.
            Created entity if a create statement.
            Number of entities updated if an update statement.
            Number of entities deleted if a delete statement.
        """
        return stmt.options(session=self).execute()

    @copy_doc(select)
    def select(self, *items):
        """Generate a select statement with the session attached."""
        return select(*items).options(session=self, page_size=self.page_size)
