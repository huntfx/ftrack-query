# ftrack-query
FTrack Query is an object-orientated wrapper over the FTrack API. While the default query syntax is powerful, it is entirely text based so dynamic queries can be difficult to construct. This module supports **and**/**or** operators with nested comparisons.

It is recommended to first read https://ftrack-python-api.readthedocs.io/en/stable/tutorial.html for a basic understanding of how the FTrack API works.

## Installation
    pip install ftrack_query

## Examples

### Original Syntax
This will build queries attached to the current session, which allows them to be executed directly.

```python
from ftrack_query import FTrackQuery, entity, or_

with FTrackQuery() as session:
    # Create
    note = session.Note.create(
        content='My new note',
        author=session.User('peter'),
        category=session.NoteLabel.where(entity.color!=None, name='Internal').one(),
    )

    # Query
    task = session.Task.where(
        entity.status.name.in_('Lighting', 'Rendering'),
        or_(
            entity.parent == session.Episode.first(),
            entity.parent == None,
        ),
        name='My Task',
    ).order(
        entity.type.name.desc(),
    ).select(
        'name', 'type.name', 'status.name',
    ).first()

    task['notes'].append(note)
    session.commit()
```

# Statement Syntax
In version 1.7, new statement functions were added, to allow queries to be built without an associated `session` object.

These require a `session.execute` call in order to work, but the underlying logic is the same as with the original syntax.

```python
from ftrack_query import FTrackQuery, select, create, update, delete

with FTrackQuery() as session:
    # Query
    stmt = (
        select('Task.name', 'Task.type.name', 'Task.status.name')
        .where(entity.status.name.in_('Lighting', 'Rendering'))
        .order_by(entity.name.desc())
        .offset(5)
        .limit(1)
    )
    task = session.execute(stmt).first()
    print(f'Task found: {task})

    # Create
    stmt = (
        create('Task')
        .values(name='My Task', parent=task)
    )
    task = session.execute(stmt)
    session.commit()
    print(f'Task created: {task}')

    # Update
    stmt = (
        update('Task')
        .where(name='Old Task Name')
        .values(name='New Task Name')
    )
    rows = session.execute(stmt)
    session.commit()
    print(f'Tasks updated: {rows}')

    # Delete
    stmt = (
        delete('Task')
        .where(name='Old Task Name')
    )
    rows = session.execute(stmt)
    session.commit()
    print(f'Tasks deleted: {rows}')
```

### Event Syntax
The event system uses a slightly different query language, this has been added for convenience but generally should not be needed.

```python
from ftrack_query import FTrackQuery, event

with FTrackQuery() as session:
    session.event_hub.subscribe(str(
        event.and_(
            event.topic('ftrack.update'),
            event.data.user.name != getuser(),
        )
    ))
    session.event_hub.wait()
```

# Reference

## FTrackQuery
Main class inherited from `ftrack_api.Session`.

## Query
Every available entity type is an attribute of a session. What was originally `session.query('Note')` is now `session.Note`. This results in the `Query` object, which is used for constructing and executing queries.

### .where(_\*args, \*\*kwargs_)
Filter the result.

Using kwargs is the recommended way, with a syntax like `.where(first_name='Peter', last_name='Hunt')`.

Using args is required for complex queries. This uses the `Comparison` object, which is automatically created when comparing multiple `Query` objects. An example would be `.where(entity.project.metadata.any(entity.key!='disabled'))`.

### .populate(_\*args_) | .select(_\*args_)
Pre-fetch entity attributes.

An an example, in order to iterate through the name of every user, it would be a good idea to prefetch `first_name` and `last_name`, as otherwise two queries will be performed for each individual user.

### .order_by(_attribute_)
Sort the results by an attribute.

The attribute and order can be given in the format `entity.name.desc()`, or as a raw string such as `name descending`.

### .reverse()
Reverse the sorting direction.

### .limit(_value_)
Limit the amount of results to a certain value.

### .offset(_value_)
In the case of using a limit, this applies an offset to the result that is returned.

### .in_(_subquery_) | .not_in(_subquery_)
Perform a check to check if an attribute matches any results.

This can accept a subquery such `.in_('select id from table where x is y')`, or a list of items like `.in_('x', 'y')`.

### .\_\_call\_\_(_value_)
If an entity has a primary key, by calling the value of that primary key, the entity or `None` will be returned.
Currently only `User` supports this.

## Comparison
The `Comparison` object is designed to convert data to a string. It contains a wide array of operators that can be used against any data type, including other `Comparison` objects.

Any comparison can be reversed with the `~` prefix or the `not_` function.

- String Comparison: `entity.attr=='value'`
- Number comparison: `entity.attr>5`
- Pattern Comparison: `entity.attr.like('value%')`
- Time Comparison: `entity.attr.after(arrow.now().floor('day'))`
- Scalar Relationship: `entity.attr.has(subattr='value')`
- Collection Relationship: `entity.attr.any(subattr='value')`
- Subquery Relationship: `entity.attr.in_(subquery)`

## and\_(_\*args, \*\*kwargs_) | or\_(_\*args, \*\*kwargs_)
Join multiple comparisons. `and_` is used by default if nothing is provided.

## Statements
The statement functions build upon the `Query` object, but are not attached to any session. Instead of `session.Note`, it becomes `select('Note')`.

### select(_\*_entity_type_)
A select statement has access to the `Query` methods such as `.where()`.

If multiple arguments are given, it will use these in place of `.populate()` (eg. `select('Task.name', Task.parent')` is the same as `select('Task').populate('name', 'parent')`).

Calling `session.execute(stmt)` will execute the query and return FTrack's own `QueryResult` object, from which `.one()`, `.first()` or `.all()` may be called.

### create(_entity_type_)
A create statement has a `.values()` method used to input the data.

Calling `session.execute(stmt)` will return the created entity.

### update(_entity_type_)
An update statement has access to all of the `Query` methods, but also has a `.values()` method used to input the new data.

Calling `session.execute(stmt)` will return how many entities were found and updated.

### delete(_entity_type_)
A delete statement has access to most of the `Query` methods.

Calling `session.execute(stmt)` will return how many entities were deleted.

A convenience method, `.clean_components()`, can be used when deleting a `Component`. Enabling this will remove the component from every location before it is deleted.



## Equivalent examples from the [API reference](http://ftrack-python-api.rtd.ftrack.com/en/0.9.0/querying.html):

```python
# Project
select('Project')

# Project where status is active
select('Project').where(status='active')

# Project where status is active and name like "%thrones"
select('Project').where(entity.name.like('%thrones'), status='active')

# session.query('Project where status is active and (name like "%thrones" or full_name like "%thrones")')
select('Project').where(or_(entity.name.like('%thrones'), entity.full_name.like('%thrones')), status='active')

# session.query('Task where project.id is "{0}"'.format(project['id']))
select('Task').where(project=project)

# session.query('Task where project.id is "{0}" and status.type.name is "Done"'.format(project['id']))
select('Task').where(entity.status.type.name == 'Done', project=project)

# session.query('Task where timelogs.start >= "{0}"'.format(arrow.now().floor('day')))
select('Task').where(entity.timelogs.start >= arrow.now().floor('day'))

# session.query('Note where author has (first_name is "Jane" and last_name is "Doe")')
select('Note').where(entity.author.has(first_name='Jane', last_name='Doe'))

# session.query('User where not timelogs any ()')
select('User').where(~entity.timelogs.any())

# projects = session.query('select full_name, status.name from Project')
select('Project.full_name', 'Project.status.name')
# or
select('Project').populate('full_name', 'status.name')

# select name from Project where allocations.resource[Group].memberships any (user.username is "john_doe")
select('Project').select('name').where(entity.allocations.resource['Group'].memberships.any(entity.user.username == 'john_doe'))

# Note where parent_id is "{version_id}" or parent_id in (select id from ReviewSessionObject where version_id is "{version_id}")
select('Note').where(or_(entity.parent_id.in_(select('ReviewSessionObject.id').where(version_id=version_id)), parent_id=version_id))
```


## Planned Changes for 2.0

Since a lot of functionality has been added from the initial version, and old features are no longer needed, v2 is going to have a major overhaul.

- Replace `session.<Entity>` with `session.select(<Entity>)` - this will also remove the `session.<Entity>.get()` shortcut
- Replace `entity.x.y == z` with `attr('x.y') == z`
- Add `session.select`, `session.update`, `session.insert` and `session.delete`. This will allow the same queries to run with or without an attached session.
- All statements will have a `.execute()` method.
- `session.execute(stmt)` will call `stmt.options(session=self).execute()`
