import mago
mago.connect("leviathan")


# class A(object):
#     uno = "1"

# print(getattr(A, "un", "noaa"))

# asd

class User(mago.Model):
    user = mago.Field(str)


u = User()
u.user = "viejo1"
u.save()

print(u.copy())

input("c....")

# u.user = 1
u.update_sync(user=1)

print(u.copy())


