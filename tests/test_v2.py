import os
import unittest
import sys

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import FTrackQuery, exception, attr, entity, select


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
            'select name from Task where parent in (select id from Shot where name is "My Shot")'
        )


class TestAttr(unittest.TestCase):
    def test_main(self):
        self.assertEqual(str(~attr('parent.val').in_(range(5))), str(~entity.parent.val.in_(range(5))))
        self.assertNotEqual(str(~attr('parent.val').in_(range(5))), str(entity.parent.val.in_(range(5))))

    def test_in_empty(self):
        self.assertEqual(attr('task').in_(), 'task in ()')


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True, page_size=100)

    def test_session(self):
        query_session = self.session.select('Task')
        query_no_session = select('Task')

        self.assertNotEqual(query_no_session._session, query_session._session)
        self.assertEqual(query_no_session.options(session=self.session)._session, query_session._session)

    def test_page_size(self):
        query = self.session.select('Task').options(page_size=50)
        self.assertEqual(query._page_size, 50)


class TestException(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True)

    def testUnboundSession(self):
        with self.assertRaises(exception.UnboundSessionError):
            select('Task').first()

        with self.assertRaises(exception.UnboundSessionError):
            self.session.select('Task').options(session=None).first()


if __name__ == '__main__':
    unittest.main()
