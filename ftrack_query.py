"""Python ORM over the SQL based FTrack syntax.
Inspiration was taken from SQLALchemy but it was simplified.
Querying and creating is supported, but extra functionality for
creation can be added if the need arises.
"""

__all__ = ['FTrackQuery', 'and_', 'or_']

import logging
import os
import ftrack_api
from functools import wraps


logger = logging.getLogger('ftrack-wrapper')


def clone_instance(func):
    """To avoid modifying the current instance, create a new one."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self.copy(), *args, **kwargs)
    return wrapper


def parse_value(func):
    """Construct a string from the inputs."""
    @wraps(func)
    def wrapper(self, value):
        # If an entity is passed in, use the ID
        if isinstance(value, ftrack_api.entity.base.Entity):
            return func(self, '"{}"'.format(value['id']), base=self.value+'.id')

        if value is None:
            value = 'none'
        else:
            value = '"{}"'.format(value)
        return func(self, value)
    return wrapper


class Criteria(object):
    """Handle parsing the arguments to construct the query critera."""
    def __init__(self, operator, brackets):
        self.operator = operator
        self.brackets = brackets

    def __call__(self, *args, **kwargs):
        query = []
        if kwargs:
            query.append(' {} '.format(self.operator).join('{} is "{}"'.format(k, v) for k, v in kwargs.items()))
            if args:
                query.append(self.operator)
        if args:
            query.append(' {} '.format(self.operator).join(map(str, args)))

        if self.brackets and len(args) + len(kwargs) > 1:
            return Comparison('('+' '.join(query)+')')
        return Comparison(' '.join(query))


and_ = Criteria('and', brackets=False)

or_ = Criteria('or', brackets=True)


class Comparison(object):
    """Deal with individual query comparisons."""
    def __init__(self, value):
        self.value = str(value)

    def __getattr__(self, attr):
        """Get subkeys of the entity keys.
        Example: session.Entity.key.<subkey>.<subkey>...
        """
        return Comparison(self.value+'.'+attr)

    def __str__(self):
        return self.value

    def __invert__(self):
        return self.__class__('not '+self.value)
    
    def __call__(self, value):
        """Cast a relation to a concrete type.

        Example:
            # With the following query, parent is limited to "Project" only:
            TypedContext.where(TypedContext.parent(Project).status=='hidden')
        """
        return self.__class__('{}[{}]'.format(self.value, value))

    @parse_value
    def __eq__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} is {}'.format(base, value))

    @parse_value
    def __ne__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} is_not {}'.format(base, value))

    @parse_value
    def __gt__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} > {}'.format(base, value))

    @parse_value
    def __ge__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} >= {}'.format(base, value))

    @parse_value
    def __lt__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} < {}'.format(base, value))

    @parse_value
    def __le__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} <= {}'.format(base, value))

    @parse_value
    def like(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} like {}'.format(base, value))

    @parse_value
    def not_like(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} not_like {}'.format(base, value))

    @parse_value
    def after(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} after {}'.format(base, value))

    @parse_value
    def before(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} before {}'.format(base, value))

    def has(self, *args, **kwargs):
        return self.__class__('{} has ({})'.format(self.value, and_(*args, **kwargs)))

    def any(self, *args, **kwargs):
        return self.__class__('{} any ({})'.format(self.value, and_(*args, **kwargs)))


class Query(object):
    """Base class for constructing a query."""
    _EntityKeyCache = {}
    def __init__(self, session, entity):
        self._session = session
        self._entity = entity
        self._where = []
        self._populate = []
        self._sort = []
        self._offset = 0
        self._limit = None

    def __len__(self):
        return len(self.all())

    def __getattr__(self, attr):
        """Get the main keys.
        Example: session.Entity.key
        """
        return Comparison(attr)

    def __str__(self):
        query = []
        if self._populate:
            query.append('select')
            query.append(', '.join(self._populate))
            query.append('from')
        query.append(self._entity)
        query.append(str(and_(*self._where)))
        if query[-1]:
            query.insert(-1, 'where')
        if self._sort:
            query.append('order by')
            sort = ('{}{}'.format(value, ('', ' descending')[descending]) for value, descending in self._sort)
            query.append(', '.join(sort))
        if self._offset:
            query += ['offset', str(self._offset)]
        if self._limit is not None:
            query += ['limit', str(self._limit)]
        return ' '.join(filter(bool, query))

    def __call__(self, *args, **kwargs):
        raise TypeError("'Query' object is not callable, perhaps you meant to use 'Query.where()'?")

    def __iter__(self):
        return self._session.query(str(self)).__iter__()

    @classmethod
    def new(cls, session, entity):
        """Create a new Query object."""
        if entity == 'Note':
            return QueryNote(session)
        if entity == 'User':
            return QueryUser(session)
        return Query(session, entity)

    def copy(self):
        cls = Query.new(session=self._session, entity=self._entity)
        cls._entity = self._entity
        cls._where = list(self._where)
        cls._populate = list(self._populate)
        cls._sort = list(self._sort)
        cls._offset = self._offset
        cls._limit = self._limit
        return cls

    def get(self, value):
        """Get an entity from the ID."""
        logger.debug('Get ({}): {}'.format(self._entity, value))
        return super(FTrackQuery, self._session).get(self._entity, value)

    def create(self, **kwargs):
        """Create a new entity."""
        return self._session.create(self._entity, kwargs)

    def ensure(self, **kwargs):
        """Ensure an entity.
        Will create if it doesn't exist.
        """
        return self._session.ensure(self._entity, kwargs)

    def one(self):
        return self._session.query(str(self)).one()

    def first(self):
        return self._session.query(str(self)).first()

    def all(self):
        return self._session.query(str(self)).all()

    def count(self):
        return len(self)

    def keys(self):
        if self._entity not in self._EntityKeyCache:
            self._EntityKeyCache[self._entity] = self.first().keys()
        return self._EntityKeyCache[self._entity]

    @clone_instance
    def where(self, *args, **kwargs):
        """Filter the result."""
        for arg in args:
            if isinstance(arg, dict):
                kwargs.update(arg)
            else:
                self._where.append(str(arg))
        for key, value in kwargs.items():
            self._where.append(Comparison(key)==value)
        return self

    @clone_instance
    def populate(self, *args):
        self._populate += map(str, args)
        return self
    select = populate

    @clone_instance
    def sort(self, value, desc=None, asc=None):
        if desc is not None and asc is not None:
            raise ValueError('sorting cannot be both descending and ascending')
        elif desc is None and asc is None:
            desc = False
        elif asc is not None:
            desc = not asc
        self._sort.append((value, desc))
        return self
    order = sort

    @clone_instance
    def offset(self, value):
        self._offset = value
        return self

    @clone_instance
    def limit(self, value):
        self._limit = value
        return self


class QueryNote(Query):
    def __init__(self, session):
        super(QueryNote, self).__init__(session, 'Note')

    def create(self, **kwargs):
        """Handle special cases when creating notes.

        Recipients:
            Can be a Group/User contained within a Recipient entity.
            For ease of use, a Recipient will be automatically created
            if another entity type is given.

        Category:
            According to the API code, categories will be deprecated,
            and NoteLabelLinks should be used instead. This deals with
            the conversion automatically.
        """
        try:
            recipients = list(kwargs.pop('recipients', []))
        except TypeError:
            recipients = []
        category = kwargs.pop('category', None)

        note = self._session.create(self._entity, kwargs)

        for recipient in recipients:
            if recipient.__class__.__name__ != 'Recipient':
                recipient = self._session.Recipient.create(note_id=note['id'], resource_id=recipient['id'])
            note['recipients'].append(recipient)
        if category:
            entity = self._session.NoteLabelLink.create(note_id=note['id'], label_id=category['id'])
            note['note_label_links'].append(entity)
        return note


class QueryUser(Query):
    def __init__(self, session):
        super(QueryUser, self).__init__(session, 'User')

    def ensure(self, **kwargs):
        return self._session.ensure(self._entity, kwargs, identifying_keys=['username'])


class FTrackQuery(ftrack_api.Session):
    exc = ftrack_api.exception
    symbol = ftrack_api.symbol
    Entity = ftrack_api.entity.base.Entity

    def __init__(self, server_url=None, api_key=None, api_user=None, debug=False, **kwargs):
        self.debug = debug
        try:
            super(FTrackQuery, self).__init__(server_url=server_url, api_key=api_key, api_user=api_user, **kwargs)
        except (TypeError, ftrack_api.exception.ServerError):
            if not self.debug:
                raise
        logger.debug('New session initialised.')

    def __getattr__(self, attr):
        """Get entity."""
        return Query.new(self, attr)
    
    def __exit__(self, *args):
        if not self.debug:
            return super(FTrackQuery, self).__exit__(*args)

    def get(self, id):
        logger.debug('Get (Context): '+id)
        return super(FTrackQuery, self).get('Context', id)

    def query(self, query):
        logger.debug('Query: '+query)
        return super(FTrackQuery, self).query(query)
