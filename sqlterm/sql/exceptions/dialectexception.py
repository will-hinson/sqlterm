"""
class sqlterm.sql.exceptions.dialectexception

Contains the definition of the DialectException class, an exception class
that is thrown whenever a sql dialect related error occurs (for example, 
trying to perform an operation that is not implemented for the
currently selected dialect)
"""

from .sqlbackendexception import SqlBackendException


class DialectException(SqlBackendException):
    """
    class DialectException

    An exception class that is thrown whenever a sql dialect related
    error occurs (for example, trying to perform an operation that is
    not implemented for the currently selected dialect)
    """
