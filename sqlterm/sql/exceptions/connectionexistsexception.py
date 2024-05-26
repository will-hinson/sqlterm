"""
module sqlterm.sql.exceptions.connectionexistsexception

Contains the definition of the ConnectionExistsException class, an exception
that is thrown whenever a SQL connection has already been established in
the current sqlterm environment
"""

from .sqlconnectionexception import SqlConnectionException


class ConnectionExistsException(SqlConnectionException):
    """
    class ConnectionExistsException

    An exception that is thrown whenever a SQL connection has already been
    established in the current sqlterm environment
    """
