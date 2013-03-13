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
        Foo.collection().remove({})

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
        self.assertTrue(foo["session"] is mago.UnSet)
        self.assertTrue(isinstance(foo["_id"], ObjectId))

        session.add_all([foo, bar, foobar])

        self.assertTrue(foo in session._states[mago.Session.NEW])
        self.assertTrue(bar in session._states[mago.Session.NEW])
        self.assertTrue(foobar in session._states[mago.Session.NEW])
        self.assertEqual(len(session._states[mago.Session.NEW]), 3)

        self.assertTrue(isinstance(bar.id, ObjectId))
        session.close()

        # everything must be destroyed
        self.assertEqual([session._bkp_pool, session._pool, session._states],
                         [None, None, None])

    # @unittest.skip("pinto")
    def test_rollback(self):
        Foo.collection().remove({})
        Foo(foo="bar").save()

        # test news
        session = mago.Session()
        foo = Foo(field='foo')

        session.add(foo)
        foo['field'] = "ups"
        foo['field'] = "I did it again"

        session.rollback()
        self.assertTrue(foo._session is None)

        # begin in clean
        it = Foo.find({"foo":"bar"})
        session.add_all(it)
        foo = it[0]
        foo['foo'] = "Im so dirty (lipbite)"
        session.rollback()                # rolling....

        self.assertTrue(foo._state is mago.Session.CLEAN)
        self.assertTrue(foo['foo'], "bar")

        # delete a clean
        session.delete(foo)
        session.rollback()
        self.assertTrue(foo._state is mago.Session.CLEAN)

        # delete a dirty
        foo['foo'] = "i'm dirty"
        session.delete(foo)
        session.rollback()
        self.assertTrue(foo['foo'], "bar")
        self.assertTrue(foo._state is mago.Session.CLEAN)

        # TODO: fix this
        # Session.delete(foo)
        # foo.dirty = "very"
        # Session.rollback()
        # self.assertTrue(foo['foo'], "bar")
        # self.assertTrue(foo._state is mago.Session.CLEAN)

    # @unittest.skip("pinto")
    def test_track_changes(self):
        Foo(hola="man").save()
        session = mago.Session()

        # test clean models {{{
        it = Foo.find({"hola":"man"})
        session.add_all(it)
        foo = it[0]

        self.assertTrue(foo._state is mago.Session.CLEAN)
        foo['hola'] = "sd"
        self.assertTrue(foo._state is mago.Session.DIRTY)
        foo['hola'] = "man"
        self.assertTrue(foo._state is mago.Session.CLEAN)
        foo['mano'] = "bro"
        self.assertTrue(foo._state is mago.Session.DIRTY)
        del foo['mano']
        self.assertTrue(foo._state is mago.Session.CLEAN)
        del foo['hola']
        self.assertTrue(foo._state is mago.Session.DIRTY)
        foo['hola'] = "man"
        self.assertTrue(foo._state is mago.Session.CLEAN)
        session.delete(foo)
        self.assertTrue(foo._state is mago.Session.DELETED)

        # }}}
        # test new object {{{
        foo = Foo(field='foo')
        session.add(foo)
        self.assertTrue(foo._state is mago.Session.NEW)
        foo['foo'] = "I'm so dirty"
        self.assertTrue(foo._state is mago.Session.NEW)
        del foo['foo']
        self.assertTrue(foo._state is mago.Session.NEW)
        session.delete(foo)
        self.assertTrue(foo._session is None)
        self.assertTrue(foo._state is None)


if __name__ == "__main__":
    unittest.main()


# TODO: check session values `session` y `state`
