# pylint: disable=consider-using-f-string
"""Wrapper over the FTrack API to make it more pythonic to use.
Supports the querying and creation of objects, and a way to build
event listeners.

It's designed to hide the SQL-like syntax in favour of an object
orientated approach. Inspiration was taken from SQLALchemy.
"""

__all__ = ['FTrackQuery', 'entity', 'and_', 'or_', 'not_', 'event',
           'select', 'create', 'update', 'delete', 'attr']

__version__ = '1.8.0'

from functools import wraps

import ftrack_api

from . import utils
from .abstract import AbstractStatement
from .query import Query, entity, and_, or_, not_
from .event import event
from .statement import attr, select, insert, create, update, delete


def _copydoc(from_fn):
    """Copy a docstring from one function to another."""
    def decorator(to_fn):
        to_fn.__doc__ = from_fn.__doc__
        return to_fn
    return decorator


class FTrackQuery(ftrack_api.Session):
    # pylint: disable=arguments-differ
    """Expansion of the ftrack_api.Session class."""

    def __init__(self, **kwargs):
        """Attempt to initialise the connection.
        If the debug argument is set, the connection will be ignored.
        """
        self.debug = kwargs.pop('debug', False)
        self._logger = kwargs.pop('logger', utils.logger)
        self._logger.debug('Connecting...')
        if not self.debug:
            super(FTrackQuery, self).__init__(**kwargs)
        self._logger.debug('New session initialised.')

    def __getattribute__(self, attr):
        """Get an entity type if it exists.
        The standard AttributeError will be raised if not.
        """
        try:
            return super(FTrackQuery, self).__getattribute__(attr)
        except AttributeError:
            if self.debug or attr in super(FTrackQuery, self).__getattribute__('types'):
                return Query(self, attr)
            raise

    def close(self, *args, **kwargs):
        """Avoid error when closing session in debug mode."""
        if not self.debug:
            return super(FTrackQuery, self).close(*args, **kwargs)

    def get(self, value, _value=None, *args, **kwargs):  # pylint: disable=keyword-arg-before-vararg
        """Get any entity from its ID.
        The _value argument is for compatibility with ftrack_api.Session.
        """
        if _value is None:
            entity = 'Context'
        else:
            entity, value = value, _value
        self._logger.debug('Get: %s(%r)', entity, value)
        return super(FTrackQuery, self).get(entity, value, *args, **kwargs)

    def query(self, query, *args, **kwargs):
        """Create an FTrack query object from a string."""
        query = str(query)
        self._logger.debug('Query: %s', query)
        return super(FTrackQuery, self).query(query, *args, **kwargs)

    def create(self, entity, data, *args, **kwargs):
        """Create a new entity."""
        if not kwargs.get('reconstructing', False):
            self._logger.debug('Create: %s(%s)', entity, utils.dict_to_str(data))
        return super(FTrackQuery, self).create(entity, data, *args, **kwargs)

    def delete(self, entity, *args, **kwargs):
        """Delete an FTrack entity."""
        self._logger.debug('Delete: %r', entity)
        return super(FTrackQuery, self).delete(entity, *args, **kwargs)

    def where(self, *args, **kwargs):
        """Set entity type as TypedContext if none provided."""
        return self.TypedContext.where(*args, **kwargs)

    def commit(self, *args, **kwargs):
        """Commit changes."""
        self._logger.debug('Changes saved.')
        return super(FTrackQuery, self).commit(*args, **kwargs)

    def rollback(self, *args, **kwargs):
        """Rollback changes."""
        self._logger.debug('Changes discarded.')
        return super(FTrackQuery, self).rollback(*args, **kwargs)

    def populate(self, entities, projections):
        """Populate new values."""
        if isinstance(projections, (list, tuple, set)):
            projections = ','.join(map(str, projections))
        return super(FTrackQuery, self).populate(entities, projections)

    def execute(self, stmt):
        """Execute a statement."""
        if isinstance(stmt, AbstractStatement):
            return stmt.with_session(self).execute()
        raise NotImplementedError(type(stmt))

    @_copydoc(select)
    def select(self, *items):
        return select(*items).with_session(self)

    @_copydoc(insert)
    def insert(self, entity_type):
        return insert(entity_type).with_session(self)

    @_copydoc(update)
    def update(self, entity_type):
        return update(entity_type).with_session(self)

    @_copydoc(delete)
    def delete(self, entity_type):
        return delete(entity_type).with_session(self)
