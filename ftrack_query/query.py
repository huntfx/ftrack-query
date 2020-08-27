"""Python wrapper over the SQL based FTrack syntax.
Supports the querying and creation of objects.
"""

__all__ = ['FTrackQuery', 'entity', 'and_', 'or_', 'not_']


import ftrack_api

from .base import *  # pylint: disable=unused-wildcard-import


class Comparison(BaseComparison):
    # pylint: disable=unexpected-special-method-signature
    def __getitem__(self, value):
        """Cast a relation to a concrete type.
        One example would be TypedContext.parent(Project), where it
        will limit the TypedContext search to the direct children of
        projects.
        """
        return self.__class__('{}[{}]'.format(self.value, value))

    def __call__(self, *args, **kwargs):
        """Access special features based on the attribute name.
        For example, .desc can be used as a key normally, but .desc()
        will be used as a sort string.
        If no override exists, then the standard TypeError will be
        raised. *args and **kwargs are ignored to avoid a different
        TypeError complaining about the number of arguments.
        """
        try:
            value, attr = self.value.rsplit('.', 1)
        except ValueError:
            attr = self.value
        if attr == 'desc':
            return '{} descending'.format(value)
        elif attr == 'asc':
            return '{} ascending'.format(value)
        return super(Comparison, self).__call__(*args, **kwargs)

    @parse_operators
    def __eq__(self, value, base):
        return self.__class__('{} is {}'.format(base, value))

    @parse_operators
    def __ne__(self, value, base):
        return self.__class__('{} is_not {}'.format(base, value))

    @parse_operators
    def __gt__(self, value, base):
        return self.__class__('{} > {}'.format(base, value))

    @parse_operators
    def __ge__(self, value, base):
        return self.__class__('{} >= {}'.format(base, value))

    @parse_operators
    def __lt__(self, value, base):
        return self.__class__('{} < {}'.format(base, value))

    @parse_operators
    def __le__(self, value, base):
        return self.__class__('{} <= {}'.format(base, value))

    @parse_operators
    def like(self, value, base):
        return self.__class__('{} like {}'.format(base, value))

    @parse_operators
    def not_like(self, value, base):
        return self.__class__('{} not_like {}'.format(base, value))

    @parse_operators
    def after(self, value, base):
        return self.__class__('{} after {}'.format(base, value))

    @parse_operators
    def before(self, value, base):
        return self.__class__('{} before {}'.format(base, value))

    def has(self, *args, **kwargs):
        where = Comparison.parser(*args, **kwargs)
        return self.__class__('{} has ({})'.format(self.value, and_(*where)))

    def any(self, *args, **kwargs):
        where = Comparison.parser(*args, **kwargs)
        return self.__class__('{} any ({})'.format(self.value, and_(*where)))

    def in_(self, *args):
        """The in operator works slightly differently to the others.
        It supports subqueries (x in (select y from z)), and multiple
        items (x in ("y", "z")).
        Since quotation marks are important, an attempt is made to
        guess if the input is a subquery or a list of possible values.
        """
        # Args were given as entities
        if isinstance(args[0], ftrack_api.entity.base.Entity):
            return self.__class__('{}.id in ({})'.format(
                self.value, ', '.join(convert_output_value(entity['id']) for entity in args)
            ))

        # Args were given as a list of strings
        if len(args) == 1 and args[0].startswith('select ') and ' from ' in args[0]:
            subquery = args[0]
        else:
            subquery = ', '.join(map(convert_output_value, args))
        return self.__class__('{} in ({})'.format(self.value, subquery))

    def not_in(self, *args):
        return self.in_(*args).__invert__()


class Query(BaseQuery):
    """Base class for constructing a query."""
    _EntityKeyCache = {}

    # These keys are used where it's likely there's a unique value for each entity
    _PrimaryKeys = {
        'Disk': 'name',
        'Location': 'name',
        'NoteLabel': 'name',
        'Priority': 'name',
        'Project': 'name',
        'ProjectSchema': 'name',
        'SecurityRole': 'name',
        'Setting': 'name',
        'State': 'name',
        'Status': 'name',
        'Type': 'name',
        'User': 'username',
    }

    def __init__(self, session, entity):
        self._session = session
        self._entity = entity
        self._where = []
        self._populate = []
        self._sort = []
        self._offset = 0
        self._limit = None

    def __len__(self):
        """Get the number of results.
        This executes the query so should not be used lightly.
        """
        return len(self.all())
    length = __len__

    def __getattr__(self, attr):
        """Get an entity attribute.
        Example: session.Entity.<attr>
        """
        return Comparison(attr)

    def __str__(self):
        """Evaluate the query data and convert to a string."""
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
            sort = ('{}{}'.format(value, ('', ' descending')[descending])
                    for value, descending in self._sort)
            query.append(', '.join(sort))
        if self._offset:
            query += ['offset', str(self._offset)]
        if self._limit is not None:
            query += ['limit', str(self._limit)]
        return ' '.join(filter(bool, query))

    def __call__(self, *args, **kwargs):
        """Custom error message if attempting to call.
        This is due to it being quite a common mistake.

        In rare cases, it can be valid to pass in a single argument,
        such as User('username'). The inspiration for this was taken
        from the old API.
        """
        if self._entity in self._PrimaryKeys and len(args) == 1 and not kwargs:
            try:
                return self.where(**{self._PrimaryKeys[self._entity]: args[0]}).one()
            except ftrack_api.exception.NoResultFoundError:
                return None

        raise TypeError("'Query' object is not callable, "
                        "perhaps you meant to use 'Query.where()'?")

    def __iter__(self):
        """Iterate through results without executing the full query."""
        return self._session.query(str(self)).__iter__()

    @clone_instance
    def __or__(self, entity):
        """Combine two queries together."""
        self._where = [or_(and_(*self._where), and_(*entity._where))]
        return self

    @classmethod
    def new(cls, session, entity):
        """Create a new Query object."""
        return Query(session, entity)

    def copy(self):
        # pylint: disable=protected-access
        """Create a new copy of the class."""
        cls = Query.new(session=self._session, entity=self._entity)
        cls._entity = self._entity
        cls._where = list(self._where)
        cls._populate = list(self._populate)
        cls._sort = list(self._sort)
        cls._offset = self._offset
        cls._limit = self._limit
        return cls

    def get(self, value, _value=None):
        """Get an entity from the ID.
        The _value argument is for compatibility with ftrack_api.Session.
        """
        if _value is None:
            entity = self._entity
        else:
            entity, value = value, _value
        return self._session.get(entity, value)

    def create(self, **kwargs):
        """Create a new entity."""
        return self._session.create(self._entity, kwargs)

    def ensure(self, **kwargs):
        """Ensure an entity.
        Will create if it doesn't exist.
        """
        return self._session.ensure(self._entity, kwargs)

    def one(self):
        """Returns and expects a single query result."""
        return self._session.query(str(self)).one()

    def first(self):
        """Returns the first available query result, or None."""
        return self._session.query(str(self)).first()

    def all(self):
        """Returns every query result."""
        return self._session.query(str(self)).all()

    def keys(self):
        """Get the keys related to an entity.
        As these are dynamically generated, the first call on an entity
        will perform a query, the results are then cached for later.
        """
        if self._entity not in self._EntityKeyCache:
            self._EntityKeyCache[self._entity] = self.first().keys()
        return self._EntityKeyCache[self._entity]

    @clone_instance
    def where(self, *args, **kwargs):
        """Filter the result."""
        self._where += list(Comparison.parser(*args, **kwargs))
        return self

    @clone_instance
    def populate(self, *args):
        """Prefetch attributes with the query."""
        # Allow empty string or None without breaking
        try:
            if not args[0] and len(args) == 1:
                return self
        except IndexError:
            return self

        self._populate += map(str, args)
        return self
    select = populate

    @clone_instance
    def sort(self, attribute=None):
        """Sort the query results."""
        desc = False

        # Grab the sorting method from the string if provided
        if attribute is not None:
            attribute = str(attribute)
            if ' ' in attribute:
                attribute, method = attribute.split(' ')
                if method == 'descending':
                    desc = True
                elif method != 'ascending':
                    raise NotImplementedError('unknown sorting method: {!r}'.format(method))

        if attribute is None:
            self._sort = []
        else:
            self._sort.append((attribute, desc))
        return self
    order = sort

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


class FTrackQuery(ftrack_api.Session):
    # pylint: disable=arguments-differ
    """Expansion of the ftrack_api.Session class."""

    exc = ftrack_api.exception
    symbol = ftrack_api.symbol
    Entity = ftrack_api.entity.base.Entity

    def __init__(self, **kwargs):
        """Attempt to initialise the connection.
        If the debug argument is set, the connection will be ignored.
        """
        self.debug = kwargs.pop('debug', False)
        self._logger = kwargs.pop('logger', logger)
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
                return Query.new(self, attr)
            raise

    def __exit__(self, type, value, traceback):
        """Override __exit__ to not break if debug mode is set."""
        if not self.debug:
            super(FTrackQuery, self).__exit__(type, value, traceback)
        if traceback is not None:
            return False

    def get(self, value, _value=None, *args, **kwargs):
        """Get any entity from its ID.
        The _value argument is for compatibility with ftrack_api.Session.
        """
        if _value is None:
            entity = 'Context'
        else:
            entity, value = value, _value
        self._logger.debug('Get: {}({})'.format(entity, value.__repr__()))
        return super(FTrackQuery, self).get(entity, value, *args, **kwargs)

    def query(self, query, *args, **kwargs):
        """Create an FTrack query object from a string."""
        query = str(query)
        self._logger.debug('Query: '+query)
        return super(FTrackQuery, self).query(query, *args, **kwargs)

    def create(self, entity, data, *args, **kwargs):
        """Create a new entity."""
        if not kwargs.get('reconstructing', False):
            self._logger.debug('Create: {}({})'.format(entity, dict_to_str(data)))
        return super(FTrackQuery, self).create(entity, data, *args, **kwargs)

    def delete(self, entity, *args, **kwargs):
        """Delete an FTrack entity."""
        self._logger.debug('Delete: '+entity.__repr__())
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


class Entity(object):
    """Quick access to a basic query object for comparisons.

    Example:
        >>> session.Episode.where(session.Episode.project.name=='Project')
        >>> session.Episode.where(entity.project.name=='Project')
    """

    def __init__(self):
        self._query = Query.new(None, None)

    def __getattr__(self, attr):
        """Bypass the methods of Query to just get attributes."""
        return self._query.__getattr__(attr)


and_ = Join('and', brackets=False, compare=Comparison)

or_ = Join('or', brackets=True, compare=Comparison)

entity = Entity()
