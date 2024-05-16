import functools
import shutil
import time
import traceback
from typing import Any, Callable, Dict, Iterable, List, Tuple

from prompt_toolkit import (
    print_formatted_text,
    prompt,
    PromptSession,
    shortcuts,
)
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import ScrollablePane
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.processors import Processor, TabsProcessor
from prompt_toolkit.styles import (
    BaseStyle,
    merge_styles,
    Style,
    style_from_pygments_cls,
)
from prompt_toolkit.validation import Validator, ValidationError
from pygments.styles import get_style_by_name, get_all_styles
from pygments.token import Token
import sqlparse

from .... import constants
from ...abstract.promptbackend import PromptBackend
from .completers import DefaultCompleter
from ....config import SqlTermConfig
from .controls import ObjectBrowser, SqlObjectView, SelectionCursorShapeConfig
from ...dataclasses import InputModel, SqlReference, SqlStatusDetails, Suggestion
from ...enums import PromptType
from ...exceptions import UserExit
from ....sql.generic.dataclasses import SqlObject, SqlStructure
from ....sql.generic.enums.sqldialect import SqlDialect
from ....sql.exceptions import DisconnectedException
from .sqltermlexer import SqlTermLexer


class _InputModelCompleter(Completer):
    __completer_func: Callable[[str, str, int], List[Suggestion]] | None

    def __init__(
        self: "_InputModelCompleter",
        completer_func: Callable[[str, str, int], List[Suggestion]] | None,
    ) -> None:
        super().__init__()

        self.__completer_func = completer_func

    def get_completions(self: "_InputModelCompleter", document: Document, _):
        if self.__completer_func is None:
            return []

        word_before_cursor = document.get_word_before_cursor()
        input_model_suggestions: List[Suggestion] = self.__completer_func(
            document.text, word_before_cursor, document.cursor_position_col
        )

        return [
            Completion(
                suggestion.content,
                start_position=suggestion.position,
                display_meta=suggestion.suffix,
            )
            for suggestion in input_model_suggestions
        ]


class _InputModelValidator(Validator):
    __validate_func: Callable[[str], str | None] | None

    def __init__(
        self: "_InputModelValidator", validate_func: Callable[[str], str | None] | None
    ) -> None:
        self.__validate_func = validate_func

    def validate(self: "_InputModelValidator", document: Document) -> None:
        if self.__validate_func is not None:
            if (error_message := self.__validate_func(document.text)) is not None:
                raise ValidationError(document.cursor_position, message=error_message)


class PromptToolkitBackend(PromptBackend):
    __completer: DefaultCompleter
    __lexer: SqlTermLexer
    __session: PromptSession
    __current_statement_index: int

    __dialect_escape_chars: Dict[SqlDialect, str] = {
        SqlDialect.GENERIC: '"',
        SqlDialect.MYSQL: "`",
        SqlDialect.POSTGRES: '"',
        SqlDialect.SQLITE: '"',
        SqlDialect.TSQL: '"',
    }

    def __init__(
        self: "PromptToolkitBackend",
        config: SqlTermConfig,
        *args: Tuple,
        **kwargs: Dict,
    ) -> None:
        super().__init__(config=config)

        self.__completer = DefaultCompleter()
        self.__lexer = self._default_lexer

        self.__session = PromptSession(
            *args,  # type: ignore
            bottom_toolbar=functools.partial(type(self)._get_bottom_toolbar, self=self),
            input_processors=self._default_input_processors,
            key_bindings=self._default_key_bindings,
            lexer=self.__lexer,
            multiline=True,
            prompt_continuation=self._prompt_continuation,  # type: ignore
            style=merge_styles(
                [
                    self._default_style,
                    style_from_pygments_cls(self._get_style_for_config()),
                ]
            ),
            completer=self.__completer,
            cursor=SelectionCursorShapeConfig(),
            **kwargs,
        )
        self.__current_statement_index = 0
        shortcuts.clear()

    def change_dialect(self: "PromptToolkitBackend", dialect: SqlDialect) -> None:
        self._dialect = dialect

    def clear_completions(self: "PromptToolkitBackend") -> None:
        self.__completer.clear_completions()

    @property
    def _default_input_processors(self: "PromptToolkitBackend") -> List[Processor]:
        return [TabsProcessor()]

    @property
    def _default_key_bindings(self: "PromptToolkitBackend") -> KeyBindings:
        bindings: KeyBindings = KeyBindings()

        def insert_newline(buffer: Buffer) -> None:
            if buffer.document.current_line_after_cursor:
                # When we are in the middle of a line. Always insert a newline.
                buffer.insert_text("\n")
            else:
                current_line: str = buffer.document.current_line_before_cursor.rstrip()
                buffer.insert_text("\n")

                # insert spaces to match the previous indentation level. if there's a semicolon,
                # dedent one level
                space_count: int = 0
                for char in current_line:
                    if char.isspace():
                        space_count += 1
                    else:
                        break

                buffer.insert_text(
                    " "
                    * (
                        space_count
                        # auto-dedent when it looks like a statement is completed
                        - (
                            constants.SPACES_IN_TAB
                            if current_line.strip().endswith(";")
                            else 0
                        )
                    )
                )

        def selected_lines(event: KeyPressEvent) -> List[int]:
            start_pos, end_pos = event.current_buffer.document.selection_range()

            begin_line: int = -1
            end_line: int = -1
            char_index: int = 0

            for index, line in enumerate(event.current_buffer.document.lines):
                if start_pos in range(char_index, char_index + len(line) + 1):
                    begin_line = index
                if end_pos in range(char_index, char_index + len(line) + 1):
                    end_line = index

                char_index += len(line) + 1

                if begin_line > -1 and end_line > -1:
                    break

            return list(range(begin_line, end_line + 1))

        # NOTE: we have to have our own bindings here as the Alt-Up/Down combination can perform
        # a selection that won't cancel for whatever reason. this ensures that the arrow keys will
        # always cancel an active selection without a shift modifier
        @bindings.add(Keys.Down)
        def binding_arrow_down(event: KeyPressEvent) -> None:
            event.current_buffer.exit_selection()
            event.current_buffer.auto_down()

        @bindings.add(Keys.Left)
        def binding_arrow_left(event: KeyPressEvent) -> None:
            event.current_buffer.exit_selection()
            event.current_buffer.cursor_left()

        @bindings.add(Keys.Right)
        def binding_arrow_right(event: KeyPressEvent) -> None:
            event.current_buffer.exit_selection()
            event.current_buffer.cursor_right()

        @bindings.add(Keys.Up)
        def binding_arrow_up(event: KeyPressEvent) -> None:
            event.current_buffer.exit_selection()
            event.current_buffer.auto_up()

        @bindings.add("backspace")
        def binding_backspace(event: KeyPressEvent) -> None:
            # check if there is text currently selected that the user is trying to
            # delete by pressing backspace
            if event.current_buffer.document.selection is not None:
                buffer = event.current_buffer
                selection_start, selection_end = buffer.document.selection_range()

                buffer.exit_selection()
                buffer.document = Document(
                    buffer.document.text[:selection_start]
                    + buffer.document.text[selection_end:]
                )

                buffer.cursor_position = selection_start
                buffer.selection_state = None

                return

            # check if the preceding set of four characters is all spaces. if so,
            # this is a tab equivalent and should be removed as a group
            if (
                (
                    preceding_line_length := len(
                        event.app.current_buffer.document.current_line_before_cursor
                    )
                )
                > 0
                and preceding_line_length % 4 == 0
                and all(
                    char == " "
                    for char in event.app.current_buffer.document.current_line_before_cursor[
                        preceding_line_length
                        - (
                            constants.SPACES_IN_TAB
                            if preceding_line_length % constants.SPACES_IN_TAB == 0
                            else preceding_line_length % constants.SPACES_IN_TAB
                        ) :
                    ]
                )
            ):
                # remove the tab equivalent
                event.current_buffer.delete_before_cursor(
                    (
                        constants.SPACES_IN_TAB
                        if preceding_line_length % constants.SPACES_IN_TAB == 0
                        else preceding_line_length % constants.SPACES_IN_TAB
                    )
                )
            else:
                # otherwise, just remove an individual character like a regular backspace
                event.current_buffer.delete_before_cursor()

        @bindings.add("c-b")
        def binding_ctrl_b(event: KeyPressEvent) -> None:
            try:
                dialect_escape_char: str = (
                    self.__dialect_escape_chars[self.dialect]
                    if self.dialect in self.__dialect_escape_chars
                    else '"'
                )
                object_browser_result: SqlReference | None = (
                    self.display_object_browser(show_loading=False)
                )

                if object_browser_result is not None:
                    event.current_buffer.insert_text(
                        ".".join(
                            dialect_escape_char
                            + sql_object.name.replace(
                                dialect_escape_char, dialect_escape_char * 2
                            )
                            + dialect_escape_char
                            for sql_object in object_browser_result.hierarchy
                        )
                    )
            except DisconnectedException:
                ...

        # NOTE: disable the default i-search
        @bindings.add("c-s")
        def binding_ctrl_s(_: KeyPressEvent) -> None: ...

        @bindings.add("enter")
        def binding_enter(event: KeyPressEvent) -> None:
            # check for a blank line or a shell or sqlterm command (also, show help if the user enters 'help')
            current_text_stripped: str = event.current_buffer.text.strip()
            if len(current_text_stripped) == 0 or current_text_stripped[:1] in (
                constants.PREFIX_SHELL_COMMAND,
                constants.PREFIX_SQLTERM_COMMAND,
            ):
                event.current_buffer.validate_and_handle()
                return
            elif current_text_stripped.lower() == "help":
                event.current_buffer.text = "%help"
                event.current_buffer.validate_and_handle()
                return

            # check if this is a blank last line and the previous line ends with ';'
            if (
                len(event.current_buffer.document.current_line) == 0
                and event.current_buffer.document.on_last_line
                and current_text_stripped.endswith(";")
            ) or (
                event.current_buffer.document.line_count == 1
                and current_text_stripped.endswith(";")
                and event.current_buffer.cursor_position
                == len(event.current_buffer.document.text)
            ):
                event.current_buffer.validate_and_handle()
            else:
                insert_newline(event.current_buffer)

        @bindings.add(Keys.Escape)
        def binding_escape(event: KeyPressEvent) -> None:
            current_buffer = event.app.current_buffer
            current_buffer.cancel_completion()

            if current_buffer.complete_state is not None:
                current_buffer.complete_state.completions = []

        @bindings.add(Keys.Escape, Keys.Down)
        def binding_alt_down_arrow(event: KeyPressEvent) -> None:
            # get a list of the currently selected lines
            orig_cursor_position: int | None = (
                event.current_buffer.document.selection.original_cursor_position
                if event.current_buffer.document.selection is not None
                else None
            )
            selection_start, selection_end = (
                event.current_buffer.document.selection_range()
            )
            line_indexes: List[int] = selected_lines(event)

            # check if the first selected line is the last overall line and do nothing if so
            if line_indexes[-1] == len(event.app.current_buffer.document.lines) - 1:
                return

            # swap the current lines with the next one
            next_line: str = event.app.current_buffer.document.lines[
                line_indexes[-1] + 1
            ]
            current_lines: List[str] = [
                event.app.current_buffer.document.lines[line_index]
                for line_index in line_indexes
            ]
            cursor_col: int = event.app.current_buffer.document.cursor_position_col
            cursor_line: int = event.app.current_buffer.document.cursor_position_row

            event.app.current_buffer.text = "\n".join(
                event.app.current_buffer.document.lines[: line_indexes[0]]
                + [next_line, *current_lines]
                + event.app.current_buffer.document.lines[line_indexes[-1] + 2 :]
            )

            # check if there was originally a selection
            if orig_cursor_position is None:
                # seek to column 0
                event.app.current_buffer.cursor_position -= (
                    event.app.current_buffer.document.cursor_position_col
                )

                # check if the cursor moved down or not. if it didn't, seek down a line
                if cursor_line == event.app.current_buffer.document.cursor_position_row:
                    event.app.current_buffer.cursor_down()

                # seek to the old column where the cursor was
                event.app.current_buffer.cursor_right(cursor_col)
            else:
                # if there was a selection, recreate the selection on the new relative lines
                event.app.current_buffer.cursor_position = (
                    orig_cursor_position + len(next_line) + 1
                )
                event.app.current_buffer.start_selection()
                event.app.current_buffer.cursor_position = (
                    selection_start + len(next_line) + 1
                    if selection_start < orig_cursor_position
                    else selection_end + len(next_line) + 1
                )

        @bindings.add(Keys.Escape, Keys.Up)
        def binding_alt_up_arrow(event: KeyPressEvent) -> None:
            # check if we're already on the first line and do nothing if so
            if event.app.current_buffer.document.on_first_line:
                return

            # get a list of the currently selected lines
            orig_cursor_position: int | None = (
                event.current_buffer.document.selection.original_cursor_position
                if event.current_buffer.document.selection is not None
                else None
            )
            selection_start, selection_end = (
                event.current_buffer.document.selection_range()
            )
            line_indexes: List[int] = selected_lines(event)

            # check if the first selected line is the first overall line and do nothing if so
            if line_indexes[0] == 0:
                return

            # swap the current line with the previous one
            prev_line: str = event.app.current_buffer.document.lines[
                line_indexes[0] - 1
            ]
            # current_line: str = event.app.current_buffer.document.current_line
            current_lines: List[str] = [
                event.app.current_buffer.document.lines[line_index]
                for line_index in line_indexes
            ]
            cursor_col: int = event.app.current_buffer.document.cursor_position_col
            cursor_line: int = event.app.current_buffer.document.cursor_position_row

            event.app.current_buffer.text = "\n".join(
                event.app.current_buffer.document.lines[: line_indexes[0] - 1]
                + [*current_lines, prev_line]
                + event.app.current_buffer.document.lines[line_indexes[-1] + 1 :]
            )

            # check if there was originally a selection
            if orig_cursor_position is None:
                # seek to column 0
                event.app.current_buffer.cursor_position -= (
                    event.app.current_buffer.document.cursor_position_col
                )

                # check if the cursor moved up or not. if it didn't, seek up a line
                if cursor_line == event.app.current_buffer.document.cursor_position_row:
                    event.app.current_buffer.cursor_up()

                # seek to the old column where the cursor was
                event.app.current_buffer.cursor_right(cursor_col)
            else:
                # if there was a selection, recreate the selection on the new relative lines
                event.app.current_buffer.cursor_position = (
                    orig_cursor_position - len(prev_line) - 1
                )
                event.app.current_buffer.start_selection()
                event.app.current_buffer.cursor_position = (
                    selection_start - len(prev_line) - 1
                    if selection_start < orig_cursor_position
                    else selection_end - len(prev_line) - 1
                )

        @bindings.add("tab")
        def binding_tab(event: KeyPressEvent) -> None:
            # check if there is a multiline selection and indent all lines if so
            if (
                event.app.current_buffer.selection_state is not None
                and len(target_lines := selected_lines(event)) > 1
            ):
                event.current_buffer.text = event.current_buffer.transform_lines(
                    target_lines,
                    lambda line: (
                        " "
                        * (
                            (
                                constants.SPACES_IN_TAB
                                - (len(line) - len(line.lstrip(" ")))
                                % constants.SPACES_IN_TAB
                            )
                        )
                    )
                    + line,
                )
                return

            # map tab to four spaces
            event.app.current_buffer.insert_text(
                " "
                * (
                    constants.SPACES_IN_TAB
                    - (
                        event.app.current_buffer.document.cursor_position_col
                        % constants.SPACES_IN_TAB
                    )
                )
            )

        @bindings.add(Keys.F5)
        def binding_f5(event: KeyPressEvent) -> None:
            event.current_buffer.validate_and_handle()

        @bindings.add("c-t")
        def binding_ctrl_t(event: KeyPressEvent) -> None:
            event.current_buffer.document = Document(
                sqlparse.format(
                    event.current_buffer.document.text,
                    reindent=True,
                    indent_columns=True,
                    indent_width=4,
                    keyword_case="upper",
                    use_space_around_operators=True,
                )
            )

        @bindings.add(Keys.ControlR)
        def binding_ctrl_r(_: KeyPressEvent) -> None:
            self.parent.invalidate_completions()

        return bindings

    @property
    def _default_lexer(self: "PromptToolkitBackend") -> SqlTermLexer:
        return SqlTermLexer(parent=self)

    @property
    def _default_style(self: "PromptToolkitBackend") -> BaseStyle:
        # pylint: disable=protected-access
        style_for_config = self._get_style_for_config()
        colors: Dict[Any, str] = {
            token_type: (
                style_for_config._styles[token_type][0]  # type: ignore
                if style_for_config._styles[token_type][0] != ""  # type: ignore
                else "ffffff"
            )
            for token_type in (
                Token.Error,
                Token.Keyword,
                Token.Literal.String.Symbol,
                Token.Name.Builtin,
                Token.Text,
            )
        }
        # pylint: enable=protected-access

        return Style.from_dict(
            {
                "bottom-toolbar": f"bg:#222222 fg:#{colors[Token.Literal.String.Symbol]} noreverse",
                "bottom-toolbar.icon": (
                    f"bg:#222222 fg:#{colors[Token.Name.Builtin]} noreverse"
                ),
                "bottom-toolbar.info": f"fg:#{colors[Token.Text]}",
                "bottom-toolbar.text": "fg:darkgray",
                "error.type": "fg:ansibrightred",
                "error.message": "fg:ansibrightred",
                "prompt-cell.bracket": f"fg:#{colors[Token.Text]}",
                "prompt-cell.number": f"fg:#{colors[Token.Name.Builtin]} bold",
                "line-number": "fg:darkgray",
                "message.info": "fg:darkgray",
                "message.progress": f"fg:#{colors[Token.Literal.String.Symbol]}",
                "message.sql": f"fg:#{colors[Token.Name.Builtin]}",
                "object-browser.icon-expand": "fg:darkgray",
                "object-browser.icon-column": "fg:whitesmoke",
                "object-browser.icon-collapse": "fg:darkgray",
                "object-browser.icon-database": "fg:cadetblue",
                "object-browser.icon-function-scalar": "fg:springgreen",
                "object-browser.icon-function-table-valued": "fg:palegreen",
                "object-browser.icon-parameter": "fg:cornsilk",
                "object-browser.icon-procedure": "fg:gold",
                "object-browser.icon-schema": "fg:navajowhite",
                "object-browser.icon-table": "fg:skyblue",
                "object-browser.icon-view": "fg:salmon",
                "object-browser.object-name": "fg:azure",
                "shell.command": f"fg:#{colors[Token.Keyword]} bold",
                "shell.command-args": f"fg:#{colors[Token.Text]} italic",
                "shell.command-sigil": f"fg:#{colors[Token.Literal.String.Symbol]} bold",
            }
        )

    def display_exception(
        self: "PromptToolkitBackend", exception: Exception, unhandled: bool = False
    ) -> None:
        if not unhandled:
            print_formatted_text(
                FormattedText(
                    [
                        ("class:error.type", f"{type(exception).__name__}: "),
                        (
                            "class:error.message",
                            "\n".join(str(arg) for arg in exception.args),
                        ),
                    ]
                ),
                style=self.session.style,
            )
        else:
            print_formatted_text(
                FormattedText(
                    [
                        (
                            "class:error.message",
                            "\n".join(
                                line.strip("\n")
                                for line in traceback.format_exception(exception)
                            ),
                        )
                    ]
                ),
                style=self._default_style,
            )

    def display_info(self: "PromptToolkitBackend", info: str) -> None:
        print_formatted_text(
            FormattedText([("class:message.info", info)]),
            style=self._default_style,
        )

    def display_message_sql(self: "PromptToolkitBackend", message: str) -> None:
        print_formatted_text(
            FormattedText(
                [
                    ("class:message.sql", message),
                ]
            ),
            style=self._default_style,
        )

    def display_object_browser(
        self: "PromptToolkitBackend", show_loading: bool
    ) -> SqlReference | None:
        # ensure that we actually have a sql connection
        if not self.parent.context.backends.sql.connected:
            raise DisconnectedException(
                "There is no active SQL connection. Cannot display object browser."
            )

        # wait until the the sql backend is done inspecting
        self.hide_cursor()
        load_char_offset: int = 0
        while self.parent.context.backends.sql.inspecting:
            if show_loading:
                self.display_progress(
                    constants.PROGRESS_CHARACTERS[load_char_offset],
                    " Inspecting database objects...",
                )

                load_char_offset = (load_char_offset + 1) % len(
                    constants.PROGRESS_CHARACTERS
                )

            time.sleep(0.1)

        if show_loading:
            print("\r", end="")
            print(" " * (shutil.get_terminal_size().columns - 1), end="")
            print("\r", end="")

        self.show_cursor()

        return self._show_object_browser(self.__completer.inspector_structure)

    def display_progress(self: "PromptToolkitBackend", *progress_messages: str) -> None:
        print_formatted_text(
            FormattedText(
                [
                    ("class:message.progress", progress_message)
                    for progress_message in progress_messages
                ]  # type: ignore
            ),
            style=self._default_style,
            end="",
        )

        # NOTE: print_formatted_text() doesn't allow '\r' as an end string so
        # we have to write it manually here
        print(end="\r")

    def display_table(self: "PromptToolkitBackend", table: str) -> None:
        print(table)

    def _get_bottom_toolbar(self: "PromptToolkitBackend") -> List[Tuple]:
        status_details: SqlStatusDetails = self.parent.context.backends.sql.get_status()

        if status_details.connected:
            return [
                (
                    "class:bottom-toolbar.icon",
                    "\U0001f5a7 ",
                ),
                ("class:bottom-toolbar.info", status_details.connection_detail),
                ("class:bottom-toolbar.info", " "),
                ("class:bottom-toolbar.text", f"({status_details.dialect})"),
            ]
        else:
            return [
                ("class:bottom-toolbar.icon", "\u2a2f"),
                ("class:bottom-toolbar.info", " Disconnected"),
            ]

    def get_command(
        self: "PromptToolkitBackend", initial_input: str | None = None
    ) -> str:
        self.__current_statement_index += 1

        try:
            return self.session.prompt(
                [
                    ("class:prompt-cell.bracket", "["),
                    ("class:prompt-cell.number", str(self.__current_statement_index)),
                    ("class:prompt-cell.bracket", "]"),
                    ("", " " * (2 if self.__current_statement_index < 10 else 1)),
                ],
                default=initial_input if initial_input is not None else "",
            )
        except EOFError as eof:
            raise UserExit("EOFError while prompting for input") from eof
        except KeyboardInterrupt:
            return ""

    def _get_style_for_config(self: "PromptToolkitBackend") -> None:
        return (
            get_style_by_name(self.config.color_scheme)
            if self.config.color_scheme in get_all_styles()
            else get_style_by_name("dracula")
        )

    def hide_cursor(self: "PromptToolkitBackend") -> None:
        self.session.app.output.hide_cursor()

    def _prompt_continuation(
        self, width: int, line_number: int, is_soft_wrap: bool
    ) -> List[Tuple[str, str]]:
        if (
            not is_soft_wrap
            and len(line_number_str := str(line_number + 1)) < width - 1
        ):
            return [
                (
                    "class:line-number",
                    line_number_str.rjust(width - 2) + "  ",
                )
            ]

        return [("", "...".ljust(width))]

    def prompt_for(
        self: "PromptToolkitBackend", prompt_series: Iterable[InputModel]
    ) -> List[Any]:
        return [
            self._prompt_for_input_model(input_model) for input_model in prompt_series
        ]

    def _prompt_for_input_model(
        self: "PromptToolkitBackend", input_model: InputModel
    ) -> Any:
        match input_model.type:
            case PromptType.BASIC:
                return self._prompt_for_str(
                    input_model,
                    completer=_InputModelCompleter(input_model.completer),
                    validator=_InputModelValidator(input_model.validator),
                )
            case PromptType.PASSWORD:
                return self._prompt_for_str(
                    input_model,
                    completer=_InputModelCompleter(input_model.completer),
                    validator=_InputModelValidator(input_model.validator),
                    is_password=True,
                )
            case PromptType.YES_NO:
                return self._prompt_for_yes_no(input_model)
            case _:
                raise NotImplementedError(
                    f"Prompt type {input_model.type} not implemented"
                )

    def _prompt_for_str(
        self: "PromptToolkitBackend",
        input_model: InputModel,
        validator: Validator | None = None,
        completer: Completer | None = None,
        **kwargs,
    ) -> str:
        return prompt(
            message=[("class:prompt-cell.bracket", input_model.prompt)],
            multiline=False,
            completer=completer,
            validator=validator,
            validate_while_typing=False,
            style=merge_styles(
                [
                    self.session.style,  # type: ignore
                    Style.from_dict({"": "fg:darkgray"}),
                ]
            ),
            bottom_toolbar=self.session.bottom_toolbar,
            **kwargs,
        )

    _yes_no_values: Dict[str, bool] = {"y": True, "yes": True, "n": False, "no": False}

    def _prompt_for_yes_no(
        self: "PromptToolkitBackend", input_model: InputModel
    ) -> bool:
        modified_model: InputModel = InputModel(
            input_model.prompt + " [y/n] ", input_model.type, None, None
        )

        def _yes_no_validator(user_input: str) -> str | None:
            if user_input.lower().strip() not in self._yes_no_values:
                return "Error: Please enter 'yes' or 'no'"

        return self._yes_no_values[
            self._prompt_for_str(
                modified_model, validator=_InputModelValidator(_yes_no_validator)
            )
            .lower()
            .strip()
        ]

    def refresh_structure(
        self: "PromptToolkitBackend", structure: SqlStructure
    ) -> None:
        self.__completer.refresh_structure(structure)

    @property
    def session(self: "PromptToolkitBackend") -> PromptSession:
        return self.__session

    def show_cursor(self: "PromptToolkitBackend") -> None:
        self.session.app.output.hide_cursor()

    def _build_object_browser(
        self: "PromptToolkitBackend", structure: SqlStructure
    ) -> ObjectBrowser:
        bindings: KeyBindings = KeyBindings()

        object_browser_layout: Layout = Layout(
            HSplit(
                [
                    ScrollablePane(
                        objects_hsplit := HSplit(
                            [
                                SqlObjectView(root_object, index)
                                for index, root_object in enumerate(
                                    filter(
                                        lambda root_object: not root_object.builtin,
                                        sorted(
                                            structure.objects,
                                            key=lambda sql_object: sql_object.name,
                                        ),
                                    )
                                )
                            ]
                        )
                    ),
                    VSplit(
                        [
                            Window(
                                content=FormattedTextControl(
                                    self._get_bottom_toolbar()
                                ),
                                height=1,
                                style="class:bottom-toolbar",
                                align=WindowAlign.LEFT,
                            ),
                            Window(
                                content=FormattedTextControl(
                                    [
                                        ("", "[Arrows] Navigate"),
                                        ("", " "),
                                        ("", "[^S] Search"),
                                        ("", " "),
                                        ("", "[q] Quit"),
                                    ]
                                ),
                                height=1,
                                style="class:bottom-toolbar",
                                align=WindowAlign.RIGHT,
                            ),
                        ]
                    ),
                ]
            )
        )

        # store a reference to the parent hsplit in all sqlobjectviews
        for child in objects_hsplit.children:
            child.parent = objects_hsplit

        focus_index: int = 0

        @bindings.add(Keys.Enter)
        def binding_accept(event: KeyPressEvent) -> None:
            nonlocal focus_index

            current_index: int = focus_index
            current_hierarchy_level: int = objects_hsplit.children[
                current_index
            ].indent_level
            object_hierarchy: List[SqlObject] = [
                objects_hsplit.children[current_index].sql_object
            ]
            while current_hierarchy_level > 0 and current_index > 0:
                current_object: SqlObjectView = objects_hsplit.children[current_index]
                if (
                    new_hierarchy_level := current_object.indent_level
                ) < current_hierarchy_level:
                    current_hierarchy_level = new_hierarchy_level
                    object_hierarchy.append(current_object.sql_object)

                current_index -= 1

            object_hierarchy.reverse()
            event.app.result = SqlReference(hierarchy=object_hierarchy)
            event.app.exit()

        @bindings.add(Keys.Left)
        def binding_collapse_or_find_parent(event: KeyPressEvent) -> None:
            nonlocal focus_index
            focus_index = objects_hsplit.children[focus_index].collapse_or_find_parent(
                event.app.layout
            )

        @bindings.add(Keys.Right)
        def binding_expand(_: KeyPressEvent) -> None:
            nonlocal focus_index
            objects_hsplit.children[focus_index].expand_if_collapsed()

        @bindings.add("space")
        def binding_expand_or_collapse(_: KeyPressEvent) -> None:
            nonlocal focus_index
            objects_hsplit.children[focus_index].toggle_collapse()

        @bindings.add(Keys.Down)
        def binding_next_object(event: KeyPressEvent) -> None:
            nonlocal focus_index
            focus_index = min(focus_index + 1, len(objects_hsplit.children) - 1)
            event.app.layout.focus(objects_hsplit.children[focus_index])

        @bindings.add(Keys.Up)
        def binding_previous_object(event: KeyPressEvent) -> None:
            nonlocal focus_index
            focus_index = max(0, focus_index - 1)
            event.app.layout.focus(objects_hsplit.children[focus_index])

        @bindings.add("c-c")
        @bindings.add("c-d")
        @bindings.add("q")
        def binding_quit(event: KeyPressEvent) -> None:
            event.app.exit()

        return ObjectBrowser(
            layout=object_browser_layout,
            key_bindings=bindings,
            full_screen=True,
            max_render_postpone_time=1.0,
            style=self._default_style,
        )

    def _show_object_browser(
        self: "PromptToolkitBackend", structure: SqlStructure
    ) -> SqlReference | None:
        object_browser: ObjectBrowser = self._build_object_browser(structure)
        object_browser.run(in_thread=True)

        return object_browser.result
