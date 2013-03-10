#!/usr/bin/python3.2
import mago
import unittest

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

    def test_basic_usage(self):
        Foo(field="hoa").save()
        cursor = Foo.find({"field":"hoa"})

        self.assertEqual(cursor.count(), 1)
        cursor[0]
        self.assertEqual(cursor.count(), 1)


if __name__ == "__main__":
    unittest.main()
