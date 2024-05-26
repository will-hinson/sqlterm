"""
module sqlterm.sql.exceptions.returnsnorecords

Contains the definition of the ReturnsNoRecords class, an exception
that is thrown when the result set currently being requested by
a SQL backend does not contain any records
"""

from .sqlexception import SqlException


class ReturnsNoRecords(SqlException):
    """
    class ReturnsNoRecords

    An exception that is thrown when the result set currently being
    requested by a SQL backend does not contain any records
    """
