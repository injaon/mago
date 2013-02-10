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

    # @unittest.skip("pinto")
    def test_basic(self):
        session = mago.Session()
        self.assertEqual(len(session._bkp_pool), 0)
        self.assertEqual(len(session._pool), 0)
        self.assertEqual(len(session._states[mago.Session.DIRTY]), 0)
        self.assertEqual(len(session._states[mago.Session.NEW]), 0)
        self.assertEqual(len(session._states[mago.Session.DELETED]), 0)
        self.assertEqual(len(session._states[mago.Session.CLEAN]), 0)

        foo = Foo(field="foo")
        bar = Foo(field="bar")
        foobar = Foo(field="foobar")

        session.add(foo)
        session.add_all([foo, bar, foobar])

        self.assertTrue(foo in session._states[mago.Session.NEW])
        self.assertTrue(bar in session._states[mago.Session.NEW])
        self.assertTrue(foobar in session._states[mago.Session.NEW])
        self.assertEqual(len(session._states[mago.Session.NEW]), 3)

        self.assertTrue(isinstance(bar.id, ObjectId))
        session.close()

        # everything must be destroyed
        self.assertEqual([session._bkp_pool, session._pool,
                          session._states[mago.Session.DELETED],
                          session._states[mago.Session.NEW],
                          session._states[mago.Session.DELETED],
                          session._states[mago.Session.CLEAN]],
                         [None, None, None, None, None, None])

    # @unittest.skip("pinto")
    def test_rollback(self):
        # new in new
        Foo.remove({})
        Foo(foo="bar").save()

        session = mago.Session()
        foo = Foo(field='foo')

        session.add(foo)
        foo.field = "ups"
        self.assertFalse(foo.state is mago.Session.DIRTY)
        self.assertTrue(foo.state is mago.Session.NEW)

        session.rollback()
        self.assertFalse(foo in session._pool)
        self.assertFalse(foo.state is mago.Session.DIRTY)
        self.assertFalse(foo.state is mago.Session.NEW)

        # begin in clean
        it = Foo.find({"foo":"bar"})
        session.add_all(it)

        self.assertTrue(session is it.session)

        foo = it[0]
        self.assertTrue(foo.state is mago.Session.CLEAN)

        foo.foo = "Im so dirty (lipbite)"
        self.assertTrue(foo.state is mago.Session.DIRTY)

        session.rollback()                # rolling....

        self.assertTrue(foo.state is mago.Session.CLEAN)
        self.assertTrue(foo.id in session._pool)
        self.assertTrue(foo.foo, "bar")

        # delete something
        # session.delete(foo)
        # self.assertTrue(foo.state is mago.Session.DELETED)

        # session.rollback()
        # self.assertTrue(foo.state is mago.Session.CLEAN)

        # TODO: sup with del foo.bar

    # @unittest.skip("pinto")
    def test_track_changes(self):
        Foo(hola="man").save()
        session = mago.Session()
        it = Foo.find({"hola":"man"})
        session.add_all(it)
        foo = it[0]

        self.assertTrue(foo.state is mago.Session.CLEAN)
        foo.hola = "sd"
        self.assertTrue(foo.state is mago.Session.DIRTY)
        foo.hola = "man"
        self.assertTrue(foo.state is mago.Session.CLEAN)
        foo.mano = "bro"
        self.assertTrue(foo.state is mago.Session.DIRTY)
        del foo.mano
        self.assertTrue(foo.state is mago.Session.CLEAN)
        del foo.hola
        self.assertTrue(foo.state is mago.Session.DIRTY)

    # @unittest.skip("pinto")
    def test_foo(self):
        foo = Foo(hola="aasd").save()
        d = {}
        d[foo.id] = foo

if __name__ == "__main__":
    unittest.main()


# TODO: check session values `session` y `state`
