"""
module sqlterm.sql.exception.disconnectedexception

Contains the definition of the DisconnectedException class, an exception
that is thrown whenever a request for a SQL operation is made of a
SQL backend that does not have an established connection
"""

from .sqlconnectionexception import SqlConnectionException


class DisconnectedException(SqlConnectionException):
    """
    class DisconnectedException

    An exception that is thrown whenever a request for a SQL operation is
    made of a SQL backend that does not have an established connection
    """
