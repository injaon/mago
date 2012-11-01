import mago
mago.connect("foo")
import sys

class User(mago.Model):
    user = mago.Field(str)


class B:
    def __init__(self):
        self.una = 1

    def hola(self):
        print(self.una)

 # u = User.find({"user": "hola"}).first()
cur = User.find({"user": "hola"})
for c in cur:
    print(c.copy())



# u.u.hola()
# u = User.find_one()
# mad = B()
# mad.b = "as"

# u.user = "hola"
# u.u = mad
# u.save()

# User.drop()
