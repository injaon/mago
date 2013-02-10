#!/usr/bin/python3.2
""" Various tests for the Model class """

from mago import Field, ReferenceField, Model, connect, UnSet
from bson import ObjectId
import unittest

class Bar(object):
    bar = "open bar"
    def __init__(self):
        self.close = "almost a model"

class NotAModel(object):
    class_attr = "class...ic"

    def __init__(self):
        self.obj_attr = "objective"
        self._so = Bar()

    def method(self):
        return "just a {wait_for_it}".format(wait_for_it=self.obj_attr)

class Foo(Model):

    field = Field()
    default = Field(default="default")
    _private_field = Field()
    # callback = Field(get_callback=lambda x, y: "foo",
    #                  set_callback=lambda x, y: "bar")
    # reference = ReferenceField(Ref)


class Small(Model):
    foo = Field()


class MagoModelTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self._mongo_connection = connect("__test_model")
        Foo.remove({})

    def tearDown(self):
        super().tearDown()
        self._mongo_connection.drop_database("__test_model")
        self._mongo_connection.disconnect()

    def test_model_fields_init(self):
        """ Test that the model properly retrieves the fields """
        foo = Foo()
        self.assertTrue("field" in foo._fields.keys())
        self.assertTrue("default" in foo._fields.keys())
        self.assertTrue("_private_field" in foo._fields.keys())
        # self.assertTrue("callback" in foo._fields.keys())
        # self.assertTrue("reference" in foo._fields.keys())

    def test_basic_operations(self):
        foo = Foo(foo="bar")
        self.assertEqual(foo.id, UnSet)
        before_saved = foo.copy()
        foo.save()

        self.assertEqual(type(foo.id), ObjectId)

        same_foo = Foo.find_one({"foo": "bar"})
        self.assertEqual(foo, same_foo)
        self.assertEqual(foo.id, same_foo.id)
        self.assertEqual(foo.copy(), same_foo.copy())

        for k, v in before_saved.items():
            self.assertEqual(same_foo[k], v)
            self.assertEqual(foo[k], v)
        self.assertEqual(len(foo), len(same_foo), len(before_saved) + 1)

    def test_custom_obj_store(self):
        foo = Foo()    # a model
        foo.custom = "custom"
        obj = NotAModel()
        foo.obj = obj
        foo.save()
        other_foo = Foo.find_one({"custom" : "custom"})

        self.assertEqual(foo, other_foo)

        # test types
        self.assertEqual(type(foo.obj), type(other_foo.obj))
        self.assertEqual(type(foo.obj), type(obj))
        self.assertEqual(type(foo.obj), NotAModel)

        # test object
        self.assertEqual(foo.obj.method(), other_foo.obj.method())
        self.assertEqual(foo.obj.method(), obj.method())

        self.assertEqual(foo.obj._so.close, other_foo.obj._so.close)
        self.assertEqual(foo.obj._so.__class__.bar,
                         other_foo.obj._so.__class__.bar)
        self.assertEqual(NotAModel.class_attr, other_foo.obj.__class__.class_attr)
        self.assertEqual(len(foo.copy()), len(other_foo.copy()))

    def test_queries(self):
        Small.remove({})
        Small(foo="foo").save()
        Small(foo="bar").save()
        Small(foo="foobar").save()

        cursor = Small.find({"foo":"bara"})
        self.assertEqual(cursor.count(), 0)
        cursor = Small.find({"foo":"bar"})
        self.assertEqual(cursor.count(), 1)
        self.assertEqual(type(cursor[0]), Small)





    # def test_null_reference(self):
    #     foo = Foo()
    #     foo.reference = None
    #     self.assertEqual(foo.reference, None)

    # def test_reference_subclass(self):
    #     foo = Foo()
    #     child_ref = ChildRef(_id="testing")  # hardcoding id
    #     foo.reference = child_ref
    #     self.assertEqual(foo["reference"].id, child_ref.id)

    # def test_inheritance(self):
    #     self.assertEqual(Person._get_name(), Child._get_name())
    #     self.assertEqual(Person._get_name(), Infant._get_name())
    #     person = Person()
    #     self.assertTrue(isinstance(person, Person))
    #     self.assertTrue(person.walk())
    #     self.assertEqual(person.role, "person")
    #     with self.assertRaises(AttributeError):
    #         person.crawl()
    #     child = Person(role="child")
    #     self.assertTrue(isinstance(child, Child))
    #     child2 = Child()
    #     self.assertTrue(child2.walk())
    #     self.assertEqual(child2.role, "child")
    #     child3 = Child(role="person")
    #     self.assertTrue(isinstance(child3, Person))

    #     infant = Infant()
    #     self.assertTrue(isinstance(infant, Infant))
    #     self.assertEqual(infant.age, 3)
    #     self.assertTrue(infant.crawl())
    #     self.assertFalse(infant.walk())
    #     infant2 = Person(age=3, role="infant")
    #     self.assertTrue(isinstance(infant2, Infant))



if __name__ == "__main__":
    unittest.main()
