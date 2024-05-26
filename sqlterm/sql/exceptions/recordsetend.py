"""
module sqlterm.sql.exceptions.recordsetend

Contains the definition of the RecordSetEnd class, an exception
that is thrown when the result set currently being requested by
a SQL backend has already returned the final record
"""

from .sqlexception import SqlException


class RecordSetEnd(SqlException):
    """
    class RecordSetEnd

    An exception that is thrown when the result set currently being
    requested by a SQL backend has already returned the final record
    """
