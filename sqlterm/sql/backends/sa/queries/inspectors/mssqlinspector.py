from typing import Dict, Set, Tuple

from pygments.lexers.sql import TransactSqlLexer
from pygments.token import Token
from sqlalchemy import Connection, create_engine
from sqlalchemy.engine import Engine

from ...enums.sadialect import generic_dialect_map
from .....generic.dataclasses import SqlObject, SqlStructure
from .....generic.enums import SqlObjectType
from .sqlinspector import SqlInspector


class MsSqlInspector(SqlInspector):
    # derive a list of tsql functions from the pygments lexer
    _mssql_functions: Set[str] = {
        word.upper()
        for word_list in [
            token_tuple[0].words
            for token_tuple in TransactSqlLexer().tokens["root"]
            if token_tuple[1] == Token.Name.Function
        ]
        for word in word_list
    }

    _mssql_keywords: Set[str] = {
        "ADD",
        "ALL",
        "ALTER",
        "AND",
        "ANY",
        "AS",
        "ASC",
        "AUTHORIZATION",
        "BACKUP",
        "BEGIN",
        "BETWEEN",
        "BREAK",
        "BROWSE",
        "BULK",
        "BY",
        "CASCADE",
        "CASE",
        "CHECK",
        "CHECKPOINT",
        "CLOSE",
        "CLUSTERED",
        "COALESCE",
        "COLLATE",
        "COLUMN",
        "COMMIT",
        "COMPUTE",
        "CONSTRAINT",
        "CONTAINS",
        "CONTAINSTABLE",
        "CONTINUE",
        "CONVERT",
        "CREATE",
        "CROSS",
        "CURRENT",
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "CURRENT_USER",
        "CURSOR",
        "DATABASE",
        "DBCC",
        "DEALLOCATE",
        "DECLARE",
        "DEFAULT",
        "DELETE",
        "DENY",
        "DESC",
        "DISK",
        "DISTINCT",
        "DISTRIBUTED",
        "DOUBLE",
        "DROP",
        "DUMP",
        "ELSE",
        "END",
        "ERRLVL",
        "ESCAPE",
        "EXCEPT",
        "EXEC",
        "EXECUTE",
        "EXISTS",
        "EXIT",
        "EXTERNAL",
        "FETCH",
        "FILE",
        "FILLFACTOR",
        "FOR",
        "FOREIGN",
        "FREETEXT",
        "FREETEXTTABLE",
        "FROM",
        "FULL",
        "FUNCTION",
        "GOTO",
        "GRANT",
        "GROUP",
        "HAVING",
        "HOLDLOCK",
        "IDENTITY",
        "IDENTITYCOL",
        "IDENTITY_INSERT",
        "IF",
        "IN",
        "INDEX",
        "INNER",
        "INSERT",
        "INTERSECT",
        "INTO",
        "IS",
        "JOIN",
        "KEY",
        "KILL",
        "LEFT",
        "LIKE",
        "LINENO",
        "LOAD",
        "MERGE",
        "NATIONAL",
        "NOCHECK",
        "NONCLUSTERED",
        "NOT",
        "NULL",
        "NULLIF",
        "OF",
        "OFF",
        "OFFSETS",
        "ON",
        "OPEN",
        "OPENDATASOURCE",
        "OPENQUERY",
        "OPENROWSET",
        "OPENXML",
        "OPTION",
        "OR",
        "ORDER",
        "OUTER",
        "OVER",
        "PERCENT",
        "PIVOT",
        "PLAN",
        "PRECISION",
        "PRIMARY",
        "PRINT",
        "PROC",
        "PROCEDURE",
        "PUBLIC",
        "RAISERROR",
        "READ",
        "READTEXT",
        "RECONFIGURE",
        "REFERENCES",
        "REPLICATION",
        "RESTORE",
        "RESTRICT",
        "RETURN",
        "REVERT",
        "REVOKE",
        "RIGHT",
        "ROLLBACK",
        "ROWCOUNT",
        "ROWGUIDCOL",
        "RULE",
        "SAVE",
        "SCHEMA",
        "SECURITYAUDIT",
        "SELECT",
        "SEMANTICKEYPHRASETABLE",
        "SEMANTICSIMILARITYDETAILSTABLE",
        "SEMANTICSIMILARITYTABLE",
        "SESSION_USER",
        "SET",
        "SETUSER",
        "SHUTDOWN",
        "SOME",
        "STATISTICS",
        "SYSTEM_USER",
        "TABLE",
        "TABLESAMPLE",
        "TEXTSIZE",
        "THEN",
        "TO",
        "TOP",
        "TRAN",
        "TRANSACTION",
        "TRIGGER",
        "TRUNCATE",
        "TRY_CONVERT",
        "TSEQUAL",
        "TYPE",
        "UNION",
        "UNIQUE",
        "UNPIVOT",
        "UPDATE",
        "UPDATETEXT",
        "USE",
        "USER",
        "VALUES",
        "VARYING",
        "VIEW",
        "WAITFOR",
        "WHEN",
        "WHERE",
        "WHILE",
        "WITH",
        "WITHIN",
        "WRITETEXT",
    }

    _mssql_object_type_map: Dict[str, SqlObjectType] = {
        "CLR_SCALAR_FUNCTION": SqlObjectType.FUNCTION_SCALAR,
        "CLR_STORED_PROCEDURE": SqlObjectType.PROCEDURE,
        "CLR_TABLE_VALUED_FUNCTION": SqlObjectType.FUNCTION_TABLE_VALUED,
        "EXTENDED_STORED_PROCEDURE": SqlObjectType.PROCEDURE,
        "SQL_INLINE_TABLE_VALUED_FUNCTION": SqlObjectType.FUNCTION_TABLE_VALUED,
        "SQL_SCALAR_FUNCTION": SqlObjectType.FUNCTION_SCALAR,
        "SQL_STORED_PROCEDURE": SqlObjectType.PROCEDURE,
        "SQL_TABLE_VALUED_FUNCTION": SqlObjectType.FUNCTION_TABLE_VALUED,
        "SYNONYM": SqlObjectType.SYNONYM,
        "TABLE_TYPE": SqlObjectType.DATATYPE_USER,
        "USER_TABLE": SqlObjectType.TABLE,
        "VIEW": SqlObjectType.VIEW,
    }

    def _get_builtin_types(
        self: "MsSqlInspector", connection: Connection
    ) -> Set[SqlObject]:
        return {
            SqlObject(
                name=type_name, type=SqlObjectType.DATATYPE_BUILTIN, children=set()
            )
            for type_name in map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT DISTINCT
                            UPPER([name])
                        FROM
                            sys.types
                        WHERE
                            [is_user_defined] = 0;
                        """
                    ).sa_text
                ).fetchall(),
            )
        }

    def _get_children_for(
        self: "MsSqlInspector",
        sql_object: SqlObject,
        database_name: str,
        object_id: int,
        connection: Connection,
    ) -> Set[SqlObject]:
        match sql_object.type:
            case SqlObjectType.PROCEDURE:
                return self._get_children_for_procedure(
                    database_name, object_id, connection=connection
                )
            case SqlObjectType.TABLE:
                return self._get_children_for_table(
                    database_name, object_id, connection=connection
                )
            case _:
                return set()

    def _get_children_for_procedure(
        self: "MsSqlInspector",
        database_name: str,
        object_id: int,
        connection: Connection,
    ) -> Set[SqlObject]:
        return {
            SqlObject(name=parameter_name, type=SqlObjectType.PARAMETER, children=set())
            for parameter_name in map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT DISTINCT
                            [name]
                        FROM
                            sys.parameters
                        WHERE
                            [object_id] = id?;
                        """.replace(
                            "id?", str(object_id)
                        )
                    ).sa_text
                ).fetchall(),
            )
        }

    def _get_children_for_table(
        self: "MsSqlInspector",
        database_name: str,
        object_id: int,
        connection: Connection,
    ) -> Set[SqlObject]:
        return {
            SqlObject(name=column_name, type=SqlObjectType.COLUMN, children=set())
            for column_name in map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT DISTINCT
                            [name]
                        FROM
                            "db?".sys.columns
                        WHERE
                            [object_id] = id?;
                        """.replace(
                            "db?", database_name.replace('"', '""')
                        ).replace(
                            "id?", str(object_id)
                        ),
                    ).sa_text
                ).fetchall(),
            )
        }

    def _get_database_names(self: "MsSqlInspector", connection: Connection) -> Set[str]:
        return set(
            map(
                lambda row: row[0],
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT DISTINCT
                            name
                        FROM
                            sys.databases;
                        """
                    ).sa_text
                ).fetchall(),
            )
        )

    def _get_database_objects(
        self: "MsSqlInspector", database_name: str, connection: Connection
    ) -> Set[Tuple[int, str, str, str]]:
        return set(
            map(
                tuple,
                connection.execute(
                    self.parent.make_query(
                        """
                        SELECT
                            a.[object_id],
                            schema_name = b.[name],
                            object_name = a.[name],
                            a.[type_desc]
                        FROM
                            "?".sys.all_objects AS a
                        LEFT JOIN "?".sys.schemas AS b ON
                            a.[schema_id] = b.[schema_id]
                        WHERE
                            a.[type_desc] IN (
                                'CLR_SCALAR_FUNCTION',
                                'CLR_STORED_PROCEDURE',
                                'CLR_TABLE_VALUED_FUNCTION',
                                'EXTENDED_STORED_PROCEDURE',
                                'SQL_INLINE_TABLE_VALUED_FUNCTION',
                                'SQL_SCALAR_FUNCTION',
                                'SQL_STORED_PROCEDURE',
                                'SQL_TABLE_VALUED_FUNCTION',
                                'SYNONYM',
                                'TABLE_TYPE',
                                'USER_TABLE',
                                'VIEW'
                            );
                        """.replace(
                            "?", database_name.replace('"', '""')
                        )
                    ).sa_text
                ).fetchall(),
            )
        )

    def _map_database(
        self: "MsSqlInspector", database_name: str, connection: Connection
    ) -> Set[SqlObject]:
        schema_objects: Dict[str, Set[SqlObject]] = {}

        for (
            object_id,
            schema_name,
            object_name,
            type_desc,
        ) in self._get_database_objects(database_name, connection=connection):
            # ensure a child set exists for this schema
            if schema_name not in schema_objects:
                schema_objects[schema_name] = set()

            # construct the sql object and get children for it if possible
            sql_object: SqlObject = SqlObject(
                name=object_name,
                type=self._mssql_object_type_map[type_desc],
                children=set(),
            )
            sql_object.children = self._get_children_for(
                sql_object,
                database_name=database_name,
                object_id=object_id,
                connection=connection,
            )

            # add the sql object as a child of this schema
            schema_objects[schema_name].add(sql_object)

        return {
            SqlObject(
                name=schema_name, type=SqlObjectType.SCHEMA, children=child_object_set
            )
            for schema_name, child_object_set in schema_objects.items()
        }

    def refresh_structure(self: "MsSqlInspector") -> None:
        connection: Connection = self.parent.make_connection()

        structure: SqlStructure = SqlStructure(
            dialect=generic_dialect_map[self.parent.dialect],
            objects=set(),
            keywords={
                SqlObject(name=keyword, type=SqlObjectType.KEYWORD, children=set())
                for keyword in self._mssql_keywords
            },
            builtin_types=self._get_builtin_types(connection),
        )

        # map all of the constituent databases
        for database_name in self._get_database_names(connection):
            structure.objects.add(
                SqlObject(
                    name=database_name,
                    type=SqlObjectType.DATABASE,
                    children=self._map_database(database_name, connection=connection),
                )
            )

        self.parent.parent.context.backends.prompt.refresh_structure(structure)
        connection.close()
