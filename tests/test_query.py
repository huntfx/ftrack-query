import os
import unittest
import sys

import arrow

sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)).rsplit(os.path.sep, 1)[0])
from ftrack_query import *


class TestComparison(unittest.TestCase):
    def test_string(self):
        self.assertEqual(str(entity.a.b=='c'), 'a.b is "c"')

    def test_number(self):
        self.assertEqual(str(entity.a.b>1), 'a.b > 1')
        self.assertEqual(str(entity.a.b<=0), 'a.b <= 0')
        self.assertEqual(str(entity.a.b==10), 'a.b is 10')

    def test_none(self):
        self.assertEqual(str(entity.a.b==None), 'a.b is none')
        self.assertEqual(str(entity.a.b!=None), 'a.b is_not none')

    def test_like(self):
        self.assertEqual(str(entity.a.b.like('% value')), 'a.b like "% value"')
        self.assertEqual(str(entity.a.b.not_like('% value')), 'a.b not_like "% value"')

    def test_time(self):
        now = arrow.now()
        self.assertEqual(str(entity.a.b.after(now)), 'a.b after "{}"'.format(now))

    def test_scalar(self):
        self.assertEqual(str(entity.a.b.has(c='d')), 'a.b has (c is "d")')
        self.assertEqual(str(entity.a.b.has(entity.c>0)), 'a.b has (c > 0)')

    def test_collection(self):
        self.assertEqual(str(entity.a.b.any(c='d')), 'a.b any (c is "d")')
        self.assertEqual(str(entity.a.b.any(entity.c>0)), 'a.b any (c > 0)')

    def test_in(self):
        self.assertEqual(str(entity.a.b.in_('select id from User')), 'a.b in (select id from User)')
        self.assertEqual(str(entity.a.b.in_('c', 'd', 'e')), 'a.b in ("c", "d", "e")')
        self.assertEqual(str(entity.a.b.in_('c')), 'a.b in ("c")')
        # TODO: Check if ints work with the API

    def test_not(self):
        self.assertEqual(str(entity.a.b!='c'), 'a.b is_not "c"')
        self.assertEqual(str(~entity.a.b=='c'), 'not a.b is "c"')
        self.assertEqual(str(not_(entity.a.b=='c')), 'not a.b is "c"')
        self.assertEqual(str(entity.a.b.not_in('c', 'd', 'e')), 'not a.b in ("c", "d", "e")')

    def test_and(self):
        self.assertEqual(str(and_(entity.a>0, b=5)), 'a > 0 and b is 5')

    def test_or(self):
        self.assertEqual(str(or_(entity.a>0, b=5)), '(a > 0 or b is 5)')

    def test_complex_and_or(self):
        self.assertEqual(str(and_(
            ~or_(a=0, b=1), c=2
        )), 'not (a is 0 or b is 1) and c is 2')
        self.assertEqual(str(or_(
            ~and_(a=0, b=1), c=2
        )), '(not (a is 0 and b is 1) or c is 2)')

    def test_complex_inverse(self):
        self.assertEqual(str(or_(
            ~and_(
                or_(a=1, b=2),
                ~or_(c=3, d=4),
            ), e=5
        )), '(not ((a is 1 or b is 2) and not (c is 3 or d is 4)) or e is 5)')

    def test_has(self):
        self.assertIn(
            str(entity.a.has(b=1, c=2)),
            ('a has (b is 1 and c is 2)', 'a has (c is 2 and b is 1)'),
        )
        # TODO: Remove brackets for this case
        self.assertIn(
            str(~entity.a.has(b=1, c=2)),
            ('not (a has (b is 1 and c is 2))', 'not (a has (c is 2 and b is 1))'),
        )

    def test_any(self):
        self.assertIn(
            str(entity.a.any(b=1, c=2)),
            ('a any (b is 1 and c is 2)', 'a any (c is 2 and b is 1)'),
        )
        self.assertIn(
            str(~entity.a.any(b=1, c=2)),
            ('not (a any (b is 1 and c is 2))', 'not (a any (c is 2 and b is 1))'),
        )

    def test_sort(self):
        self.assertEqual(str(entity.a.desc()), 'a descending')
        self.assertEqual(str(entity.a.desc), 'a.desc')
        self.assertEqual(str(entity.a.b.asc()), 'a.b ascending')

    def test_call(self):
        self.assertEqual(str(entity.a('value')), 'a is "value"')
        self.assertEqual(str(entity.a.b(1)), 'a.b is 1')

    def test_str_functions(self):
        self.assertEqual(str(entity.value.startswith('value')), 'value like "value%"')
        self.assertEqual(str(entity.value.endswith('value')), 'value like "%value"')

    def test_quotation_escape(self):
        self.assertEqual(str(entity.value.like('%"value"%')), r'value like "%\"value\"%"')

    def test_percent_escape(self):
        self.assertEqual(str(entity.value.startswith('a%b')), r'value like "a\%b%"')
        self.assertEqual(str(entity.value.like('a%b')), r'value like "a%b"')

    def test_contains_error(self):
        with self.assertRaises(TypeError):
            'a' in event.a


class TestSessionComparison(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery()

    def tearDown(self):
        self.session.close()

    def test_id_remap(self):
        schema = self.session.ProjectSchema.first()
        self.assertEqual(
            str(self.session.Project.where(project_schema=schema)),
            'Project where project_schema.id is "{}"'.format(schema['id'])
        )

    def test_id_remap_in(self):
        schema = self.session.ProjectSchema.first()
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.in_(schema))),
            'Project where project_schema.id in ("{}")'.format(schema['id'])
        )

    def test_id_remap_in_multiple(self):
        schema = self.session.ProjectSchema.first()
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.in_(schema, schema))),
            'Project where project_schema.id in ("{s}", "{s}")'.format(s=schema['id'])
        )


class TestQueryComparison(unittest.TestCase):
    def setUp(self):
        self.session = FTrackQuery(debug=True)

    def test_in(self):
        query = self.session.ProjectSchema.where(name='My Schema')
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.in_(query))),
            'Project where project_schema.id in (select id from ProjectSchema where name is "My Schema")',
        )
        with self.assertRaises(ValueError):
            str(self.session.Project.where(entity.project_schema.in_(query, query)))

    def test_has_simple(self):
        query = self.session.ProjectSchema.where(name='My Schema')
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.has(query))),
            'Project where project_schema has (name is "My Schema")',
        )

    def test_has_complex(self):
        query = self.session.ProjectSchema.where(~entity.project.has(name='Invalid Project'), name='My Schema')
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.has(query))),
            'Project where project_schema has (not project has (name is "Invalid Project") and name is "My Schema")',
        )

    def test_has_multiple(self):
        query1 = self.session.ProjectSchema.where(~entity.project.has(name='Invalid Project'))
        query2 = self.session.ProjectSchema.where(name='My Schema')
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.has(query1, query2))),
            'Project where project_schema has (not project has (name is "Invalid Project") and name is "My Schema")',
        )
        self.assertEqual(
            str(self.session.Project.where(entity.project_schema.any(query1, query2))),
            'Project where project_schema any (not project has (name is "Invalid Project") and name is "My Schema")',
        )

    def test_equals(self):
        with self.assertRaises(NotImplementedError):
            entity.value == self.session.ProjectSchema.where(name='My Schema')
        with self.assertRaises(NotImplementedError):
            entity.value != self.session.ProjectSchema.where(name='My Schema')



if __name__ == '__main__':
    unittest.main()
