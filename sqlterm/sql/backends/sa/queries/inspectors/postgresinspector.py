from typing import Dict, Set, Tuple

from pygments.lexers.sql import PlPgsqlLexer
from pygments.token import Token
from sqlalchemy import Connection

from .....generic.dataclasses import SqlObject, SqlStructure
from .....generic.enums import SqlDialect, SqlObjectType
from .sqlinspector import SqlInspector


class PostgresInspector(SqlInspector):
    _postgres_keywords: Set[str] = {
        word.upper()
        for word_list in [
            token_tuple[0].words
            for token_tuple in PlPgsqlLexer().tokens["root"]
            if token_tuple[1] == Token.Keyword
        ]
        for word in word_list
    }

    _postgres_types: Set[str] = {
        "BIGINT",
        "BIGSERIAL",
        "BIT",
        "BIT VARYING",
        "BOOLEAN",
        "BOX",
        "BYTEA",
        "CHARACTER",
        "CHARACTER VARYING",
        "CIDR",
        "CIRCLE",
        "DATE",
        "DOUBLE PRECISION",
        "INET",
        "INTEGER",
        "INTERVAL",
        "JSON",
        "JSONB",
        "LINE",
        "LSEG",
        "MACADDR",
        "MACADDR8",
        "MONEY",
        "NUMERIC",
        "PATH",
        "PG_LSN",
        "PG_SNAPSHOT",
        "POINT",
        "POLYGON",
        "REAL",
        "SERIAL",
        "SMALLINT",
        "SMALLSERIAL",
        "TEXT",
        "TIME",
        "TIMESTAMP",
        "TSQUERY",
        "TSVECTOR",
        "UUID",
        "XML",
    }

    __column_map: Dict[str, Dict[str, Dict[str, Set[str]]]] | None = None

    def _cache_column_map(self: "PostgresInspector", connection: Connection) -> None:
        self.__column_map = {}

        for (
            column_catalog,
            column_schema,
            column_table,
            column_name,
        ) in self._fetch_query_results(
            """
            SELECT
                TABLE_CATALOG,
                TABLE_SCHEMA,
                TABLE_NAME,
                COLUMN_NAME
            FROM
                INFORMATION_SCHEMA.COLUMNS
            """,
            connection=connection,
        ):
            if column_catalog not in self.__column_map:
                self.__column_map[column_catalog] = {}
            if column_schema not in self.__column_map[column_catalog]:
                self.__column_map[column_catalog][column_schema] = {}
            if column_table not in self.__column_map[column_catalog][column_schema]:
                self.__column_map[column_catalog][column_schema][column_table] = set()

            self.__column_map[column_catalog][column_schema][column_table].add(
                column_name
            )

    def _fetch_query_results(
        self: "PostgresInspector", query: str, connection: Connection
    ) -> Set[Tuple]:
        return set(
            map(
                tuple,
                connection.execute(self.parent.make_query(query).sa_text).fetchall(),
            )
        )

    def _get_columns_for_table(
        self: "DefaultInspector", table_catalog: str, table_schema: str, table_name: str
    ) -> Set[SqlObject] | None:
        if (
            self.__column_map is not None
            and table_catalog in self.__column_map
            and table_schema in self.__column_map[table_catalog]
            and table_name in self.__column_map[table_catalog][table_schema]
        ):
            return {
                SqlObject(column_name, type=SqlObjectType.COLUMN, children=set())
                for column_name in self.__column_map[table_catalog][table_schema][
                    table_name
                ]
            }

        return None

    def _get_current_database_name(
        self: "PostgresInspector", connection: Connection
    ) -> str:
        return connection.execute(
            self.parent.make_query("SELECT CURRENT_DATABASE();").sa_text
        ).scalar()  # type: ignore

    def _get_database_names(
        self: "PostgresInspector", connection: Connection
    ) -> Set[str]:
        return set(
            map(
                lambda row: row[0],
                self._fetch_query_results(
                    """
                    SELECT DISTINCT
                        datname
                    FROM
                        pg_catalog.pg_database;
                    """,
                    connection=connection,
                ),
            )
        )

    def _get_schemas_by_database(
        self: "PostgresInspector", current_database: str, connection: Connection
    ) -> Dict[str, Dict[str, SqlObject]]:
        # first, get a list of databases at the global level
        schemas_by_database: Dict[str, Dict[str, SqlObject]] = {
            database_name: {} for database_name in self._get_database_names(connection)
        }

        # then, add all of the schemas to the current database
        for schema_name in map(
            lambda row: row[0],
            self._fetch_query_results(
                """
                SELECT DISTINCT
                    nspname
                FROM
                    pg_catalog.pg_namespace;
                """,
                connection=connection,
            ),
        ):
            schemas_by_database[current_database][schema_name] = SqlObject(
                schema_name, type=SqlObjectType.SCHEMA, children=set()
            )

        return schemas_by_database

    def _populate_functions(
        self: "PostgresInspector",
        schemas_by_database: Dict[str, Dict[str, SqlObject]],
        current_database: str,
        connection: Connection,
    ) -> None:
        for schema_name, function_name in self._fetch_query_results(
            """
            SELECT DISTINCT
                b.nspname,
                a.proname
            FROM
                pg_catalog.pg_proc AS a
            LEFT JOIN pg_catalog.pg_namespace AS b ON
                a.pronamespace = b.oid
            WHERE 
                a.prokind NOT IN (
                    'p'
                )
                AND a.prorettype != 'pg_catalog.trigger'::pg_catalog.regtype
                AND pg_catalog.pg_function_is_visible(a.oid);
            """,
            connection=connection,
        ):
            schemas_by_database[current_database][schema_name].children.add(
                SqlObject(function_name, type=SqlObjectType.FUNCTION, children=set())
            )

    def _populate_procedures(
        self: "PostgresInspector",
        schemas_by_database: Dict[str, Dict[str, SqlObject]],
        current_database: str,
        connection: Connection,
    ) -> None:
        for schema_name, procedure_name in self._fetch_query_results(
            """
            SELECT DISTINCT
                b.nspname,
                a.proname
            FROM
                pg_catalog.pg_proc AS a
            LEFT JOIN pg_catalog.pg_namespace AS b ON
                a.pronamespace = b.oid;
            """,
            connection=connection,
        ):
            schemas_by_database[current_database][schema_name].children.add(
                SqlObject(procedure_name, type=SqlObjectType.PROCEDURE, children=set())
            )

    def _populate_tables(
        self: "PostgresInspector",
        schemas_by_database: Dict[str, Dict[str, SqlObject]],
        current_database: str,
        connection: Connection,
    ) -> None:
        for schema_name, table_name in self._fetch_query_results(
            """
            SELECT DISTINCT
                schemaname,
                tablename
            FROM
                pg_catalog.pg_tables;
            """,
            connection=connection,
        ):
            children: Set[SqlObject] | None = self._get_columns_for_table(
                current_database, schema_name, table_name
            )
            if children is None:
                children = set()

            schemas_by_database[current_database][schema_name].children.add(
                SqlObject(table_name, type=SqlObjectType.TABLE, children=children)
            )

    def _populate_types(
        self: "PostgresInspector",
        schemas_by_database: Dict[str, Dict[str, SqlObject]],
        current_database: str,
        connection: Connection,
    ) -> None:
        for schema_name, type_name in self._fetch_query_results(
            r"""
            SELECT DISTINCT
                b.nspname,
                a.typname
            FROM
                pg_catalog.pg_type AS a
            LEFT JOIN pg_catalog.pg_namespace AS b ON
                a.typnamespace = b.oid
            WHERE
                typname NOT LIKE '\_%'
                AND pg_catalog.pg_type_is_visible(oid);
            """,
            connection=connection,
        ):
            schemas_by_database[current_database][schema_name].children.add(
                SqlObject(type_name, type=SqlObjectType.TABLE, children=set())
            )

    def _populate_views(
        self: "PostgresInspector",
        schemas_by_database: Dict[str, Dict[str, SqlObject]],
        current_database: str,
        connection: Connection,
    ) -> None:
        for schema_name, view_name in self._fetch_query_results(
            """
            SELECT DISTINCT
                schemaname,
                viewname
            FROM
                pg_catalog.pg_views;
            """,
            connection=connection,
        ):
            children: Set[SqlObject] | None = self._get_columns_for_table(
                current_database, schema_name, view_name
            )
            if children is None:
                children = set()

            schemas_by_database[current_database][schema_name].children.add(
                SqlObject(view_name, type=SqlObjectType.VIEW, children=children)
            )

    def refresh_structure(self: "PostgresInspector") -> None:
        connection: Connection = self.parent.make_connection()

        # prebuild a list of columns
        self._cache_column_map(connection)

        # get the name of the current database and an initial schema mapping at the
        # database level. note that we'll only be able to get schemas in the current
        # database context as postgres doesn't allow cross-database references
        database_name: str = self._get_current_database_name(connection)
        schemas_by_database: Dict[str, Dict[str, SqlObject]] = (
            self._get_schemas_by_database(
                current_database=database_name, connection=connection
            )
        )

        # populate all of the objects into the database/schema mapping
        for populate_func in (
            self._populate_functions,
            self._populate_procedures,
            self._populate_tables,
            self._populate_views,
        ):
            populate_func(
                schemas_by_database,
                current_database=database_name,
                connection=connection,
            )

        self.parent.parent.context.backends.prompt.refresh_structure(
            SqlStructure(
                dialect=SqlDialect.POSTGRES,
                objects={
                    SqlObject(
                        catalog_name,
                        type=SqlObjectType.DATABASE,
                        children=set(schema_dict.values()),
                    )
                    for catalog_name, schema_dict in schemas_by_database.items()
                },
                keywords={
                    SqlObject(keyword, type=SqlObjectType.KEYWORD, children=set())
                    for keyword in self._postgres_keywords
                },
                builtin_types={
                    SqlObject(
                        type_name, type=SqlObjectType.DATATYPE_BUILTIN, children=set()
                    )
                    for type_name in self._postgres_types
                },
            )
        )
