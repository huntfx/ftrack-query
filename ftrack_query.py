"""Python wrapper over the SQL based FTrack syntax.
Inspiration for the syntax was taken from SQLALchemy.
Querying and creating are supported.
"""

__all__ = ['FTrackQuery', 'entity', 'and_', 'or_']
__version__ = '1.3.1'

import logging
import os
import ftrack_api
from functools import wraps
from string import ascii_lowercase, ascii_uppercase


logger = logging.getLogger('ftrack-query')


def clone_instance(func):
    """To avoid modifying the current instance, create a new one."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self.copy(), *args, **kwargs)
    return wrapper


def convert_output_value(value):
    """Convert the output value to something that FTrack understands.
    As of right now, this is adding speech marks.
    """
    if value is None:
        return 'none'
    elif isinstance(value, (float, int)):
        return value
    return '"{}"'.format(value)


def parse_operators(func):
    """Parse the value when an operator is used."""
    @wraps(func)
    def wrapper(self, value):
        # If an entity is passed in, use the ID
        if isinstance(value, ftrack_api.entity.base.Entity):
            return func(self, convert_output_value(value['id']), base=self.value+'.id')
        return func(self, convert_output_value(value))
    return wrapper


def dict_to_str(dct):
    """Convert a dict to a string."""
    def convert(dct):
        for k, v in dct.items():
            if isinstance(v, ftrack_api.entity.base.Entity):
                v = str(v)
            else:
                v = v.__repr__()
            yield '{}={}'.format(k, v)
    return ', '.join(convert(dct))


def parse_inputs(*args, **kwargs):
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

    comparison = kwargs.pop('__cmp__', 'is')
    for arg in args:
        # The query has not been performed, attempt to execute
        # This shouldn't really be used, so don't catch any errors
        if isinstance(arg, Query):
            arg = arg.one()

        if isinstance(arg, dict):
            for key, value in arg.items():
                yield Comparison(key)==value

        # Attempt to convert entity to lowercase name with ID
        # For example, "<Project>" will evaluate to 'project.id is "<Project['id']>"'
        elif isinstance(arg, ftrack_api.entity.base.Entity):
            yield ' '.join([
                get_key_from_entity(arg)+'.id',
                comparison,
                convert_output_value(arg['id'])
            ])

        # The object is likely a comparison object, so convert to str
        # If an actual string is input, then assume it's valid syntax
        else:
            yield arg

    for key, value in kwargs.items():
        if isinstance(value, Query):
            value = value.one()
        yield Comparison(key)==value


_UC_REMAP = {u: '_'+l for l, u in zip(ascii_lowercase, ascii_uppercase)}
def get_key_from_entity(entity):
    """Guess the attribute that would be given to an entity.
    This is done by converting UpperCase to lower_case.

    Ideally this shouldn't ever be called, but in some cases it can
    make sense. Instead of "Task.where(project=project)", we can assume
    the attribute is "project", and write it as "Task.where(project)".
    """
    if isinstance(entity, ftrack_api.entity.base.Entity):
        entity = entity.__class__.__name__
    if entity == 'NoteLabel':
        return 'category'
    return ''.join(_UC_REMAP.get(c, c) for c in entity).lstrip('_')


class Criteria(object):
    """Convert multiple arguments into a valid query."""
    def __init__(self, operator, brackets):
        self.operator = operator
        self.brackets = brackets

    def __call__(self, *args, **kwargs):
        query_parts = list(parse_inputs(*args, **kwargs))
        query = ' {} '.format(self.operator).join(map(str, query_parts))
        if self.brackets and len(query_parts) > 1:
            return Comparison('({})'.format(query))
        return Comparison(query)


and_ = Criteria('and', brackets=False)

or_ = Criteria('or', brackets=True)


class Comparison(object):
    """Deal with individual query comparisons."""
    def __init__(self, value):
        self.value = value

    def __getattr__(self, attr):
        """Get sub-attributes of the entity attributes.
        Example: session.Entity.attr.<subattr>.<subattr>...
        """
        return Comparison(self.value+'.'+attr)

    def __repr__(self):
        return 'Comparison({})>'.format(self.value.__repr__())

    def __str__(self):
        return self.value

    def __invert__(self):
        return self.__class__('not '+self.value)

    def __getitem__(self, value):
        """Cast a relation to a concrete type.
        One example would be TypedContext.parent(Project), where it
        will limit the TypedContext search to the direct children of
        projects.
        """
        return self.__class__('{}[{}]'.format(self.value, value))

    def __call__(self):
        """Access special features based on the attribute name.
        For example, .desc can be used as a key normally, but .desc()
        will be used as a sort string.
        If no override exists, then the standard TypeError will be
        raised.
        """
        value, attr = self.value.rsplit('.', 1)
        if attr == 'desc':
            return '{} descending'.format(value)
        elif attr == 'asc':
            return '{} ascending'.format(value)
        else:
            raise TypeError("'{}' object is not callable".format(self.__class__.__name__))

    @parse_operators
    def __eq__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} is {}'.format(base, value))
    is_ = __eq__

    @parse_operators
    def __ne__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} is_not {}'.format(base, value))
    is_not = __ne__

    @parse_operators
    def __gt__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} > {}'.format(base, value))

    @parse_operators
    def __ge__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} >= {}'.format(base, value))

    @parse_operators
    def __lt__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} < {}'.format(base, value))

    @parse_operators
    def __le__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} <= {}'.format(base, value))

    @parse_operators
    def like(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} like {}'.format(base, value))

    @parse_operators
    def not_like(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} not_like {}'.format(base, value))

    @parse_operators
    def after(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} after {}'.format(base, value))

    @parse_operators
    def before(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} before {}'.format(base, value))

    def has(self, *args, **kwargs):
        where = parse_inputs(*args, **kwargs)
        return self.__class__('{} has ({})'.format(self.value, and_(*where)))

    def any(self, *args, **kwargs):
        where = parse_inputs(*args, **kwargs)
        return self.__class__('{} any ({})'.format(self.value, and_(*where)))


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
        """
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
        self._where += list(parse_inputs(*args, **kwargs))
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
        asc = desc = False

        # Grab the sorting method from the string if provided
        if attribute is not None and ' ' in attribute:
            attribute, method = attribute.split(' ')
            if method == 'ascending':
                asc = True
            elif method == 'descending':
                desc = True

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


# Quick access to a query object for comparisons
# An example would be "session.Episode.where(entity.project.name=='Project')"
# instead of "session.Episode.where(session.Episode.project.name=='Project')"
entity = Query.new(None, None)
