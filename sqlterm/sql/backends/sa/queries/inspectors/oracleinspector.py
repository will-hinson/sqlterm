from typing import Dict, Set, Tuple

from sqlalchemy import Connection

from .sqlinspector import SqlInspector
from .....generic.dataclasses import SqlObject, SqlStructure
from .....generic.enums import SqlDialect, SqlObjectType


class OracleInspector(SqlInspector):
    _oracle_type_name_mapping: Dict[str, SqlObjectType] = {
        "FUNCTION": SqlObjectType.FUNCTION,
        "PROCEDURE": SqlObjectType.PROCEDURE,
        "SYNONYM": SqlObjectType.SYNONYM,
        "TABLE": SqlObjectType.TABLE,
        "TYPE": SqlObjectType.TYPE,
        "VIEW": SqlObjectType.VIEW,
    }

    _column_cache: Dict[str, Dict[str, Set[str]]]

    def _cache_columns(self: "OracleInspector", connection: Connection) -> None:
        self._column_cache = {}

        for owner, table_name, column_name in connection.execute(
            self.parent.make_query(
                """
                SELECT
                    OWNER,
                    TABLE_NAME,
                    COLUMN_NAME
                FROM
                    ALL_TAB_COLUMNS
                """
            ).sa_text
        ):
            if owner not in self._column_cache:
                self._column_cache[owner] = {}
            if table_name not in self._column_cache[owner]:
                self._column_cache[owner][table_name] = set()

            self._column_cache[owner][table_name].add(column_name)

    def _get_children_for(
        self: "OracleInspector",
        schema_name: str,
        object_name: str,
        sql_object_type: SqlObjectType,
    ) -> Set[SqlObject]:
        match sql_object_type:
            case SqlObjectType.TABLE:
                return (
                    set(
                        SqlObject(column_name, SqlObjectType.COLUMN, children=set())
                        for column_name in self._column_cache[schema_name][object_name]
                    )
                    if object_name in self._column_cache[schema_name]
                    else set()
                )
            case _:
                return set()

    def _get_schema_objects(
        self: "OracleInspector", connection: Connection
    ) -> Set[Tuple[str, str, str]]:
        return set(
            map(
                tuple,
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT
                            OWNER,
                            OBJECT_NAME,
                            OBJECT_TYPE
                        FROM
                            ALL_OBJECTS
                        WHERE
                            OBJECT_TYPE IN (
                                'TABLE',
                                'SYNONYM',
                                'VIEW',
                                'FUNCTION',
                                'PROCEDURE',
                                'TYPE'
                            )
                        """
                    ).sa_text
                ),
            )
        )

    def refresh_structure(self: "OracleInspector") -> None:
        connection: Connection = self.parent.make_connection()
        self._cache_columns(connection=connection)

        schemas: Dict[str, SqlObject] = {}
        for schema_name, object_name, object_type in self._get_schema_objects(
            connection
        ):
            if schema_name not in schemas:
                schemas[schema_name] = SqlObject(
                    schema_name, type=SqlObjectType.SCHEMA, children=set()
                )

            schemas[schema_name].children.add(
                SqlObject(
                    object_name,
                    type=(
                        sql_object_type := self._oracle_type_name_mapping[object_type]
                    ),
                    children=self._get_children_for(
                        schema_name, object_name, sql_object_type
                    ),
                    is_alias=sql_object_type == SqlObjectType.SYNONYM,
                )
            )

        self.parent.parent.context.backends.prompt.refresh_structure(
            SqlStructure(
                dialect=SqlDialect.ORACLE,
                objects=set(schemas.values()),
                keywords=set(),
                builtin_types=set(),
            )
        )
