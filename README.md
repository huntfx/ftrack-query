# ftrack-query
FTrack Query is an object-orientated wrapper over the FTrack API. While the default query syntax is powerful, it is entirely text based so dynamic queries can be difficult to construct. This module supports **and**/**or** operators with nested comparisons.

It is recommended to first read https://ftrack-python-api.readthedocs.io/en/stable/tutorial.html for a basic understanding of how the FTrack API works.

## Installation
    pip install ftrack_query

## Information

Instead of writing the whole query string at once, a "statement" is constructed (_eg. `stmt = select('Task')`_), and the query can be built up by calling methods such as `.where()` and `.populate()` on the statement.

The [CRUD](https://en.wikipedia.org/wiki/CRUD) methods are all supported (`create`, `select`, `update`, `delete`), but the main functionality is designed for use with `select`. The statements are built with a similar syntax to the main API so it should be straightforward to transition between the two.


## Examples

The below example is for very basic queries:

```python
from ftrack_query import FTrackQuery, attr, create, select, and_, or_

with FTrackQuery() as session:
    # Select
    project = session.select('Project').where(name='Test Project').one()

    # Create
    task = session.execute(
        create('Task').values(
            name='My Task',
            project=project,
        )
    )
    session.commit()

    # Update
    rows_updated = session.execute(
        update('Task')
        .where(name='Old Task Name')
        .values(name='New Task Name')
    )
    rows_updated = session.execute(stmt)
    session.commit()

    # Delete
    rows_deleted = session.execute(
        delete('Task').where(
            name='Old Task Name',
        )
    )
    rows_deleted = session.execute(stmt)
    session.commit()
```

For a much more complex example:


```python

ATTR_TYPE = attr('type.name')

TASK_STMT = (
    select('Task')
    # Filter the tasks
    .where(
        # Get any task without these statuses
        ~attr('status.name').in_(['Lighting', 'Rendering']),
        # Check for notes matching any of the following conditions:
        attr('notes').any(
            # Ensure note was posted by someone outside the company
            ~attr('user.email').endswith('@company.com')
            # Ensure note either not completable or not completed
            or_(
                and_(
                    completed_by=None,
                    is_todo=True,
                ),
                is_todo=False,
            ),
        ),
        # Ensure it has an animation task
        or_(
            ATTR_TYPE.contains('Animation'),
            ATTR_TYPE == 'Anim_Fixes',
        ),
    ),
    # Order the results
    .order_by(
        ATTR_TYPE.desc(),  # Equivalent to "type.name desc"
        'name',
    )
    # Use projections to populate attributes as part of the query
    .populate(
        'name',
        'notes',
        'status.name',
        ATTR_TYPE,
    )
    .limit(5)
)

with FTrackQuery() as session:
    # Filter the above query to the result of another query
    task_stmt = TASK_STMT.where(
        project_id=session.select('Project').where(name='Test Project').one()['id']
    )

    # Use the current session to execute the statement
    tasks = session.execute(task_stmt).all()
```


### Events
The event system uses a slightly different query language.

```python
from ftrack_query import FTrackQuery, event
from ftrack_query.event import attr, and_, or_

with FTrackQuery() as session:
    session.event_hub.subscribe(str(
        and_(
            attr('topic') == 'ftrack.update',
            attr('data.user.name') != getuser(),
        )
    ))
    session.event_hub.wait()
```

Note that `attr()`, `and_()`, and `or_()` are present in both `ftrack_query` and `ftrack_query.event`. These are **not** interchangable, so if both are needed, then import `event` and use that as the namespace.

# API Reference

## ftrack_query.FTrackQuery
Main class inherited from `ftrack_api.Session`.

## ftrack_query.select
Used for building the query string.

```python
from ftrack_query import select

stmt = select(entity).where(...).populate(...)
```

Calling `session.execute(stmt)` will execute the query and return FTrack's own `QueryResult` object, from which `.one()`, `.first()` or `.all()` may be called. Alternatively, by using the shortcut `session.select(entity)`, then this may be skipped.

### where(_\*args, \*\*kwargs_)
Filter the result.

Using keywords is the fastest way, such as `.where(first_name='Peter', last_name='Hunt')`.
However `attr()` is required for relationship queries, or anything other than eqality checks, such as `.where(attr('project.metadata').any(attr('key') != 'disabled'))`.

### populate(_\*attrs_)
Pre-fetch entity attributes.

An an example, in order to iterate through the name of every user, it would be a good idea to load `first_name` and `last_name` as part of the query. Without that, it would take 2 separate queries _per user_, which is known as the [N+1 query problem](https://stackoverflow.com/questions/97197/what-is-the-n1-selects-problem-in-orm-object-relational-mapping).

### order_by(_\*attrs_) | order(_\*attrs_) | order(_\*attrs_)
Sort the results by an attribute.

The attribute and order can be given in the format `attr('name').desc()`, or as a raw string such as `name descending`.

### reverse()
Reverse the sorting direction.

### limit(_value_)
Limit the amount of results to a certain value.

Note: This is not compatible with calling `.first()` or `.one()`, as FTrack applies their own limit automatically.

### offset(_value_)
In the case of using a limit, apply an offset to the result that is returned.

### options(_\*\*kwargs_)
For advanced users only.
`page_size`: Set the number of results to be fetched at once from FTrack.
`session`: Attach a session object to the query.

### subquery(_attribute='id'_)
Make the statement a subquery for use within `.in_()`.
This ensures there's always a "select from" as part of the statement.
Manually setting the attribute parameter will override any existing projections.


## ftrack_query.create
Used for creating new entities.

```python
from ftrack_query import create

stmt = create(entity).values(...)
```

Calling `session.execute(stmt)` will return the created entity.

### values(_\*\*kwargs_)
Values to create the entity with.

## ftrack_query.update
Used to quickly update values.
This is built off the `select` method so contains a lot of the same methods.

```python
from ftrack_query import update

stmt = update(entity).where(...).values(...)
```

Calling `session.execute(stmt)` will return how many entities were found and updated.

### where(_\*args, \*\*kwargs_)
Filter what to update.

### values(_\*\*kwargs_)
Values to update on the entity.


## ftrack_query.delete
Used to delete entities.
This is built off the `select` method so contains a lot of the same methods.

```python
from ftrack_query import delete

stmt = delete(entity).where(...).options(remove_components=True)
```

Calling `session.execute(stmt)` will return how many entities were deleted.

A convenience method, `.options(remove_components=True)`, can be used when deleting a `Component`.

### where(_\*args, \*\*kwargs_)
Filter what to update.

### options(_\*\*kwargs_)
Additional flag added for `remove_components`.
Enabling this will remove any `Component` entity from every `Location` containing it before it is deleted.
Note that this prevents rollbacks so is not enabled by default.


## ftrack_query.attr
The `Comparison` object is designed to convert data to a string. It contains a wide array of operators that can be used against any data type, including other `Comparison` objects. The function `attr` is a shortcut to this.

Any comparison can be reversed with the `~` prefix or the `not_` function.

- String Comparison: `attr(key) == 'value'`
- Number comparison: `attr(key) > 5`
- Pattern Comparison: `attr(key).like('value%')`
- Time Comparison: `attr(key).after(arrow.now().floor('day'))`
- Scalar Relationship: `attr(key).has(subkey='value')`
- Collection Relationship: `attr(key).any(subkey='value')`
- Subquery Relationship: `attr(key).in_(subquery)`

### \_\_eq\_\_(_value_) | \_\_ne\_\_(_value_) | \_\_gt\_\_(_value_) | \_\_ge\_\_(_value_) | \_\_lt\_\_(_value_) | \_\_lt\_\_(_value_)
Simple comparisons.

### and\_(_\*args, \*\*kwargs_) | or\_(_\*args, \*\*kwargs_)
Join multiple comparisons.
`and_` is used by default if multiple arguments are given.

### in\_(_values_) | not\_in(_values_)
Perform a check to check if an attribute matches any results.

This can accept a subquery such `.in_('select id from table where x is y')`, or a list of items like `.in_(['x', 'y'])`.

### like(_value_) | not\_like(_value_) | startswith(_value_) | endwith(_value_) | contains(_value_)
Check if a string is contained within the query.
Use a percent sign as the wildcard if using `like` or `not_like`; the rest are shortcuts and do this automatically.

### has\_(_\*args, \*\*kwargs_) | any\_(_\*args, \*\*kwargs_)
Test against scalar and collection relationships.

### before(_values_) | after(_values_)
Test against dates.
Using `arrow` objects is recommended.


## Equivalent examples from the [API reference](http://ftrack-python-api.rtd.ftrack.com/en/0.9.0/querying.html):

```python
# Project
select('Project')

# Project where status is active
select('Project').where(status='active')

# Project where status is active and name like "%thrones"
select('Project').where(attr('name').like('%thrones'), status='active')

# session.query('Project where status is active and (name like "%thrones" or full_name like "%thrones")')
select('Project').where(or_(attr('name').like('%thrones'), attr('full_name').like('%thrones')), status='active')

# session.query('Task where project.id is "{0}"'.format(project['id']))
select('Task').where(project=project)

# session.query('Task where project.id is "{0}" and status.type.name is "Done"'.format(project['id']))
select('Task').where(attr('status.type.name') == 'Done', project=project)

# session.query('Task where timelogs.start >= "{0}"'.format(arrow.now().floor('day')))
select('Task').where(attr('timelogs.start') >= arrow.now().floor('day'))

# session.query('Note where author has (first_name is "Jane" and last_name is "Doe")')
select('Note').where(attr('author').has(first_name='Jane', last_name='Doe'))

# session.query('User where not timelogs any ()')
select('User').where(~attr('timelogs').any())

# projects = session.query('select full_name, status.name from Project')
select('Project').populate('full_name', 'status.name')

# select name from Project where allocations.resource[Group].memberships any (user.username is "john_doe")
select('Project').select('name').where(attr('allocations.resource[Group].memberships').any(attr('user.username') == 'john_doe'))

# Note where parent_id is "{version_id}" or parent_id in (select id from ReviewSessionObject where version_id is "{version_id}")
select('Note').where(or_(attr('parent_id').in_(select('ReviewSessionObject').where(version_id=version_id).subquery()), parent_id=version_id))
```
