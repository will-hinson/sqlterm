from typing import Dict, Set, Tuple

from sqlalchemy import Connection

from ...... import constants
from .....generic.dataclasses import SqlObject, SqlStructure
from .....generic.enums import SqlDialect, SqlObjectType
from .sqlinspector import SqlInspector


class DefaultInspector(SqlInspector):
    __column_map: Dict[str, Dict[str, Dict[str, Set[str]]]] | None = None
    __routine_type_mapping: Dict[str, SqlObjectType] = {
        "PROCEDURE": SqlObjectType.PROCEDURE,
        "FUNCTION": SqlObjectType.FUNCTION_SCALAR,
    }

    def _cache_column_map(self: "DefaultInspector", connection: Connection) -> None:
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
        self: "DefaultInspector", query: str, connection: Connection
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

    def _get_schemas_by_catalog(
        self: "DefaultInspector", connection: Connection
    ) -> Dict[str, Dict[str, SqlObject]]:
        schemas_by_catalog: Dict[str, Dict[str, SqlObject]] = {}

        # first, get a list of known schemas
        for catalog_name, schema_name in self._fetch_query_results(
            """
            SELECT
                CATALOG_NAME,
                SCHEMA_NAME
            FROM
                INFORMATION_SCHEMA.SCHEMATA
            """,
            connection=connection,
        ):
            if catalog_name not in schemas_by_catalog:
                schemas_by_catalog[catalog_name] = {}

            schemas_by_catalog[catalog_name][schema_name] = SqlObject(
                name=schema_name, type=SqlObjectType.SCHEMA, children=set()
            )

        return schemas_by_catalog

    def _populate_routines(
        self: "DefaultInspector",
        schemas_by_catalog: Dict[str, Dict[str, SqlObject]],
        connection: Connection,
    ) -> None:
        for (
            routine_catalog,
            routine_schema,
            routine_name,
            routine_type,
        ) in self._fetch_query_results(
            """
            SELECT
                ROUTINE_CATALOG,
                ROUTINE_SCHEMA,
                ROUTINE_NAME,
                ROUTINE_TYPE
            FROM
                INFORMATION_SCHEMA.ROUTINES
            """,
            connection=connection,
        ):
            if routine_type not in self.__routine_type_mapping:
                continue

            schemas_by_catalog[routine_catalog][routine_schema].children.add(
                SqlObject(
                    name=routine_name,
                    type=self.__routine_type_mapping[routine_type],
                    children=set(),
                )
            )

    def _populate_tables(
        self: "DefaultInspector",
        schemas_by_catalog: Dict[str, Dict[str, SqlObject]],
        connection: Connection,
    ) -> None:
        for table_catalog, table_schema, table_name in self._fetch_query_results(
            """
            SELECT
                TABLE_CATALOG,
                TABLE_SCHEMA,
                TABLE_NAME
            FROM
                INFORMATION_SCHEMA.TABLES
            WHERE
                TABLE_TYPE = 'BASE TABLE'
            """,
            connection=connection,
        ):
            children: Set[SqlObject] | None = self._get_columns_for_table(
                table_catalog, table_schema, table_name
            )
            if children is None:
                children = set()

            schemas_by_catalog[table_catalog][table_schema].children.add(
                SqlObject(name=table_name, type=SqlObjectType.TABLE, children=children)
            )

    def _populate_views(
        self: "DefaultInspector",
        schemas_by_catalog: Dict[str, Dict[str, SqlObject]],
        connection: Connection,
    ) -> None:
        for table_catalog, table_schema, table_name in self._fetch_query_results(
            """
            SELECT
                TABLE_CATALOG,
                TABLE_SCHEMA,
                TABLE_NAME
            FROM
                INFORMATION_SCHEMA.VIEWS
            """,
            connection=connection,
        ):
            schemas_by_catalog[table_catalog][table_schema].children.add(
                SqlObject(name=table_name, type=SqlObjectType.TABLE, children=set())
            )

    def refresh_structure(self: "DefaultInspector") -> None:
        connection: Connection = self.parent.make_connection()

        # preload a list of columns for all tables
        self._cache_column_map(connection)

        # get a mapping of schemas by catalog
        schemas_by_catalog: Dict[
            str, Dict[str, SqlObject]
        ] = self._get_schemas_by_catalog(connection)

        # populate the mapping with underlying objects
        for populate_function in (
            self._populate_routines,
            self._populate_tables,
            self._populate_views,
        ):
            populate_function(schemas_by_catalog, connection=connection)

        self.parent.parent.context.backends.prompt.refresh_structure(
            SqlStructure(
                dialect=SqlDialect.GENERIC,
                objects={
                    SqlObject(
                        catalog_name,
                        type=SqlObjectType.CATALOG,
                        children=set(schema_dict.values()),
                    )
                    for catalog_name, schema_dict in schemas_by_catalog.items()
                },
                keywords={
                    SqlObject(keyword, type=SqlObjectType.KEYWORD, children=set())
                    for keyword in constants.ANSI_SQL_KEYWORDS
                },
                builtin_types=set(),
            )
        )
