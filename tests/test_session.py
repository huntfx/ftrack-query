import os
import unittest
import sys

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import FTrackQuery, exception, select


class TestSession(unittest.TestCase):

    def setUp(self):
        self.session = FTrackQuery(debug=True, page_size=100)

    def test_session(self):
        query_session = self.session.select('Task')
        query_no_session = select('Task')

        self.assertNotEqual(query_no_session._session, query_session._session)
        self.assertEqual(query_no_session.options(session=self.session)._session, query_session._session)

    def test_page_size(self):
        query = self.session.select('Task')
        self.assertEqual(query._page_size, 100)
        query.options(page_size=50)
        self.assertEqual(query._page_size, 100)
        query = query.options(page_size=50)
        self.assertEqual(query._page_size, 50)

        os.environ['FTRACK_API_PAGE_SIZE'] = '10'
        self.assertEqual(FTrackQuery(debug=True).page_size, 10)
        self.assertEqual(FTrackQuery(debug=True, page_size=100).page_size, 100)
        del os.environ['FTRACK_API_PAGE_SIZE']


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
