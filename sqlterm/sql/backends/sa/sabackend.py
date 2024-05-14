from typing import List, Tuple, Type
import warnings

import pyodbc
from sqlalchemy import Connection, create_engine, make_url, NullPool, URL
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ...abstract import Query, SqlBackend
from ...exceptions import (
    ConnectionExistsException,
    ConnectionFailedException,
    DialectException,
    DisconnectedException,
    InvalidUrlException,
    MissingModuleException,
    NoTableBackendException,
    RecordSetEnd,
    ReturnsNoRecords,
    SqlBackendMismatchException,
    SqlQueryException,
)
from .dataclasses import ConnectionPromptModel
from .enums import SaDialect
from .enums.sadialect import (
    generic_dialect_map,
    dialect_connection_parameters,
    dialect_connection_prompt_models,
)
from ...generic import RecordSet
from ...generic.enums import SqlDialect
from ....prompt.dataclasses import SqlStatusDetails
from .queries.inspectors import (
    DefaultInspector,
    sql_inspector_for_dialect,
    SqlInspector,
)
from .queries.managers import DefaultManager, query_manager_for_dialect, QueryManager
from .saspoolmonitor import SaSpoolMonitor
from .saquery import SaQuery

# disable pyodbc pooling so that extra database connections will not stay open
pyodbc.pooling = False


class SaBackend(SqlBackend):
    __active_connection: Connection | None = None
    __dialect: SaDialect | None = None
    __engine: Engine | None = None
    __inspector: SqlInspector | None = None

    def connect(self: "SaBackend", connection_string: str) -> None:
        self._connect_with_string(connection_string)

    @property
    def connected(self: "SaBackend") -> bool:
        return self.__active_connection is not None

    def disconnect(self: "SaBackend") -> None:
        self.parent.context.backends.prompt.clear_completions()

        if self.__active_connection is not None:
            self.__active_connection.close()
            self.__active_connection = None

        if self.__engine is not None:
            self.__engine.dispose()
            self.__engine = None

        self.__dialect = None
        self._update_prompt_dialect()

    def _connect_with_string(self: "SaBackend", connection_string: str) -> None:
        # check if a connection already exists
        if self.engine is not None:
            raise ConnectionExistsException(
                "A connection has already been established with "
                + str(
                    self.connection.engine.url.host
                    if self.connection.engine.url.host is not None
                    else repr(self.connection.engine.url)
                )
                + ". Disconnect the existing session first"
            )

        # construct a URL from the connection string and try mapping to a dialect
        connection_url: URL = self._try_make_url(connection_string)
        try:
            self.__dialect = SaDialect(
                self._dialect_name_from_driver_string(connection_url.drivername)
            )
            self._update_prompt_dialect()
        except ValueError:
            self.__dialect = None

        # ensure we're not already connected
        self._init_engine(connection_url)

        # establish a connection to the sql host
        try:
            self.__active_connection = self.make_connection()

            # NOTE: we were originally streaming the results but this caused issues
            # with DDL statements in postgres
            #
            # self.__active_connection.execution_options(stream_results=True)
        except SQLAlchemyError as sae:
            self.disconnect()
            raise ConnectionFailedException("\n".join(sae.args)) from sae

        # set up an inspector for this dialect
        self._init_inspector()

        # check if this dialect has an appropriate QueryManager subclass
        self._show_dialect_warnings(connection_url)

    @property
    def connection(self: "SaBackend") -> Connection:
        return self.__active_connection

    @property
    def connection_string(self: "SaBackend") -> str:
        if self.engine is not None:
            return self.engine.url.render_as_string(hide_password=False)

        raise DisconnectedException("No SQL connection is currently established")

    @property
    def dialect(self: "SaBackend") -> SaDialect | None:
        return self.__dialect

    def _dialect_name_from_driver_string(self: "SaBackend", drivername: str) -> str:
        if "+" in drivername:
            return drivername[: drivername.index("+")]

        return drivername

    def display_progress(self: "SaBackend", *progress_messages) -> None:
        self.parent.context.backends.prompt.display_progress(*progress_messages)

    @property
    def engine(self: "SaBackend") -> Engine:
        return self.__engine

    def execute(self: "SaBackend", query: Query) -> None:
        # check that this is a sqlalchemy query
        if not isinstance(query, SaQuery):
            raise SqlBackendMismatchException(
                f"{type(self).__name__}.execute() requires a query of type SaQuery, "
                f"not {type(query).__name__}"
            )

        # ensure we have a connection established
        if self.engine is None:
            raise DisconnectedException(
                "No SQL connection has been established. Establish a connection first "
                "with the 'connect' command"
            )

        # initialize an appropriate manager for this dialect and start spooling
        # result records from the query
        with (
            DefaultManager
            if self.dialect not in query_manager_for_dialect
            else query_manager_for_dialect[self.dialect]
        )(connection=self.connection, target_query=query, parent=self) as manager:
            # get/display all result sets from the query
            self._spool_results(manager)

    def fetch_results_for(self: "SaBackend", query: Query) -> List[Tuple]:
        try:
            return list(map(tuple, self.connection.execute(query.sa_text).fetchall()))
        except SQLAlchemyError as sae:
            raise SqlQueryException("\n".join(sae.args)) from sae

    def get_status(self: "SaBackend") -> SqlStatusDetails:
        connection_detail: str = (
            "" if self.engine is None else self._get_status_connection_detail()
        )

        return SqlStatusDetails(
            connected=self.connection is not None,
            connection_detail=connection_detail,
            dialect=(
                self.engine.url.get_backend_name() if self.engine is not None else None
            ),
        )

    def _get_status_connection_detail(self: "SaBackend") -> str:
        connection_detail: str
        url: URL = self.engine.url
        if url.host is None:
            connection_detail = url.render_as_string(hide_password=True)
        else:
            if url.database is None:
                connection_detail = (
                    "" if url.username is None else f"{url.username}@"
                ) + url.host
            else:
                connection_detail = (
                    "" if url.username is None else f"{url.username}@"
                ) + f"{url.host}:{url.database}"

        return connection_detail

    def _init_engine(self: "SaBackend", connection_url: URL) -> None:
        try:
            self.__engine = self.make_engine(connection_url, dialect=self.dialect)
        except ModuleNotFoundError as mnfe:
            raise MissingModuleException(mnfe.args[0]) from mnfe

    def _init_inspector(self: "SaBackend") -> None:
        inspector_type: Type[SqlInspector] | None = (
            sql_inspector_for_dialect[self.dialect]
            if self.dialect in sql_inspector_for_dialect
            else None
        )

        if inspector_type is not None:
            self.__inspector = inspector_type(parent=self)
            self.__inspector.start()
        else:
            self.__inspector = DefaultInspector(parent=self)
            self.__inspector.start()

    @property
    def inspecting(self: "SaBackend") -> bool:
        return self.__inspector.is_alive()

    def invalidate_completions(self: "SaBackend") -> None:
        # don't invalidate if we don't currently have a connection
        if self.engine is None:
            return

        self._init_inspector()

    def make_connection(self: "SaBackend") -> Connection:
        # patch the _autobegin() method with one that doesn't start a transaction
        # and set up autocommit on the underlying connection object if we can
        def _no_autobegin(*_, **__) -> None: ...

        Connection._autobegin = _no_autobegin

        connection: Connection = self.__engine.connect()
        if hasattr(connection._dbapi_connection.dbapi_connection, "autocommit"):
            connection._dbapi_connection.dbapi_connection.autocommit = True

        return connection

    def make_engine(
        self: "SaBackend", connection_url: URL, dialect: SaDialect
    ) -> Engine:
        return create_engine(
            connection_url,
            connect_args=(
                {}
                if dialect not in dialect_connection_parameters
                else dialect_connection_parameters[dialect]
            ),
            # relinquishes all DBAPI connections back to the database server
            poolclass=NullPool,
            # disables enclosing transactions when running queries
            # isolation_level="AUTOCOMMIT",
        )

    def make_query(self: "SaBackend", query_str: str) -> SaQuery:
        return SaQuery(query_str)

    def required_packages_for_dialect(self: "SaBackend", dialect: str) -> List[str]:
        match dialect:
            case "oracle+oracledb":
                return ["oracledb==2.1.2"]
            case "postgresql+psycopg2":
                return ["psycopg2==2.9.9"]
            case "mssql+pyodbc":
                return ["pyodbc==5.1.0"]
            case "mysql+mysqlconnector":
                return ["mysql-connector-python==8.3.0"]
            case _:
                raise DialectException(
                    f"{type(self).__name__}: Required packages for dialect '{dialect}' "
                    "are unknown"
                )

    def resolve_connection_string(
        self: "SqlBackend", connection_string: str, test_connection: bool = False
    ) -> str:
        url: URL = self._try_make_url(
            connection_string, message_prefix="Testing connection to "
        )

        if test_connection:
            try:
                engine = create_engine(url)

                with engine.connect() as connection:
                    connection.execute(self.make_query("SELECT 1").sa_text)

                engine.dispose()
            except Exception as exc:
                raise ConnectionFailedException(
                    f"Connection test failed: {exc}"
                ) from exc

        return url.render_as_string(hide_password=False)

    def _show_dialect_warnings(self: "SaBackend", connection_url: URL) -> None:
        warnings.simplefilter("always")

        if self.dialect is None:
            warnings.warn(
                f"Driver {connection_url.drivername} has no associated SQL dialect"
            )
        elif self.dialect not in query_manager_for_dialect:
            warnings.warn(
                f"SQL dialect {self.dialect} has no defined QueryManager. "
                "Defaulting to DefaultManager. Only one record set is supported and "
                "row loading performance may be noticeably degraded"
            )

        if self.dialect is not None and type(self.__inspector) == DefaultInspector:
            warnings.warn(
                f"SQL dialect {self.dialect} has no defined SqlInspector. "
                "Autocomplete suggestions will be limited to ANSI SQL keywords/functions "
                "and the information_schema if it is available"
            )

    def _spool_results(
        self: "SaBackend", query_manager: QueryManager
    ) -> List[RecordSet]:
        if self.table_backend is None:
            raise NoTableBackendException(
                "No TableBackend was provided to the SqlBackend. Cannot display results"
            )

        record_sets: List[RecordSet] = []

        while query_manager.has_another_record_set:
            spool: List[Tuple] = []

            # start a spool monitor to output progress updates
            monitor: SaSpoolMonitor = SaSpoolMonitor(spool=spool, parent=self)
            monitor.start()

            # spool all of the streaming records from the connection
            try:
                while record := query_manager.fetch_row():
                    spool.append(record)  # type: ignore
            except (RecordSetEnd, ReturnsNoRecords):
                # the record set is either done or empty. quit trying to read rows
                ...
            except (KeyboardInterrupt, Exception):
                # stop the monitor if we've encountered an unexpected exception then re-raise
                monitor.stop()
                monitor.join()
                raise

            # mark that we're done retrieving records
            monitor.done = True

            # store this spool into the list of record sets if we got records and display any
            # records that we got
            table: str | None = None
            try:
                if len(query_manager.columns) != 0:
                    record_sets.append(
                        current_record_set := RecordSet(
                            columns=query_manager.columns, records=spool
                        )
                    )
                    table = self.table_backend.construct_table(current_record_set)
            except (KeyboardInterrupt, Exception):
                # stop the monitor if we've encountered an unexpected exception then re-raise
                monitor.stop()
                monitor.join()
                raise

            # stop the monitor when we're done
            monitor.stop()
            monitor.join()

            # output the table if there is one
            if table is not None:
                self.parent.context.backends.prompt.display_table(table)

        return record_sets

    def _try_make_url(
        self: "SaBackend",
        connection_string: str,
        message_prefix: str = "Connecting to ",
    ) -> URL:
        # variable to hold a censored version of the connection string. this is the
        # same as the connection string the user entered by default, but it will
        # censor the password if the user enters the connect details via the prompt
        censored_connection_string: str = connection_string

        # check if this connection string is an alias
        if connection_string in self.parent.context.config.aliases:
            censored_connection_string = f"'{connection_string}'"
            connection_string = self.parent.context.config.aliases[
                connection_string
            ].url
        else:
            # check if this connection string represents a dialect with a known
            # connection prompt model
            dialect_string: str = (
                connection_string
                if "+" not in connection_string
                else connection_string[: connection_string.index("+")]
            )
            if (
                "://" not in connection_string
                and dialect_string in dialect_connection_prompt_models
            ):
                dialect_prompt_model: ConnectionPromptModel = (
                    dialect_connection_prompt_models[dialect_string]
                )

                # prompt the user with the prompt model and construct a url from it
                user_url: URL = dialect_prompt_model.url_factory(
                    [f"{connection_string}://"]
                    + self.parent.context.backends.prompt.prompt_for(
                        dialect_prompt_model.input_models
                    )
                )

                # render two version of the connection string, one to use and one to display
                connection_string = user_url.render_as_string(hide_password=False)
                censored_connection_string: str = user_url.render_as_string(
                    hide_password=True
                )

                # output a blank line before echoing the connection string
                self.parent.context.backends.prompt.display_message_sql("")

        # echo the string that we're connecting with. it will be censored if the user
        # entered their password at a password prompt
        self.parent.context.backends.prompt.display_message_sql(
            f"{message_prefix}{censored_connection_string}"
        )

        try:
            return make_url(connection_string)
        except SQLAlchemyError as sae:
            raise InvalidUrlException(f"{type(sae).__name__}: {sae.args[0]}") from sae

    def _update_prompt_dialect(self: "SaBackend") -> None:
        if self.dialect in generic_dialect_map:
            self.parent.context.backends.prompt.change_dialect(
                dialect=generic_dialect_map[self.dialect]
            )
        else:
            self.parent.context.backends.prompt.change_dialect(
                dialect=SqlDialect.GENERIC
            )
