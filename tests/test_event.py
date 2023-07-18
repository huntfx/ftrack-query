import os
import unittest
import sys

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query.event import attr, and_, or_, not_


class TestComparison(unittest.TestCase):

    def test_string(self):
        self.assertEqual(str(attr('topic') == 'ftrack.update'), 'topic="ftrack.update"')
        self.assertEqual(str(attr('a.b') == 'c'), 'a.b="c"')
        self.assertEqual(str(attr('a.b') != 'c'), 'a.b!="c"')

    def test_int(self):
        self.assertEqual(str(attr('a.b') == 2), 'a.b=2')

    def test_and(self):
        self.assertEqual(str(and_(attr('topic') == 'ftrack.update', attr('source.user.username') == 'username')),
                         'topic="ftrack.update" and source.user.username="username"')
        self.assertEqual(str(and_(attr('a') > 0, b=5)), 'a>0 and b=5')

    def test_or(self):
        self.assertEqual(str(or_(attr('a') > 0, b=5)), '(a>0 or b=5)')

    def test_not(self):
        self.assertEqual(str(not_(a=5)), 'not a=5')
        self.assertEqual(str(not_(a=5, b=6)), 'not (a=5 or b=6)')
        self.assertEqual(str(not_(or_(a=5, b=6))), 'not (a=5 or b=6)')
        self.assertEqual(str(not_(and_(a=5, b=6))), 'not (a=5 and b=6)')

    def test_contains_error(self):
        with self.assertRaises(TypeError):
            'a' in attr('a')

    def test_invalid_parsing(self):
        self.assertEqual(str(attr('a') == ''), 'a=""')
        self.assertEqual(str(attr('a') == None), 'a=none')


if __name__ == '__main__':
    unittest.main()
