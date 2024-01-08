import os
import unittest
import sys

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import attr, or_, and_, not_, select, create, update, delete, event


class TestAttr(unittest.TestCase):
    def test_cmp(self):
        self.assertEqual(str(attr('version') == 5), 'version is 5')
        self.assertEqual(str(attr('version') != 5), 'version is_not 5')
        self.assertEqual(str(attr('version') > 5), 'version > 5')
        self.assertEqual(str(attr('version') >= 5), 'version >= 5')
        self.assertEqual(str(attr('version') < 5), 'version < 5')
        self.assertEqual(str(attr('version') <= 5), 'version <= 5')
        self.assertEqual(str(attr('version') > 5), 'version > 5')

    def test_is(self):
        self.assertEqual(str(attr('parent.id').is_('123')), 'parent.id is "123"')
        self.assertEqual(str(attr('parent.id').is_not('123')), 'parent.id is_not "123"')

    def test_sort(self):
        self.assertEqual(str(attr('parent_id').asc()), 'parent_id ascending')
        self.assertEqual(str(attr('parent_id').desc()), 'parent_id descending')
        self.assertEqual(str(attr('parent_id').ascending()), 'parent_id ascending')
        self.assertEqual(str(attr('parent_id').descending()), 'parent_id descending')

    def test_contains(self):
        with self.assertRaises(TypeError):
            'abc' in attr('parent.name')
        self.assertEqual(str(attr('parent.name').contains('abc')), 'parent.name like "%abc%"')
        self.assertEqual(str(attr('parent.name').like('%abc%')), 'parent.name like "%abc%"')
        self.assertEqual(str(attr('parent.name').startswith('abc')), 'parent.name like "abc%"')
        self.assertEqual(str(attr('parent.name').endswith('abc')), 'parent.name like "%abc"')
        self.assertEqual(str(attr('parent.name').not_like('%abc%')), 'parent.name not_like "%abc%"')

    def test_collection(self):
        self.assertEqual(str(attr('parent').has(name='abc')), 'parent has (name is "abc")')
        self.assertEqual(str(attr('parent').has(attr('name') == 'abc')), 'parent has (name is "abc")')
        self.assertEqual(str(attr('parent').has(attr('name') != 'abc')), 'parent has (name is_not "abc")')
        self.assertEqual(str(attr('children').any(name='abc')), 'children any (name is "abc")')

    def test_date(self):
        import arrow
        self.assertEqual(str(attr('date').before(arrow.get(0))), 'date before "1970-01-01T00:00:00+00:00"')
        self.assertEqual(str(attr('date').after(arrow.get(0))), 'date after "1970-01-01T00:00:00+00:00"')

    def test_in_values(self):
        self.assertEqual(str(attr('id').in_(123, 'abc')), 'id in (123, "abc")')

    def test_in_generator(self):
        self.assertEqual(str(attr('id').in_(i for i in range(5))), 'id in (0, 1, 2, 3, 4)')
        self.assertEqual(str(attr('id').in_(str(i) for i in range(5))), 'id in ("0", "1", "2", "3", "4")')

    def test_in_empty(self):
        self.assertEqual(str(attr('id').in_(i for i in ())), 'id in ("")')
        self.assertEqual(str(attr('id').in_()), 'id in ("")')

    def test_in_subquery(self):
        subquery = select('Task').where(name='abc')
        self.assertEqual(str(attr('id').in_(subquery)), 'id in (select id from Task where name is "abc")')
        self.assertEqual(str(attr('id').not_in(subquery)), 'id not_in (select id from Task where name is "abc")')
        with self.assertRaises(ValueError):
            attr('id').in_(subquery, subquery)

        subquery = subquery.populate('name')
        self.assertEqual(str(attr('id').in_(subquery)), 'id in (select name from Task where name is "abc")')
        subquery = subquery.populate('project')
        self.assertEqual(str(attr('id').in_(subquery)), 'id in (select name, project from Task where name is "abc")')

        self.assertEqual(str(attr('id').in_('select id from Task')), 'id in (select id from Task)')

    def test_in_entity(self):
        import ftrack_api
        class Entity(ftrack_api.entity.base.Entity):
            """Recreation of the entity class to not require a session."""
            def __init__(self): pass
            def __repr__(self): return "<dynamic ftrack class 'Entity'>"
            def __getitem__(self, item): return '123'
            def __str__(self): return '<Entity(00000000-0000-0000-0000-000000000000)>'

        self.assertEqual(str(attr('parent').in_(Entity())), 'parent.id in ("123")')
        self.assertEqual(str(attr('parent').in_(Entity(), Entity())), 'parent.id in ("123", "123")')
        self.assertEqual(str(attr('parent').in_(Entity(), 123)), 'parent.id in ("123", 123)')

    def test_in_unsupported_type(self):
        self.assertEqual(str(attr('id').in_([123, 'abc'])), 'id in ("[123, \'abc\']")')
        self.assertEqual(str(attr('id').in_([123, 'abc'], [456, 'def'])), 'id in ("[123, \'abc\']", "[456, \'def\']")')
        class InTest(object):
            def __str__(self): return 'test'
        self.assertEqual(str(attr('id').in_(InTest(), 1j+1)), 'id in ("test", "(1+1j)")')
        self.assertRegex(str(attr('id').in_((i for i in range(5)), (i for i in range(5)))),
                         r'id in \("<.* at 0x[0-9A-F]+>", "<.* at 0x[0-9A-F]+>"\)')

    def test_join(self):
        self.assertEqual(str(or_(attr('version') > 3, version=1)), '(version > 3 or version is 1)')
        self.assertEqual(str(and_(attr('version') > 3, version=1)), 'version > 3 and version is 1')
        self.assertEqual(str(attr('parent').has(attr('parent.name') == 'abc', name='def')), 'parent has (parent.name is "abc" and name is "def")')
        self.assertEqual(str(attr('parent').has(and_(attr('parent.name') == 'abc', name='def'))), 'parent has (parent.name is "abc" and name is "def")')
        self.assertEqual(str(attr('parent').has(or_(attr('parent.name') == 'abc', name='def'))), 'parent has ((parent.name is "abc" or name is "def"))')
        self.assertEqual(str(attr('children').any(or_(attr('name').in_('a', 'b', 'c'), name='def'))), 'children any ((name in ("a", "b", "c") or name is "def"))')
        self.assertEqual(str(attr('children').any(or_(attr('name') == 'a', attr('name') == 'b'), or_(attr('name') == 'c', attr('name') == 'd'))), 'children any ((name is "a" or name is "b") and (name is "c" or name is "d"))')

    def test_invert(self):
        self.assertEqual(str(~attr('version') == 5), 'not version is 5')
        self.assertEqual(str(not_(attr('version') == 5)), 'not version is 5')
        self.assertEqual(str(not_(attr('version') == 5, version=6)), 'not (version is 5 or version is 6)')
        self.assertEqual(str(~attr('version') > 5), 'not version > 5')
        self.assertEqual(str(~attr('id').in_(123, 'abc')), 'not id in (123, "abc")')
        self.assertEqual(str(~attr('parent.name').endswith('abc')), 'not parent.name like "%abc"')
        self.assertEqual(str(~attr('parent').has(name='abc')), 'not parent has (name is "abc")')
        self.assertEqual(str(~or_(attr('version') > 3, version=1)), 'not (version > 3 or version is 1)')
        self.assertEqual(str(~or_(~attr('version') > 3, version=1)), 'not (not version > 3 or version is 1)')
        self.assertEqual(str(not_(or_(attr('version') > 3, not_(version=5)))), 'not (version > 3 or not version is 5)')

    def test_escape(self):
        self.assertEqual(str(attr('data').like('%"value"%')), 'data like "%\\"value\\"%"')
        self.assertEqual(str(attr('episode.name') == 'The "Thing"'), 'episode.name is "The \\"Thing\\""')
        self.assertEqual(str(attr('parent.name').contains('%abc%')), 'parent.name like "%\\%abc\\%%"')
        self.assertEqual(str(attr('parent.name').startswith('%abc%')), 'parent.name like "\\%abc\\%%"')
        self.assertEqual(str(attr('parent.name').endswith('%abc%')), 'parent.name like "%\\%abc\\%"')

    def test_operators(self):
        left = attr('x') == 1
        right = attr('y') == 2
        self.assertEqual(left & right, 'x is 1 and y is 2')
        self.assertEqual(left | right, '(x is 1 or y is 2)')
        self.assertEqual(left & right, and_(left, right))
        self.assertEqual(left & str(right), and_(left, right))
        self.assertEqual(str(left) & right, and_(left, right))


class TestSelect(unittest.TestCase):

    def test_bool(self):
        self.assertTrue(bool(select('Task')))
        self.assertTrue(bool(select('')))
        self.assertFalse(bool(select(None)))

    def test_single(self):
        self.assertEqual(str(select('Task')), 'Task')

    def test_populate(self):
        self.assertEqual(str(select('Task').populate('name', 'project.name')), 'select name, project.name from Task')

    def test_where(self):
        self.assertEqual(str(select('Task').where(name='abc')), 'Task where name is "abc"')

    def test_sort(self):
        self.assertEqual(str(select('Task').sort('name')), 'Task order by name')
        self.assertEqual(str(select('Task').sort(attr('name').asc())), 'Task order by name')
        self.assertEqual(str(select('Task').sort(attr('name').ascending())), 'Task order by name')
        self.assertEqual(str(select('Task').sort(attr('name').desc())), 'Task order by name descending')
        self.assertEqual(str(select('Task').sort(attr('name').descending())), 'Task order by name descending')
        self.assertEqual(str(select('Task').order('name')), 'Task order by name')
        self.assertEqual(str(select('Task').order_by('name')), 'Task order by name')
        self.assertEqual(str(reversed(select('Task').sort('name'))), 'Task order by name descending')
        self.assertEqual(str(reversed(select('Task').sort('name')).sort('project.name')), 'Task order by name descending, project.name')

    def test_limit(self):
        self.assertEqual(str(select('Task').limit(10)), 'Task limit 10')

    def test_offset(self):
        self.assertEqual(str(select('Task').offset(10)), 'Task offset 10')

    def test_copy(self):
        query = (
            select('AssetVersion')
            .where(attr('version') > 1, attr('task.name') == 'abc')
            .offset(10)
            .limit(10)
            .populate('task.name')
            .options(page_size=10)
            .sort('version')
        )

        query.where(name='abc')
        query.offset(20)
        query.limit(20)
        query.populate('task.children')
        query.sort('task.name')

        query2 = query.populate('notes.content')
        query2.options(page_size=20)
        query = query.populate('notes.content')
        self.assertEqual(str(query), str(query2))
        self.assertEqual(query._page_size, query2._page_size)

        self.assertEqual(str(query.limit(10)), str(query2))
        self.assertNotEqual(str(query.limit(11)), str(query2))


class TestCreate(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(create('Task').values(name='new', parent_id='123')), "create Task(name='new', parent_id='123')")

    def test_copy(self):
        stmt = create('Task')
        stmt.values(name='new')
        self.assertEqual(str(stmt), str(create('Task')))


class TestUpdate(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(update('Task').where(id=123).values(name='new', parent_id='123')), "update Task where id is 123 set (name='new', parent_id='123')")

    def test_copy(self):
        stmt = update('Task').where(id=123).values(name='new').limit(1).offset(1)
        stmt2 = update('Task')
        stmt2.where(id=123)
        self.assertNotEqual(stmt._where, stmt2._where)
        stmt2.values(name='new')
        self.assertNotEqual(stmt._values, stmt2._values)
        stmt2.limit(1)
        self.assertNotEqual(stmt._limit, stmt2._limit)
        stmt2.offset(1)
        self.assertNotEqual(stmt._offset, stmt2._offset)

    def test_populate(self):
        with self.assertRaises(AttributeError):
            update('Task').populate('name')


class TestDelete(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(delete('Task').where(id=123)), "delete Task where id is 123")

    def test_limit(self):
        self.assertEqual(str(delete('Task').limit(1).offset(1)), "delete Task offset 1 limit 1")
        self.assertEqual(str(delete('Task').where(id=123).limit(1).offset(1)), "delete Task where id is 123 offset 1 limit 1")

    def test_copy(self):
        stmt = delete('Task').where(id=123).limit(1).offset(1)
        stmt2 = delete('Task')
        stmt2.where(id=123)
        self.assertNotEqual(stmt._where, stmt2._where)
        stmt2.limit(1)
        self.assertNotEqual(stmt._limit, stmt2._limit)
        stmt2.offset(1)
        self.assertNotEqual(stmt._offset, stmt2._offset)

    def test_copy(self):
        stmt = delete('Task')
        stmt.where(id=123)
        self.assertEqual(str(stmt), str(delete('Task')))

    def test_delete_component_options(self):
        stmt = delete('Component')
        delete_method = stmt.clean_components()
        delete_option = stmt.options(remove_components=True)

        self.assertTrue(delete_method._remove_components)
        self.assertTrue(delete_option._remove_components)

        delete_method2 = stmt.clean_components(False)
        delete_option2 = stmt.options(remove_components=False)

        self.assertTrue(delete_method._remove_components)
        self.assertTrue(delete_option._remove_components)
        self.assertFalse(delete_method2._remove_components)
        self.assertFalse(delete_option2._remove_components)


class TestEvent(unittest.TestCase):

    def test_all(self):
        self.assertEqual(str(event.attr('topic') == 'ftrack.update'), 'topic="ftrack.update"')
        self.assertEqual(str(event.and_(event.attr('topic') == 'ftrack.update', event.attr('source.user.username') == 'user')), 'topic="ftrack.update" and source.user.username="user"')
        self.assertEqual(str(event.or_(event.attr('topic') != 'ftrack.update', event.attr('source.user.username') == 'user')), '(topic!="ftrack.update" or source.user.username="user")')

    def test_types(self):
        self.assertEqual(str(event.attr('x') == 2), 'x=2')
        class Test(object):
            def __str__(self): return 'test'
        self.assertEqual(str(event.attr('x') == Test()), 'x="test"')


if __name__ == '__main__':
    unittest.main()
