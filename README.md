# ftrack-query
Easy query generation for the FTrack API. The official module is extremely powerful and well designed, but the custom SQL is not very pythonic to use.
This is an object orientated approach to building queries, using inspiration from the design of SQLAlchemy.

This class expands upon `ftrack_api.Session`.

## Example Usage

```python
with FTrackQuery() as session:
    task = session.Task.first()
    note = session.Note.create(
        content='My new note',
        author=session.User.where(username='peter').one(),
        category=session.NoteLabel.where(name='Internal').one(),
    )
    task['notes'].append(note)
    
    session.commit()
```

## Equivalent examples from the [API reference](http://ftrack-python-api.rtd.ftrack.com/en/0.9.0/querying.html):

If an entity type is used multiple times, it's recommended to use `<Entity> = session.<Entity>` after the session is initialised. To save space below, that part has been omitted.

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
Task.where(project)

# session.query('Task where project.id is "{0}" and status.type.name is "Done"'.format(project['id']))
Task.where(Task.status.type.name=='Done', project=project)

# session.query('Task where timelogs.start >= "{0}"'.format(arrow.now().floor('day')))
Task.where(Task.timelogs.start>=arrow.now().floor('day'))

# session.query('Note where author has (first_name is "Jane" and last_name is "Doe")')
Note.where(Note.author.has(Username.first_name=='Jane', Username.last_name=='Doe'))

# session.query('User where not timelogs any ()')
User.where(~User.timelogs.any())

# projects = session.query('select full_name, status.name from Project')
Project.select('full_name', 'status.name')

# select name from Project where allocations.resource[Group].memberships any (user.username is "john_doe")
Project.select('name').where(Project.allocations.resource(Group).memberships.any(Project.user.username=='john_doe'))
```
