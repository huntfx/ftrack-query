__all__ = ['entity', 'and_', 'or_', 'not_']

import ftrack_api

from .abstract import AbstractComparison, AbstractQuery
from .utils import Join, clone_instance, convert_output_value, not_, parse_operators


class Comparison(AbstractComparison):
    # pylint: disable=unexpected-special-method-signature
    """Comparisons for the query syntax."""

    def __getitem__(self, value):
        """Cast a relation to a concrete type.
        One example would be TypedContext.parent[Project], where it
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

        Example:
            >>> entity.name.desc
            'name.desc'
            >>> entity.name.desc()
            'name descending'
        """
        try:
            value, attr = self.value.rsplit('.', 1)
        except ValueError:
            pass
        else:
            if attr in ('desc', 'descending'):
                return '{} descending'.format(value)
            elif attr in ('asc', 'ascending'):
                return '{} ascending'.format(value)
        return super(Comparison, self).__call__(*args, **kwargs)

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
        where = Comparison.parser(*args, **kwargs)
        return self.__class__('{} has ({})'.format(self.value, and_(*where)))

    def any(self, *args, **kwargs):
        """Test a collection relationship for values."""
        where = Comparison.parser(*args, **kwargs)
        return self.__class__('{} any ({})'.format(self.value, and_(*where)))

    def in_(self, *args):
        """One of these values.
        This supports both subqueries (x in (select y from z)), and
        multiple items (x in ("y", "z")).
        Since quotation marks are important in the final query, an
        attempt is made to guess if the input is a subquery or a list
        of possible values.
        """
        if not args:
            return self.__class__('{} in ()'.format(self.value))
        single_arg = len(args) == 1

        # Args were given as a built query
        # If a single query, assume .all() is required
        # If multiple queries, assume .one() is required on each
        if single_arg and isinstance(args[0], AbstractQuery):
            args = args[0].all()
        elif isinstance(args[0], AbstractQuery):
            args = [query.one() for query in args]

        # Args were given as entities
        if isinstance(args[0], ftrack_api.entity.base.Entity):
            return self.__class__('{}.id in ({})'.format(
                self.value, ', '.join(convert_output_value(entity['id']) for entity in args)
            ))

        # Args were given as a list of strings
        if single_arg and args[0].startswith('select ') and ' from ' in args[0]:
            subquery = args[0]
        else:
            subquery = ', '.join(map(convert_output_value, args))
        return self.__class__('{} in ({})'.format(self.value, subquery))

    def not_in(self, *args):
        """Not one of these values.
        See in_() for implementation details.
        """
        return self.in_(*args).__invert__()

    def startswith(self, value):
        """If a value starts with this."""
        return self.like(value.replace('%', '\\%') + '%')

    def endswith(self, value):
        """If a value ends with this."""
        return self.like('%' + value.replace('%', '\\%'))


class Query(AbstractQuery):
    """Base class for constructing a query."""
    _EntityKeyCache = {}

    # These keys are used where it's likely there's a unique value for each entity
    _PrimaryKeys = dict(
        AssetType='name',
        Disk='name',
        ListCategory='name',
        Location='name',
        ManagerType='name',
        NoteLabel='name',
        ObjectType='name',
        Priority='name',
        Project='name',
        ProjectSchema='name',
        SecurityRole='name',
        Scope='name',
        Setting='name',
        State='name',
        Status='name',
        Type='name',
        User='username',
    )

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
        As the FTrack database is case insensitive, in the case of
        multiple results, use Python to find the exact match.
        """
        if self._entity in self._PrimaryKeys and len(args) == 1 and not kwargs:
            key = self._PrimaryKeys[self._entity]
            value = args[0]
            try:
                return self.where(**{key: value}).one()
            except ftrack_api.exception.NoResultFoundError:
                return None
            except ftrack_api.exception.MultipleResultsFoundError:
                for result in self.where(**{key: value}):
                    if result[key] == value:
                        return result
                raise


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
                if method in ('desc', 'descending'):
                    desc = True
                elif method != ('asc', 'ascending'):
                    raise NotImplementedError('unknown sorting method: {!r}'.format(method))

        if attribute is None:
            self._sort = []
        else:
            self._sort.append((attribute, desc))
        return self
    order = order_by = sort

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
