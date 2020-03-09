# ftrack-query
FTrack Query is an object-orientated wrapper over the FTrack API. While the default query syntax is powerful, it is entirely text based so dynamic queries can be difficult to construct. This module supports **and**/**or** operators with nested comparisons.

It is recommended to first read http://ftrack-python-api.rtd.ftrack.com/en/1.7.0/tutorial.html for a basic understanding of how the FTrack API works.


## Example
```python
with FTrackQuery() as session:
    note = session.Note.create(
        content='My new note',
        author=session.User('peter'),
        category=session.NoteLabel.where(entity.color!=None, name='Internal').one(),
    )

    task = session.Task.where(
        entity.parent==session.Episode.first(),
        name='My Task',
    ).order(
        entity.type.name.desc(),
    ).first()

    task['notes'].append(note)
    session.commit()
```

# Reference

## FTrackQuery
Main class inherited from `ftrack_api.Session`.

## Query
Every available entity type is an attribute of a session. What was originally `session.query('Note')` is now `session.Note`. This results in the `Query` object, which is used for constructing and executing queries.

### .where(\*args, \*\*kwargs)
Filter the result.

Using kwargs is the recommended way, with a syntax like `.where(first_name='Peter', last_name='Hunt')`.

Using args is required for complex queries. This uses the `Comparison` object, which is automatically created when comparing multiple `Query` objects. An example would be `.where(entity.project.metadata.any(entity.key!='disabled'))`.

### .populate(\*args) | .select(\*args)
Pre-fetch entity attributes.

An an example, in order to iterate through the name of every user, it would be a good idea to prefetch `first_name` and `last_name`, as otherwise two queries will be performed for each individual user.

### .sort(attribute)
Sort the results by an attribute.

The attribute and order can be given in the format `entity.name.desc()`, or as a raw string such as `name descending`.

### .reverse()
Reverse the sorting direction.

### .limit(value)
Limit the amount of results to a certain value.

### .offset(value)
In the case of using a limit, this applies an offset to the result that is returned.

### .__call__(value)
If an entity has a primary key, by calling the value of that primary key, the entity or `None` will be returned.
Currently only `User` supports this.

## Comparison
The `Comparison` object is designed to convert data to a string. It contains a wide array of operators that can be used against any data type, including other `Comparison` objects.

Any comparison can be reversed with the `~` prefix.

- String Comparison: `entity.attr=='value'`
- Number comparison: `entity.attr>5`
- Pattern Comparison: `entity.attr.like('value%')`
- Time Comparison: `entity.attr.after(arrow.now().floor('day'))`
- Scalar Relationship: `entity.attr.has(subattr='value')`
- Collection Relationship: `entity.attr.any(subattr='value')`

## and_(\*args, \*\*kwargs) | or_(\*args, \*\*kwargs)
Join multiple comparisons. `and_` is used by default if nothing is provided.

## Equivalent examples from the [API reference](http://ftrack-python-api.rtd.ftrack.com/en/0.9.0/querying.html):
Note: If an entity type is used multiple times, it's recommended to use `<Entity> = session.<Entity>` after the session is initialised. To save space below, that part has been omitted.

```python
# projects = session.query('Project')
# for project in projects:
#     print project['name']
projects = Project
for project in projects:
    print project['name']

# session.query('Project').all()
Project.all()

# session.query('Project where status is active')
Project.where(status='active')

# session.query('Project where status is active and name like "%thrones"')
Project.where(Project.name.like('%thrones'), status='active')

# session.query('Project where status is active and (name like "%thrones" or full_name like "%thrones")')
Project.where(or_(Project.name.like('%thrones'), Project.full_name.like('%thrones')), status='active')

# session.query('Task where project.id is "{0}"'.format(project['id']))
Task.where(project=project)

# session.query('Task where project.id is "{0}" and status.type.name is "Done"'.format(project['id']))
Task.where(Task.status.type.name=='Done', project=project)

# session.query('Task where timelogs.start >= "{0}"'.format(arrow.now().floor('day')))
Task.where(Task.timelogs.start>=arrow.now().floor('day'))

# session.query('Note where author has (first_name is "Jane" and last_name is "Doe")')
Note.where(Note.author.has(User.first_name=='Jane', User.last_name=='Doe'))

# session.query('User where not timelogs any ()')
User.where(~User.timelogs.any())

# projects = session.query('select full_name, status.name from Project')
Project.select('full_name', 'status.name')

# select name from Project where allocations.resource[Group].memberships any (user.username is "john_doe")
Project.select('name').where(Project.allocations.resource[Group].memberships.any(Membership.user.username=='john_doe'))
```
