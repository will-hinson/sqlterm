from typing import Dict, Set

from pygments.lexers.sql import MySqlLexer
from pygments.token import Token
from sqlalchemy import Connection

from .....generic.dataclasses import SqlObject, SqlStructure
from .....generic.enums import SqlDialect, SqlObjectType
from .defaultinspector import DefaultInspector


class MySqlInspector(DefaultInspector):
    _mysql_keywords: Set[str] = {
        word.upper()
        for word_list in [
            token_tuple[0].words
            for token_tuple in MySqlLexer().tokens["root"]
            if token_tuple[1] == Token.Keyword and not isinstance(token_tuple[0], str)
        ]
        for word in word_list
    }

    _mysql_types: Set[str] = {
        word.upper()
        for word_list in [
            token_tuple[0].words
            for token_tuple in MySqlLexer().tokens["root"]
            if token_tuple[1] == Token.Keyword.Type
            and not isinstance(token_tuple[0], str)
        ]
        for word in word_list
    }

    def refresh_structure(self: "MySqlInspector") -> None:
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
                dialect=SqlDialect.MYSQL,
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
                    for keyword in self._mysql_keywords
                },
                builtin_types={
                    SqlObject(
                        type_name, type=SqlObjectType.DATATYPE_BUILTIN, children=set()
                    )
                    for type_name in self._mysql_types
                },
            )
        )
