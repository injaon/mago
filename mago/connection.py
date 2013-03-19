""" The wrapper for pymongo's connection stuff. """
from bson.objectid import ObjectId
from pymongo import Connection as PyConnection
from pymongo.errors import ConnectionFailure
import mago
from mago.cursor import Cursor
# import mago.transaction as tran
import mago.decorators
import urllib.parse as urlparse


@mago.decorators.singleton
class Connection(object):
    """This just caches a pymongo connection and adds a few shortcuts."""

    connection = None
    _host = None
    _port = None
    _database = None

    def connect(self, database=None, *args, **kwargs):
        """ Wraps a pymongo connection.
        TODO: Allow some of the URI stuff."""
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

        self._database = database
        self.connection = PyConnection(*args, **kwargs)
        # recover from possible errors.
        # tran.recovery()
        return self.connection

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
    return Connection().connect(*args, **kwargs)
