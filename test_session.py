#!/usr/bin/python3.2
from bson import ObjectId
import mago
import unittest

class Bar(object):
    bar = "open bar"
    def __init__(self):
        self.close = "almost a model"

class Foo(mago.Model):
    field = mago.Field()

class MagoModelTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._mongo_connection = mago.connect("__test_model")
        Foo.remove({})

    def tearDown(self):
        super().tearDown()
        self._mongo_connection.drop_database("__test_model")
        self._mongo_connection.disconnect()

    def test_basic(self):
        session = mago.Session()
        self.assertEqual(len(session._bkp_pool), 0)
        self.assertEqual(len(session._pool), 0)
        self.assertEqual(len(session._dirty), 0)
        self.assertEqual(len(session._new), 0)
        self.assertEqual(len(session._deleted), 0)
        self.assertEqual(len(session._clean), 0)

        foo = Foo(field="foo")
        bar = Foo(field="bar")
        foobar = Foo(field="foobar")

        session.add(foo)
        session.add_all([foo, bar, foobar])

        self.assertTrue(foo in session._new)
        self.assertTrue(bar in session._new)
        self.assertTrue(foobar in session._new)
        self.assertEqual(len(session._new), 3)

        self.assertTrue(isinstance(bar.id, ObjectId))

        session.close()

        # everything must be destroyed
        self.assertEqual([session._bkp_pool, session._pool, session._dirty,
                         session._new, session._deleted, session._clean],
                         [None, None, None, None, None, None])

    def test_roolback(self):
        session = mago.Session()
        foo = Foo(field='foo')

        session.add(foo)
        foo.field = "ups"
        self.assertFalse(foo in session._dirty)

        session.rollback()
        self.assertFalse(foo in session._pool)


if __name__ == "__main__":
    unittest.main()
