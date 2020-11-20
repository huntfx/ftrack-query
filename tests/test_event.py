import os
import unittest
import sys

sys.path.append(os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import *


class TestComparison(unittest.TestCase):
    def test_string(self):
        self.assertTrue(event.a.b=='c', 'a.b="c"')
        self.assertTrue(event.a.b!='c', 'a.b!="c"')

    def test_int(self):
        self.assertTrue(event.a.b==2, 'a.b=2')

    def test_and(self):
        self.assertEquals(str(and_(event.a>0, b=5)), 'a>0 and b is 5')

    def test_or(self):
        self.assertEquals(str(or_(event.a>0, b=5)), '(a>0 or b is 5)')


if __name__ == '__main__':
    unittest.main()
