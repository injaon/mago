#!/usr/bin/python3.2
from bson import ObjectId
import mago
import mago.transaction as tran
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
        # self._mongo_connection.drop_database("__test_model")
        self._mongo_connection = mago.connect("__test_model")
        Foo.collection().remove({})
        tran.Transaction.collection().remove({})
    # def tearDown(self):
    #     super().tearDown()
    #     self._mongo_connection.drop_database("__test_model")
    #     self._mongo_connection.disconnect()

    def test_insert(self):
        foo = Foo()
        foo["hola"] = "mundo"
        # test insert initial
        t = tran.Transaction()
        t.insert(foo)
        t.save()

        tran.recovery()
        same_foo = Foo(**Foo.collection().find({"_id" : foo.id})[0])
        self.assertEqual(foo, same_foo)
        foo.delete()
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

        # test insert pending
        t = tran.Transaction()
        t.insert(foo)
        t.save()
        t._to_pending()

        tran.recovery()
        same_foo = Foo(**Foo.collection().find({"_id" : foo.id})[0])
        self.assertEqual(foo, same_foo)
        foo.delete()
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

        # test insert commit
        t = tran.Transaction()
        t.insert(foo)
        t.save()
        t._to_pending()
        t._to_commit()

        tran.recovery()
        same_foo = Foo(**Foo.collection().find({"_id" : foo.id})[0])
        self.assertEqual(foo, same_foo)
        foo.delete()
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

    def test_update(self):
        foo = Foo()
        foo["hola"] = "mundo"
        foo.save()
        foo["hola"] = "world"
        # test initial
        t = tran.Transaction()
        t.update(foo)
        t.save()

        tran.recovery()
        same_foo = Foo(**Foo.collection().find({"hola" : "world"})[0])
        self.assertEqual(foo, same_foo)
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

        # test pending
        foo["hola"] = "monde"
        t = tran.Transaction()
        t.update(foo)
        t.save()
        t._to_pending()

        tran.recovery()
        same_foo = Foo(**Foo.collection().find({"hola" : "monde"})[0])
        self.assertEqual(foo, same_foo)
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

        # test commit
        foo["hola"] = "mondo"
        t = tran.Transaction()
        t.update(foo)
        t.save()
        t._to_pending()
        t._to_commit()

        tran.recovery()
        same_foo = Foo(**Foo.collection().find({"hola" : "mondo"})[0])
        self.assertEqual(foo, same_foo)
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

    def test_remove(self):
        foo = Foo()
        foo["hola"] = "mundo"
        foo.save()
        # test initial
        t = tran.Transaction()
        t.remove(foo)
        t.save()

        tran.recovery()
        self.assertRaises(IndexError, lambda : \
                         Foo.collection().find({"hola" : "mundo"})[0])
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

        # test pending
        foo["hola"] = "monde"
        foo.save()
        t = tran.Transaction()
        t.remove(foo)
        t.save()
        t._to_pending()

        tran.recovery()
        self.assertRaises(IndexError, lambda : \
                         Foo.collection().find({"hola" : "monde"})[0])
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])

        # test commit
        foo["hola"] = "mondo"
        foo.save()
        t = tran.Transaction()
        t.remove(foo)
        t.save()
        t._to_pending()
        t._to_commit()

        tran.recovery()
        self.assertRaises(IndexError, lambda : \
                         Foo.collection().find({"hola" : "mondo"})[0])
        self.assertRaises(IndexError, lambda : \
                          tran.Transaction.collection().find()[0])


if __name__ == "__main__":
    unittest.main()
