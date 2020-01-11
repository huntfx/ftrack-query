# ftrack-query
Easy query generation for the FTrack API. The official module is extremely well written, but the custom SQL was not very pythonic to use. This is a more object orientated approach to building queries, using inspiration from SQLAlchemy.

To provide a more complete set of features, the ability to create was also added, as it is quite a similar syntax anyway.

## Equivalent examples from the [API reference](http://ftrack-python-api.rtd.ftrack.com/en/0.9.0/querying.html):

Every entity in use should be defined like `Entity = session.Entity` (not doing so is fine, but it's recommended for longer queries). To save space below, that part has been omitted.

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
Note.where(Note.author.has(Username.first_name=='Jane', Username.last_name=='Doe'))

# session.query('User where not timelogs any ()')
User.where(~User.timelogs.any())

# projects = session.query('select full_name, status.name from Project')
Project.select('full_name', 'status.name')

# select name from Project where allocations.resource[Group].memberships any (user.username is "john_doe")
Project.select('name').where(Project.allocations.resource(Group).memberships.any(Project.user.username=='john_doe'))
```
