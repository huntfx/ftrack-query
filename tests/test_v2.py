import os
import unittest
import sys

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import FTrackQuery, attr, entity


class TestSelect(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True)

    def test_basic(self):
        self.assertEqual(str(self.session.select('Task')), 'select from Task')
        self.assertEqual(str(self.session.select('Task').populate('name')), 'select name from Task')

    def test_populate(self):
        self.assertEqual(str(self.session.select('Task.name')), 'select name from Task')
        self.assertEqual(str(self.session.select('Task.name')), str(self.session.select('Task').populate('name')))
        self.assertEqual(str(self.session.select('Task.parent').populate('children')), 'select parent, children from Task')
        self.assertEqual(str(self.session.select('Task.parent', 'Task.children.name')), 'select parent, children.name from Task')
        with self.assertRaises(ValueError):
            self.session.select('Task.name', 'AssetVersion.name')

    def test_subquery(self):
        self.assertEqual(
            str(self.session.select('Task.name').where(attr('parent_id').in_(self.session.select('Shot.id').where(name='My Shot')))),
            'select name from Task where parent_id in (select id from Shot where name is "My Shot")'
        )
        self.assertEqual(
            str(self.session.select('Task.name').where(attr('parent').in_(self.session.select('Shot').where(name='My Shot')))),
            'select name from Task where parent.id in (select id from Shot where name is "My Shot")'
        )


class TestInsert(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True)

    def test_basic(self):
        self.assertEqual(str(self.session.insert('Task').values(name='New Task')), "insert Task(name='New Task')")

    def test_where(self):
        with self.assertRaises(AttributeError):
            self.session.insert('Task').where(name='New Task')


class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True)

    def test_basic(self):
        self.assertEqual(str(self.session.update('Task')), 'update Task set ()')
        self.assertEqual(str(self.session.update('Task').where(name='Old Task').values(name='New Task')),
                         "update Task where name is \"Old Task\" set (name='New Task')")

    def test_populate(self):
        with self.assertRaises(AttributeError):
            self.session.update('Task').select('name')


class TestDelete(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True)

    def test_basic(self):
        self.assertEqual(str(self.session.delete('Task')), 'delete Task')
        self.assertEqual(str(self.session.delete('Task').where(name='My Task').limit(1)),
                         'delete Task where name is "My Task" limit 1')


class TestAttr(unittest.TestCase):
    def test_main(self):
        self.assertEqual(str(~attr('parent.val').in_(range(5))), str(~entity.parent.val.in_(range(5))))
        self.assertNotEqual(str(~attr('parent.val').in_(range(5))), str(entity.parent.val.in_(range(5))))


if __name__ == '__main__':
    unittest.main()
