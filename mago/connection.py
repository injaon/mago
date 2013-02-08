""" The wrapper for pymongo's connection stuff. """
from bson.objectid import ObjectId
from pymongo import Connection as PyConnection
from pymongo.errors import ConnectionFailure
from pymongo.collection import Collection as PyCollecton
import urllib.parse as urlparse


class Connection(object):
    """
    This just caches a pymongo connection and adds
    a few shortcuts.
    """

    _instance = None
    connection = None
    _host = None
    _port = None
    _database = None

    @classmethod
    def instance(cls):
        """ Retrieves the shared connection. """
        if not cls._instance:
            cls._instance = Connection()
        return cls._instance

    @classmethod
    def connect(cls, database=None, *args, **kwargs):
        """
        Wraps a pymongo connection.
        TODO: Allow some of the URI stuff.
        """
        if "uri" in kwargs:
            uri = kwargs.pop("uri")
            parsed_uri = urlparse.urlparse(uri)
            # allows overriding db name
            database = database or parsed_uri.path.replace("/", "")
            new_uri_parts = [p for p in parsed_uri]
            if len(new_uri_parts) > 2:
                # this is...hacky -- would love a better way to
                # augment the urlparse results to ensure that
                # Mago controls the dbname
                new_uri_parts[2] = "/"
            parsed_uri = tuple(new_uri_parts)
            kwargs["host"] = urlparse.urlunparse(parsed_uri)
        elif not database:
            raise TypeError("A database name or uri is required to connect.")
        conn = cls.instance()
        conn._database = database
        conn.connection = PyConnection(*args, **kwargs)
        return conn.connection

    def get_database(self, database=None):
        """ Retrieves a database from an existing connection. """
        if not self.connection:
            raise ConnectionFailure('No connection')
        if not database:
            if not self._database:
                raise Exception('No database submitted')
            database = self._database
        return self.connection[database]

    def get_collection(self, collection, database=None):
        """ Retrieve a collection from an existing connection. """
        return self.get_database(database=database)[collection]


def connect(*args, **kwargs):
    """
    Initializes a connection and the database. It returns
    the pymongo connection object so that end_request, etc.
    can be called if necessary.
    """
    return Connection.connect(*args, **kwargs)


class Session(object):
    """It implements the unit of work and transaction"""

    def __init__(self, autocommit=True):
        self._autocommit = autocommit
        self._bkp_pool = {}  # oid => dict
        self._pool = {}  # ObjectId => (obj, state_set)
        self._dirty = set()
        self._new = set()
        self._deleted = set()
        self._clean = set()

    def add(self, model, *args, **kwargs):
        """Adds a model to the session. It marks the model to be stored
        in the next commit call"""
        if not model.id:
            model['_id'] = ObjectId()
            self._new.add(model)
            self._pool[model['_id']] = [model, self._new]
            model.session = self

    def add_all(self, iterable):
        """Adds every elements of an iterable object"""
        for model in iterable:
            self.add(model)

    def _register_change(self, model, attr):
        """Tiene que ser llamado cuando se cambia un valor."""
        # TODO: fix in the model
        if model.id not in self._pool:
            raise ValueError("model not in session.")
        if model in self._new:
            return

        if model in self._clean:
            self._clean.remove(model)
            self._dirty.add(remove)
            self._pool[model.id][1] = self._dirty
            self._bkp_pool[model.id] = {}

        if attr not in self._bkp_pool[model.id]:
            self._bkp_pool[model.id] = model[attr]

    def close(self):
        """Delete everything related with session"""
        # clear everything
        self._bkp_pool.clear()
        self._pool.clear()
        self._dirty.clear()
        self._new.clear()
        self._deleted.clear()
        self._clean.clear()
        # remove instances
        self._bkp_pool = self._pool = self._dirty = self._new = None
        self._deleted = self._clean = None

    def expunge(self, model):
        """Remove the model from the session"""
        del self._pool[model.id]

    def delete(self, model):
        """Marks a model to be deleted in next commit call"""
        # TODO: delete() => add() ¿?
        if model.id not in self._pool:
            raise ValueError("model is not in session.")
        if model in self._deleted:
            return

        self._pool[model.id][1].remove(model)
        del self._pool[model.id]
        self._deleted.add(model)

    def _merge(self, model, source):
        """Helper method for merge"""
        _id = model.id
        model.clear()
        model.update(source)
        model['_id'] = _id

    def merge(self, source, load=True):
        """If source is in session, it merges the value with it and returns the
        model in the session.
        else
        if load, it searchs source in the db, if it is merge the values and set
        the the new model in dirty. Otherwise, set the model in new."""
        if source.id in self._pool:
            model = self._pool[source.id][0]
            self._merge(model, source)
            self._pool[source.id][1].remove(model)
            self._pool[source.id][1] = self._dirty
            self._dirty.add(model)
            return model

        if load:
            model = source.__class__.collection().find_one({'_id': source.id})
            if model:
                self._merge()
                # add to session
                self._pool[model.id] = [model, self._dirty]
                self._dirty.add(model)

            else:
                model = source.__class__()
                model.update(source.copy())
                self._pool[model.id] = [model, self._new]
                self._new(model)

            return model

    def query(self):
        pass

    def commit(self):
        """It makes every change to the database or raise an exception"""
        for model in self._new:
            model.save()
            self._clean.add(model)
        self._new.clear()

        for model in self._dirty:
            model.sync()
            self._clean.add(model)
        self._dirty.clear()

        for model in self._deleted:
            model.delete()
            self._clean.add(model)
        self._deleted.clear()

    def rollback(self):
        """Changes the objects to the state where the transaction started"""
        for oid, old in self._bkp_pool.items():
            for attr, val in old.itmes():
                self._pool[oid][attr] = val

        self._bkp_pool.clear()
        expunge = self._new.union(self._dirty, self._deleted)
        for model in expunge:
            self._pool.pop(model.id)

        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
