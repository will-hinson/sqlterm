from typing import Dict, List, Set

from Levenshtein import distance
from prompt_toolkit.contrib.completers.system import SystemCompleter
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from ..... import constants
from .....commands.sqltermcommand import _available_commands
from .....sql.generic.dataclasses import SqlStructure, SqlObject
from .....sql.generic.enums import SqlObjectType

_sql_object_type_short_names: Dict[SqlObjectType, str] = {
    SqlObjectType.CATALOG: "catalog",
    SqlObjectType.COLUMN: "column",
    SqlObjectType.DATABASE: "database",
    SqlObjectType.DATATYPE_BUILTIN: "type",
    SqlObjectType.DATATYPE_USER: "type*",
    SqlObjectType.FUNCTION: "func",
    SqlObjectType.FUNCTION_SCALAR: "func",
    SqlObjectType.FUNCTION_TABLE_VALUED: "tvf",
    SqlObjectType.KEYWORD: "keyword",
    SqlObjectType.PARAMETER: "param",
    SqlObjectType.PRAGMA: "pragma",
    SqlObjectType.PROCEDURE: "proc",
    SqlObjectType.SCHEMA: "schema",
    SqlObjectType.SYNONYM: "synonym",
    SqlObjectType.TABLE: "table",
    SqlObjectType.VIEW: "view",
}


class DefaultCompleter(Completer):
    inspector_structure: SqlStructure | None
    inspector_structure_flattened: Set[SqlObject] | None

    _system_completer: SystemCompleter

    def __init__(self: "DefaultCompleter") -> None:
        super().__init__()

        self.inspector_structure = None
        self.inspector_structure_flattened = None
        self._system_completer = SystemCompleter()

    def clear_completions(self: "DefaultCompleter") -> None:
        self.inspector_structure = None
        self.inspector_structure_flattened = None

    def get_completions(
        self: "DefaultCompleter", document: Document, complete_event: CompleteEvent
    ) -> List[Completion]:
        word_before_cursor = document.get_word_before_cursor().upper()
        if len(word_before_cursor) == 0:
            return []

        completions: List[Completion] = self._get_completions_unsorted(
            document, word_before_cursor, complete_event
        )
        completions.sort(
            key=lambda completion: distance(completion.text, word_before_cursor)
        )

        return completions

    def _get_completions_unsorted(
        self, document: Document, word_before_cursor: str, complete_event: CompleteEvent
    ) -> List[Completion]:
        match document.current_line[:1]:
            case constants.PREFIX_SHELL_COMMAND:
                return list(
                    self._system_completer.get_completions(
                        Document(
                            text=document.text[1:],
                            cursor_position=document.cursor_position - 1,
                        ),
                        complete_event,
                    )
                )
            case constants.PREFIX_SQLTERM_COMMAND:
                return self._get_completions_sqlterm_command(word_before_cursor)
            case _:
                return self._get_completions_ansi_sql(
                    word_before_cursor
                ) + self._get_completions_inspector(word_before_cursor)

    def _get_completions_inspector(
        self: "DefaultCompleter", word_before_cursor: str
    ) -> List[Completion]:
        if self.inspector_structure_flattened is None:
            return []

        # TODO: perform contextual completions here
        return [
            Completion(
                sql_object.name,
                start_position=-len(word_before_cursor),
                display_meta=(
                    _sql_object_type_short_names[sql_object.type]
                    if sql_object.type in _sql_object_type_short_names
                    else sql_object.type.name
                ),
            )
            for sql_object in self.inspector_structure_flattened
            if word_before_cursor.upper() in sql_object.name.upper()
            and sql_object.type not in {SqlObjectType.COLUMN, SqlObjectType.PARAMETER}
        ]

    def _get_completions_ansi_sql(
        self: "DefaultCompleter", word_before_cursor: str
    ) -> List[Completion]:
        return (
            [
                Completion(
                    keyword,
                    start_position=-len(word_before_cursor),
                    display_meta="keyword",
                )
                for keyword in constants.ANSI_SQL_KEYWORDS
                if keyword.upper().startswith(word_before_cursor)
            ]
            + [
                Completion(
                    keyword,
                    start_position=-len(word_before_cursor),
                    display_meta="function",
                )
                for keyword in constants.ANSI_SQL_FUNCTIONS
                if keyword.upper().startswith(word_before_cursor)
            ]
            if self.inspector_structure_flattened is None
            else []
        )

    def _get_completions_sqlterm_command(
        self: "DefaultCompleter", word_before_cursor: str
    ) -> List[Completion]:
        return [
            Completion(
                command, start_position=-len(word_before_cursor), display_meta="command"
            )
            for command in _available_commands
            if command.upper().startswith(word_before_cursor)
        ]

    def refresh_structure(self: "DefaultCompleter", structure: SqlStructure) -> None:
        self.inspector_structure = structure
        self.inspector_structure_flattened = self.inspector_structure.flatten()
