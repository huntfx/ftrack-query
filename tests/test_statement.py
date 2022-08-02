import os
import unittest
import sys

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import entity, select, create, update, delete


class TestSelect(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(str(select('Task')), 'select from Task')
        self.assertEqual(str(select('Task').populate('name')), 'select name from Task')

    def test_populate(self):
        self.assertEqual(str(select('Task.name')), 'select name from Task')
        self.assertEqual(str(select('Task.name')), str(select('Task').populate('name')))
        self.assertEqual(str(select('Task.parent').populate('children')), 'select parent, children from Task')
        self.assertEqual(str(select('Task.parent', 'Task.children.name')), 'select parent, children.name from Task')
        with self.assertRaises(ValueError):
            select('Task.name', 'AssetVersion.name')

    def test_subquery(self):
        self.assertEqual(
            str(select('Task.name').where(entity.parent.id.in_(select('Shot').where(name='My Shot')))),
            'select name from Task where parent.id in (select id from Shot where name is "My Shot")'
        )
        self.assertEqual(
            str(select('Task.name').where(entity.parent.id.in_(select('Shot.id').where(name='My Shot')))),
            'select name from Task where parent.id in (select id from Shot where name is "My Shot")'
        )
        (
            str(select('Task.name').where(entity.parent.name.in_(select('Shot.name').where(name='My Shot')))),
            'select name from Task where parent.name in (select name from Shot where name is "My Shot")'
        )


class TestCreate(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(str(create('Task').values(name='New Task')), "create Task(name='New Task')")

    def test_where(self):
        with self.assertRaises(AttributeError):
            create('Task').where(name='New Task')


class TestUpdate(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(str(update('Task')), 'update Task set ()')
        self.assertEqual(str(update('Task').where(name='Old Task').values(name='New Task')),
                         "update Task where name is \"Old Task\" set (name='New Task')")

    def test_populate(self):
        with self.assertRaises(AttributeError):
            update('Task').select('name')


class TestDelete(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(str(delete('Task')), 'delete Task')
        self.assertEqual(str(delete('Task').where(name='My Task').limit(1)),
                         'delete Task where name is "My Task" limit 1')


if __name__ == '__main__':
    unittest.main()
