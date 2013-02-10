""" The wrapper for pymongo's connection stuff. """
from bson.objectid import ObjectId
from pymongo import Connection as PyConnection
from pymongo.errors import ConnectionFailure
from mago.cursor import Cursor
import mago
import urllib.parse as urlparse


class Connection(object):
    """This just caches a pymongo connection and adds a few shortcuts."""

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
    """It implements unit of work and transaction"""
    DIRTY = 0
    NEW = 1
    DELETED = 2
    CLEAN = 3

    @property
    def is_active(self):
        return self._pool is not None

    def __init__(self, autocommit=True):
        self._autocommit = autocommit
        self._bkp_pool = {}  # oid => dict
        self._pool = {}  # ObjectId => (model)
        self._states = [set(), set(), set(), set()]

    def _to_state(self, model, state, new=False):
        if not new:
            self._states[model.state].remove(model)
        model._set_state(state)
        self._states[model.state].add(model)

    def add(self, model):
        """Adds a model to the session. It marks the model to be stored
        in the next commit call"""
        if not model.id:                  # TODO: else: ...
            model['_id'] = ObjectId()
            self._to_state(model, Session.NEW, new=True)
            model.session = self
            self._pool[model.id] = model

    def add_all(self, iterable):
        """Adds every elements of an iterable object"""
        if isinstance(iterable, Cursor):
            iterable.session = self
            return

        for model in iterable:
            self.add(model)

    def _register_change(self, model, attr, old_value=None):
        """It must be called when a model modify or delete an attribute.
        it moves the model to clean or dirty and stores the first value
        in case.
        New models and deleted are ignored"""
        if model.state in [Session.NEW, Session.DELETED]:
            return

        if not self._bkp_pool.get(model.id):
            self._to_state(model, Session.DIRTY)
            self._bkp_pool[model.id] = {}
            self._bkp_pool[model.id][attr] = old_value
            return

        if not attr in self._bkp_pool[model.id]:
            self._bkp_pool[model.id][attr] = old_value
        else:
            if model[attr] == self._bkp_pool[model.id][attr]:
                del self._bkp_pool[model.id][attr]
                if len(self._bkp_pool[model.id]) == 0:
                    self._to_state(model, Session.CLEAN)
                    del self._bkp_pool[model.id]

    def _register_clean(self, model):
        """Adds model to the session in state clean. It _must_ be
        synchronized with the values in the db."""
        self._pool[model.id] = model
        self._to_state(model, Session.CLEAN, new=True)
        return model

    def close(self):
        """Delete everything related with session"""
        # clear everything
        self._bkp_pool.clear()
        self._pool.clear()
        self._states[Session.DIRTY].clear()
        self._states[Session.NEW].clear()
        self._states[Session.DELETED].clear()
        self._states[Session.CLEAN].clear()
        # remove instances
        self._bkp_pool = self._pool = self._states[Session.DIRTY] = \
          self._states[Session.NEW] = self._states[Session.DELETED] = \
          self._states[Session.CLEAN] = None

    def expunge(self, model):
        """Remove the model from the session"""
        del self._pool[model.id]
        model._set_state(None)
        model.set_session(None)

    def delete(self, model):
        """Marks a model to be deleted in next commit call"""
        # TODO: delete() => add() ¿?
        if model.id not in self._pool:
            raise ValueError("model is not in session.")

        self._to_state(model, Session.DELETED)
        del self._pool[model.id]

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
            self._pool[source.id][1] = self._states[Session.DIRTY]
            self._states[Session.DIRTY].add(model)
            return model

        if load:
            model = source.__class__.collection().find_one({'_id': source.id})
            if model:
                self._merge()
                # add to session
                self._pool[model.id] = [model, self._states[Session.DIRTY]]
                self._states[Session.DIRTY].add(model)

            else:
                model = source.__class__()
                model.update(source.copy())
                self._pool[model.id] = [model, self._states[Session.NEW]]
                self._states[Session.NEW](model)

            return model

    def commit(self):
        """It makes every change to the database or raise an exception"""
        for model in self._states[Session.NEW]:
            model.save()
            self._states[Session.CLEAN].add(model)
        self._states[Session.NEW].clear()

        for model in self._states[Session.DIRTY]:
            model.sync()
            self._states[Session.CLEAN].add(model)
        self._states[Session.DIRTY].clear()

        for model in self._states[Session.DELETED]:
            model.delete()
            self._states[Session.CLEAN].add(model)
        self._states[Session.DELETED].clear()

    def rollback(self):
        """Changes the objects to the state where the transaction started"""
        for oid, old in self._bkp_pool.items():
            for attr, val in old.items():
                self._pool[oid]._set_state(Session.NEW)   # Don't track changes
                self._pool[oid][attr] = val
                self._pool[oid]._set_state(Session.DIRTY)   # Don't track changes
                self._to_state(self._pool[oid], Session.CLEAN)


        self._bkp_pool.clear()

        # que hago con
        # from pprint import pprint
        # pprint(self._states)
        # pprint(self._pool)

        [(self._pool.pop(model.id), model._set_state(None))
        for model in self._states[Session.NEW]]
        # for model in self._states[Session.NEW]:
        #     print(model)
        #     self._pool.pop(model.id)
        #     model._set_state(None)


        self._states[Session.DIRTY].clear()
        self._states[Session.NEW].clear()
        self._states[Session.DELETED].clear()
