"""
module sqlterm.sql.exceptions

Contains definitions of all exceptions that are thrown directly by a SQL backend
as a result of the state of a connection or query
"""

from .connectionexistsexception import ConnectionExistsException
from .connectionfailedexception import ConnectionFailedException
from .dialectexception import DialectException
from .disconnectedexception import DisconnectedException
from .invalidurlexception import InvalidUrlException
from .missingmoduleexception import MissingModuleException
from .notablebackendexception import NoTableBackendException
from .recordsetend import RecordSetEnd
from .returnsnorecords import ReturnsNoRecords
from .sqlbackendexception import SqlBackendException
from .sqlbackendmismatchexception import SqlBackendMismatchException
from .sqlconnectionexception import SqlConnectionException
from .sqlexception import SqlException
from .sqlqueryexception import SqlQueryException
