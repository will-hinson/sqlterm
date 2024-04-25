from typing import Dict, Set

from sqlalchemy import Connection
from sqlalchemy.exc import OperationalError

from ...enums.sadialect import generic_dialect_map
from .....generic.dataclasses import SqlObject, SqlStructure
from .....generic.enums import SqlObjectType
from .sqlinspector import SqlInspector


class SqliteInspector(SqlInspector):
    _sqlite_keywords: Set[str] = {
        "ABORT",
        "ACTION",
        "ADD",
        "AFTER",
        "ALL",
        "ALTER",
        "ALWAYS",
        "ANALYZE",
        "AND",
        "AS",
        "ASC",
        "ATTACH",
        "AUTOINCREMENT",
        "BEFORE",
        "BEGIN",
        "BETWEEN",
        "BY",
        "CASCADE",
        "CASE",
        "CAST",
        "CHECK",
        "COLLATE",
        "COLUMN",
        "COMMIT",
        "CONFLICT",
        "CONSTRAINT",
        "CREATE",
        "CROSS",
        "CURRENT",
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "DATABASE",
        "DEFAULT",
        "DEFERRABLE",
        "DEFERRED",
        "DELETE",
        "DESC",
        "DETACH",
        "DISTINCT",
        "DO",
        "DROP",
        "EACH",
        "ELSE",
        "END",
        "ESCAPE",
        "EXCEPT",
        "EXCLUDE",
        "EXCLUSIVE",
        "EXISTS",
        "EXPLAIN",
        "FAIL",
        "FILTER",
        "FIRST",
        "FOLLOWING",
        "FOR",
        "FOREIGN",
        "FROM",
        "FULL",
        "GENERATED",
        "GLOB",
        "GROUP",
        "GROUPS",
        "HAVING",
        "IF",
        "IGNORE",
        "IMMEDIATE",
        "IN",
        "INDEX",
        "INDEXED",
        "INITIALLY",
        "INNER",
        "INSERT",
        "INSTEAD",
        "INTERSECT",
        "INTO",
        "IS",
        "ISNULL",
        "JOIN",
        "KEY",
        "LAST",
        "LEFT",
        "LIKE",
        "LIMIT",
        "MATCH",
        "MATERIALIZED",
        "NATURAL",
        "NO",
        "NOT",
        "NOTHING",
        "NOTNULL",
        "NULL",
        "NULLS",
        "OF",
        "OFFSET",
        "ON",
        "OR",
        "ORDER",
        "OTHERS",
        "OUTER",
        "OVER",
        "PARTITION",
        "PLAN",
        "PRAGMA",
        "PRECEDING",
        "PRIMARY",
        "QUERY",
        "RAISE",
        "RANGE",
        "RECURSIVE",
        "REFERENCES",
        "REGEXP",
        "REINDEX",
        "RELEASE",
        "RENAME",
        "REPLACE",
        "RESTRICT",
        "RETURNING",
        "RIGHT",
        "ROLLBACK",
        "ROW",
        "ROWS",
        "SAVEPOINT",
        "SELECT",
        "SET",
        "TABLE",
        "TEMP",
        "TEMPORARY",
        "THEN",
        "TIES",
        "TO",
        "TRANSACTION",
        "TRIGGER",
        "UNBOUNDED",
        "UNION",
        "UNIQUE",
        "UPDATE",
        "USING",
        "VACUUM",
        "VALUES",
        "VIEW",
        "VIRTUAL",
        "WHEN",
        "WHERE",
        "WINDOW",
        "WITH",
        "WITHOUT",
    }

    _sqlite_types: Set[str] = {"BLOB", "INTEGER", "NUMERIC", "REAL", "TEXT"}

    def _get_column_names(
        self: "SqliteInspector", table_name: str, connection: Connection
    ) -> Set[str]:
        return set(
            map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT
                            name
                        FROM
                            pragma_table_info('?')
                        """.replace(
                            "?", table_name.replace("'", "''")
                        )
                    ).sa_text
                ).fetchall(),
            )
        )

    def _get_pragma_columns(
        self: "SqliteInspector", pragma_name: str, connection: Connection
    ) -> Set[SqlObject]:
        try:
            with connection.execute(
                self.parent.make_query(
                    """
                    SELECT
                        *
                    FROM
                        "pragma_?"()
                    LIMIT
                        0;
                    """.replace(
                        "?", pragma_name.replace('"', '""')
                    )
                ).sa_text
            ) as cursor_result:
                return set(
                    SqlObject(
                        name=column_name, type=SqlObjectType.COLUMN, children=set()
                    )
                    for column_name in map(
                        lambda column_desc: column_desc[0],
                        cursor_result.cursor.description,
                    )
                )
        except OperationalError:
            return set()

    def _get_pragmas(self: "SqliteInspector", connection: Connection) -> Set[str]:
        return set(
            map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        "SELECT name FROM pragma_pragma_list();"
                    ).sa_text
                ).fetchall(),
            )
        )

    def _get_scalar_function_names(
        self: "SqliteInspector", connection: Connection
    ) -> Set[str]:
        return set(
            map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT DISTINCT
                            name
                        FROM
                            pragma_function_list();
                        """
                    ).sa_text
                ).fetchall(),
            )
        )

    def _get_tables_by_schema(
        self: "SqliteInspector", connection: Connection
    ) -> Set[SqlObject]:
        table_tree: Dict[str, Set[SqlObject]] = {}

        for schema_name, table_name, table_type in connection.execute(
            self.parent.make_query(
                """
                SELECT
                    schema, name, type
                FROM
                    pragma_table_list();
                """
            ).sa_text
        ).fetchall():
            # construct an object for this table with columns as children
            table_object: SqlObject = SqlObject(
                name=table_name,
                type=(
                    SqlObjectType.VIEW if table_type == "view" else SqlObjectType.TABLE
                ),
                children={
                    SqlObject(
                        name=column_name, type=SqlObjectType.COLUMN, children=set()
                    )
                    for column_name in self._get_column_names(
                        table_name, connection=connection
                    )
                },
            )

            if schema_name not in table_tree:
                table_tree[schema_name] = set()

            table_tree[schema_name].add(table_object)

        return {
            SqlObject(name=schema_name, type=SqlObjectType.SCHEMA, children=object_set)
            for schema_name, object_set in table_tree.items()
        }

    def refresh_structure(self: "SqliteInspector") -> None:
        connection: Connection = self.parent.make_connection()

        # construct the master structure object
        structure: SqlStructure = SqlStructure(
            dialect=generic_dialect_map[self.parent.dialect],
            objects=set(),
            keywords={
                SqlObject(name=keyword, type=SqlObjectType.KEYWORD, children=set())
                for keyword in self._sqlite_keywords
            },
            builtin_types={
                SqlObject(
                    name=datatype_name,
                    type=SqlObjectType.DATATYPE_BUILTIN,
                    children=set(),
                )
                for datatype_name in self._sqlite_types
            },
        )

        # add a list of pragmas as both explicit pragma objects and as tvfs
        for pragma_name in self._get_pragmas(connection=connection):
            returned_columns: Set[SqlObject] = self._get_pragma_columns(
                pragma_name, connection=connection
            )

            structure.objects.add(
                SqlObject(
                    name=pragma_name,
                    type=SqlObjectType.PRAGMA,
                    children=returned_columns,
                )
            )

            # also include as a tvf if the pragma returns columns
            if len(returned_columns) > 0:
                structure.objects.add(
                    SqlObject(
                        name=f"pragma_{pragma_name}()",
                        type=SqlObjectType.FUNCTION_TABLE_VALUED,
                        children=returned_columns,
                    )
                )

        # get all tables by schema and alias them at the global level
        for schema_object in self._get_tables_by_schema(connection=connection):
            structure.objects.add(schema_object)

            for child_table in schema_object.children:
                structure.objects.add(
                    SqlObject(
                        name=child_table.name,
                        type=child_table.type,
                        children=child_table.children,
                        is_alias=True,
                    )
                )

        # get a list of scalar functions
        for function_name in self._get_scalar_function_names(connection):
            structure.objects.add(
                SqlObject(
                    name=function_name.upper(),
                    type=SqlObjectType.FUNCTION_SCALAR,
                    children=set(),
                )
            )

        self.parent.parent.context.backends.prompt.refresh_structure(structure)
        connection.close()
