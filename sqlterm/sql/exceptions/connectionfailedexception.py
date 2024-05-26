"""
module sqlterm.sql.exceptions.connectionfailedexception

Contains the definition of the ConnectionFailedException class, an exception
that is thrown whenever a SQL connection could not be established in
the current sqlterm environment
"""

from .sqlconnectionexception import SqlConnectionException


class ConnectionFailedException(SqlConnectionException):
    """
    class ConnectionFailedException

    An exception that is thrown whenever a SQL connection could not be
    established in the current sqlterm environment
    """
