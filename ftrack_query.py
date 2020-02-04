"""Python wrapper over the SQL based FTrack syntax.
Inspiration for the syntax was taken from SQLALchemy.
Querying and creating is supported, and extra functionality will be
added if the need arises.
"""

__all__ = ['FTrackQuery', 'and_', 'or_']
__version__ = '1.0.5'

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


def convert_arg_entity(func):
    """Convert any entity arguments to keys."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, ftrack_api.entity.base.Entity):
                comparison = getattr(Query(None, None), get_key_from_entity(arg))
                args[i] = comparison.id == arg['id']
        return func(self, *args, **kwargs)
    return wrapper


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
        # For example, "<Project>" will evaluate to "project.id is <Project['id']>"
        elif isinstance(arg, ftrack_api.entity.base.Entity):
            yield '{} {} {}'.format(get_key_from_entity(arg)+'.id', comparison, arg['id'])

        # The object is likely a comparison object, so convert to str
        # If an actual string is input, then assume it's valid syntax
        else:
            yield str(arg)

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
        query = []
        if kwargs:
            query.append(' {} '.format(self.operator).join(
                '{} is "{}"'.format(k, v) for k, v in kwargs.items()
            ))
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

    def __call__(self, value):
        """Cast a relation to a concrete type.
        One example would be TypedContext.parent(Project), where it
        will limit the TypedContext search to the direct children of
        projects.
        """
        return self.__class__('{}[{}]'.format(self.value, value))

    @parse_value
    def __eq__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} is {}'.format(base, value))
    is_ = __eq__

    @parse_value
    def __ne__(self, value, base=None):
        if base is None:
            base = self.value
        return self.__class__('{} is_not {}'.format(base, value))
    is_not = __ne__

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

    @convert_arg_entity
    def has(self, *args, **kwargs):
        where = parse_inputs(*args, **kwargs)
        return self.__class__('{} has ({})'.format(self.value, and_(*where)))

    @convert_arg_entity
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
        if entity == 'Note':
            return QueryNote(session)
        if entity == 'User':
            return QueryUser(session)
        if entity == 'CalendarEvent':
            return QueryCalendarEvent(session)
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
        self._session._logger.debug('Get ({}): {}'.format(entity, value))
        return super(FTrackQuery, self._session).get(entity, value)

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
        self._populate += map(str, args)
        return self
    select = populate

    @clone_instance
    def sort(self, attribute, desc=None, asc=None):
        """Sort the query results."""
        if desc is not None and asc is not None:
            raise ValueError('sorting cannot be both descending and ascending')
        elif desc is None and asc is None:
            desc = False
        elif asc is not None:
            desc = not asc
        self._sort.append((attribute, desc))
        return self
    order = sort

    @clone_instance
    def offset(self, value):
        """Offset the results when a limit is used."""
        self._offset = value
        return self

    @clone_instance
    def limit(self, value):
        """Limit the total number of results."""
        self._limit = value
        return self


class QueryNote(Query):
    def __init__(self, session):
        """Initialise as the Note entity."""
        super(QueryNote, self).__init__(session, 'Note')

    def create(self, **kwargs):
        """Handle special cases when creating notes.

        recipients:
            This is a link between group/user and notes.
            For ease of use, the entity will be automatically created
            if another entity type is given.

        category:
            According to the API code, categories will be deprecated,
            and NoteLabelLinks should be used instead. This deals with
            the conversion automatically.
        """
        try:
            recipients = list(kwargs.pop('recipients', []))
        except TypeError:
            recipients = []
        category = kwargs.pop('category', None)

        note = super(QueryNote, self).create(**kwargs)

        for recipient in recipients:
            if recipient.__class__.__name__ != 'Recipient':
                recipient = self._session.Recipient.create(
                    note=note,
                    note_id=note['id'],
                    resource=recipient,
                    resource_id=recipient['id'],
                )
            note['recipients'].append(recipient)
        if category:
            link = self._session.NoteLabelLink.create(
                note_id=note['id'],
                label_id=category['id'],
            )
            link['note'] = note
            link['label'] = category
            note['note_label_links'].append(link)
        return note


class QueryUser(Query):
    def __init__(self, session):
        """Initialise as the User entity."""
        super(QueryUser, self).__init__(session, 'User')

    def ensure(self, **kwargs):
        """Set the identifying key as username."""
        return self._session.ensure(self._entity, kwargs, identifying_keys=['username'])


class QueryCalendarEvent(Query):
    def __init__(self, session):
        """Initialise as the CalendarEvent entity."""
        super(QueryCalendarEvent, self).__init__(session, 'CalendarEvent')

    def create(self, **kwargs):
        """Handle special cases when creating calendar events.

        calendar_event_resources:
            This is a link between user and calendar events.
            For ease of use, the entity will be automatically created
            if another entity type is given.
        """
        try:
            resources = kwargs.pop('calendar_event_resources', [])
        except TypeError:
            resources = []
        calendar_event = super(QueryCalendarEvent, self).create(**kwargs)

        for resource in resources:
            if resource.__class__.__name__ != 'CalendarEventResource':
                resource = self._session.CalendarEventResource.create(
                    calendar_event=calendar_event,
                    resource=resource,
                    resource_id=resource['id'],
                )
            calendar_event['calendar_event_resources'].append(resource)
        return calendar_event


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
        if not self.debug:
            super(FTrackQuery, self).__init__(**kwargs)
        self._logger.debug('New session initialised.')

    def __getattr__(self, attr):
        """Get entity."""
        return Query.new(self, attr)

    def __exit__(self, *args):
        """Override __exit__ to not break if debug mode is set."""
        if not self.debug:
            return super(FTrackQuery, self).__exit__(*args)

    def get(self, value, _value=None):
        """Get any entity from its ID.
        The _value argument is for compatibility with ftrack_api.Session.
        """
        if _value is None:
            entity = 'Context'
        else:
            entity, value = value, _value
        self._logger.debug('Get ({}): {}'.format(entity, value))
        return super(FTrackQuery, self).get(entity, value)

    def query(self, query):
        """Create an FTrack query object from a string."""
        query = str(query)
        self._logger.debug('Query: '+query)
        return super(FTrackQuery, self).query(query)

    def delete(self, entity):
        """Delete an FTrack entity."""
        self._logger.debug('Delete: '+entity.__repr__())
        return super(FTrackQuery, self).delete(entity)
