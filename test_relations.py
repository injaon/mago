#!/usr/bin/python3.2

from mago import Field, Model, connect, UnSet, OneToMany, ManyToOne
from bson import ObjectId
import unittest
import mago
_mongo_connection = connect("__test_model")


# 1 to *
class User(Model):
    name = Field()
    addresses = OneToMany("Address", backref="user")


# * to 1
class Address(Model):
    email = Field()
    user = ManyToOne("User", backref="addresses")


class RelationsTest(unittest.TestCase):

    def tearDown(self):
        super().tearDown()
        _mongo_connection.drop_database("__test_model")
        _mongo_connection.disconnect()


    def test_relations(self):
        self.assertEqual(User.addresses.field_name, "addresses")
        self.assertEqual(User.addresses.model, Address)
        self.assertEqual(Address.user.field_name, "user")
        self.assertEqual(Address.user.model, User)

        u = User(name="injaon")
        hugo = User(name="hugo")
        home = Address(email="injaon@gmail.com")
        work = Address(email="dafuq@gmail.com")

        # 1 to *
        # get
        self.assertEqual(dict.get(u, "addresses", None), None)
        self.assertEqual(u["addresses"], [])
        first = u["addresses"]

        # set
        u["addresses"] = [home, work]
        second = u["addresses"]
        self.assertEqual(id(first), id(second))
        self.assertEqual(u["addresses"], [home, work])
        self.assertIs(home["user"], u)
        self.assertIs(work["user"], u)

        # del
        del u["addresses"]
        self.assertEqual(u["addresses"], [])
        self.assertIs(work["user"], None)
        self.assertIs(home["user"], None)

        # * to 1
        # set
        home["user"] = u
        self.assertIs(home["user"], u)
        self.assertIs(u["addresses"][0], home)

        home["user"] = hugo
        self.assertIs(home["user"], hugo)
        self.assertIs(hugo["addresses"][0], home)
        self.assertEqual(u["addresses"], [])

        # del
        del home["user"]
        self.assertEqual(hugo["addresses"], [])
        self.assertIs(home["user"], None)


        # TODO: test pesistance


if __name__ == "__main__":
    unittest.main()
