"""
module sqlterm.sql.exceptions.sqlbackendexception

Contains the definition of the SqlBackendException class, a base class
that is the parent for exception classes thrown by sql backends
"""

from .sqlexception import SqlException


class SqlBackendException(SqlException):
    """
    class SqlBackendException

    A base exception class that is the parent for exception classes
    thrown by sql backends
    """
