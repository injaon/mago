"""
A variety of tests to cover the majority of the functionality
in mago Fields.
"""

import unittest
from mago import Field, ReferenceField, connect, Model, EnumField, ConstantField
from mago.field import FieldError

class Base(object):
    pass


class Sub(Base):
    pass


class MagoFieldTests(unittest.TestCase):

    def setUp(self):
        super(MagoFieldTests, self).setUp()
        self._mongo_connection = connect("__test_change_field_name")

    def tearDown(self):
        super(MagoFieldTests, self).tearDown()
        self._mongo_connection.drop_database("__test_change_field_name")
        self._mongo_connection.disconnect()

    def test_field(self):

        class MockModel(Model):
            field = Field(str)
            typeless = Field()
            required = Field(required=True)
            default = Field(int, default=4)
            # reference = ReferenceField(Base)

        mock = MockModel()

        # checks the unassigned values
        self.assertEqual(NotImplemented, mock.field)
        self.assertEqual(NotImplemented, mock.other)
        self.assertEqual(NotImplemented, mock["other"])
        self.assertEqual(NotImplemented, mock["field"])

        # check setters
        mock.field = "testing"
        mock.other = "schemaless"

        # test getters
        self.assertEqual("schemaless", mock["other"])
        self.assertEqual("testing", mock["field"])
        self.assertEqual("schemaless", mock.other)
        self.assertEqual("testing", mock.field)

        # test default
        self.assertEqual(mock.default, 4)
        self.assertEqual(mock["default"], 4)

        # test type constraint
        self.assertRaises(FieldError, setattr, mock, "field", 5)
        self.assertRaises(FieldError, setattr, mock, "field", object())
        self.assertRaises(FieldError, setattr, mock, "default", "object()")

        # test typeless
        mock.typeless = 5
        mock.typeless = "string"

        # test required
        self.assertRaises(FieldError, mock.save)

    def test_enum_field(self):
        """ Test the enum field """
        class EnumModel(Model):
            field = EnumField((1, 3, "what"))

        mock = EnumModel()
        mock.field = 3
        self.assertEqual(mock.field, 3)

        self.assertRaises(FieldError, setattr, mock, "field", 2)

    def test_const_field(self):
        class ConstField(Model):
            field = ConstantField(str)

        mock = ConstField()

        self.assertEqual(mock.field, NotImplemented)
        mock.field = "testing"
        self.assertEqual(mock.field, "testing")
        mock.field = "keep testing"
        self.assertEqual(mock.field, "keep testing")

        mock.save()
        self.assertEqual(mock.field, "keep testing")
        self.assertRaises(FieldError, setattr, mock, "field", "I'm jumping!")

    # def test_change_field_name(self):
    #     """It should allow an override of a field's name."""
    #     class MockModel(Model):
    #         abbreviated = Field(str, field_name="abrv")
    #         long_name = Field(str, field_name="ln", required=True)
    #         regular = Field(str, required=True)

    #     model = MockModel(
    #         abbreviated=u"lorem ipsum", long_name=u"malarky", regular=u"meh.")

    #     # Check the model's dictionary.
    #     self.assertTrue("abrv" in model)
    #     # Access by friendly name.
    #     self.assertEqual(u"lorem ipsum", model.abbreviated)
    #     # No access by field_name.
    #     self.assertRaises(AttributeError, getattr, model, "abrv")

    #     # Test save.
    #     model.save(safe=True)

    #     # Test search.
    #     fetched = MockModel.search(abbreviated=u"lorem ipsum")
    #     self.assertIsNotNone(fetched)
    #     fetched = MockModel.search(long_name=u"malarky")
    #     self.assertIsNotNone(fetched)

    #     # Test updates with long names.
    #     model.update(abbreviated=u"dolor set")
    #     self.assertEqual(u"dolor set", model.abbreviated)
    #     fetched = MockModel.search(abbreviated=u"dolor set")
    #     self.assertEqual(1, fetched.count())

    #     model.update(long_name=u"foobar")
    #     self.assertEqual(u"foobar", model.long_name)
    #     fetched = MockModel.search(long_name=u"foobar")
    #     self.assertEqual(1, fetched.count())

    #     # Test updates with short names.
    #     MockModel.update({}, {"$set": {"abrv": u"revia"}})
    #     fetched = MockModel.find_one({"abrv": "revia"})
    #     self.assertEqual(fetched.abbreviated, "revia")

    #     # Test finds with short names.
    #     fetched = MockModel.find({"ln": "foobar"})
    #     self.assertEqual(1, fetched.count())
    #     fetched = fetched.first()
    #     self.assertEqual(u"revia", fetched.abbreviated)

    #     # Test search on regular fields.
    #     fetched = MockModel.search(regular=u"meh.")
    #     self.assertEqual(1, fetched.count())



    # def test_default_field(self):
    #     """ Test that the default behavior works like you'd expect. """
    #     class TestDefaultModel(Model):
    #         field = Field()  # i.e. no default value

    #     entry = TestDefaultModel()
    #     self.assertFalse("field" in entry)

    #     self.assertEqual(None, entry.field)
    #     self.assertFalse("field" in entry)

    #     class TestDefaultModel2(Model):
    #         field = Field(default=None)

    #     entry2 = TestDefaultModel2()
    #     self.assertTrue("field" in entry2)
    #     self.assertEqual(None, entry2.field)
    #     self.assertEqual(None, entry2["field"])

    #     entry3 = TestDefaultModel2(field="foobar")
    #     self.assertEqual("foobar", entry3.field)
    #     self.assertEqual("foobar", entry3["field"])

if __name__ == "__main__":
    unittest.main()
