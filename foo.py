import mago
mago.connect("leviathan")
import sys

class User(mago.Model):
    user = mago.Field(str)


u = User()


# u["user"] = "1"
u["field"] = "1"
# print(u.user)
print(u["field"])


sys.exit(0)


print(u.user)
u.user = "haaaa"
print(u.user)
# print(u["user"])



# print(u["user"])
# print(u["holaa"])

print("copy >> ", u.copy())

# u.holaa = "hola"
# print(u.holaa)

# print("copy >> ", u.copy())


# u["holaa"] = "holaaaaa"
# print(u.holaa)
# print("copy >> ", u.copy())


sys.exit(0)


# u.chau = "cahu"

print(u.chau)
print(u.copy())


# print(User.find().count())
sys.exit(0)


User.drop()
input("c....")
User.create(hola="dd")

sandb


u = User()
u.user = "viejo1"
u.save()

print(u.copy())
input("c....")

# u.user = 1
u.update_sync(maaan="asdasd")
print(u.copy())
input("c....")

u.delete()
print(u.copy())

