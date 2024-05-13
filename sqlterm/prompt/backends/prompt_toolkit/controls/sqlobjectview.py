from typing import Dict, List, Tuple

from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import HSplit

from ..... import constants
from .....sql.generic.dataclasses import SqlObject
from .....sql.generic.enums import SqlObjectType

_sql_object_type_characters: Dict[SqlObjectType, str] = {
    SqlObjectType.CATALOG: "⛁ ",
    SqlObjectType.COLUMN: "🗅 ",
    SqlObjectType.DATABASE: "⛁ ",
    SqlObjectType.FUNCTION: "ƒ ",
    SqlObjectType.FUNCTION_SCALAR: "ƒ𝑥",
    SqlObjectType.FUNCTION_TABLE_VALUED: "🗠 ",
    SqlObjectType.PARAMETER: "⚙ ",
    SqlObjectType.PROCEDURE: "🕮 ",
    SqlObjectType.SCHEMA: "🗀 ",
    SqlObjectType.TABLE: "▦ ",
    SqlObjectType.VIEW: "👁 ",
}

_sql_object_type_format_classes: Dict[SqlObjectType, str] = {
    SqlObjectType.CATALOG: "class:object-browser.icon-database",
    SqlObjectType.COLUMN: "class:object-browser.icon-column",
    SqlObjectType.DATABASE: "class:object-browser.icon-database",
    SqlObjectType.FUNCTION: "class:object-browser.icon-function-scalar",
    SqlObjectType.FUNCTION_SCALAR: "class:object-browser.icon-function-scalar",
    SqlObjectType.FUNCTION_TABLE_VALUED: "class:object-browser.icon-function-table-valued",
    SqlObjectType.PARAMETER: "class:object-browser.icon-parameter",
    SqlObjectType.PROCEDURE: "class:object-browser.icon-procedure",
    SqlObjectType.SCHEMA: "class:object-browser.icon-schema",
    SqlObjectType.TABLE: "class:object-browser.icon-table",
    SqlObjectType.VIEW: "class:object-browser.icon-view",
}


class SqlObjectView(Window):
    __children: List["SqlObjectView"]
    __expanded: bool
    index: int
    indent_level: int
    parent: HSplit = None
    __sql_object: SqlObject

    indent_length: int = 2

    def __init__(
        self: "SqlObjectView",
        sql_object: SqlObject,
        index: int,
        parent: HSplit = None,
        indent_level: int = 0,
    ) -> None:
        self.__expanded = False
        self.__sql_object = sql_object
        self.indent_level = indent_level
        self.__children = []
        self.index = index
        self.parent = parent

        super().__init__(
            content=self._get_text_content(collapsed=not self.__expanded),
            height=1,
        )

    def _collapse(self: "SqlObjectView") -> None:
        if not self.__expanded:
            return

        # collapse all children of this object
        self.__children.reverse()
        for child in self.__children:
            child._collapse()

        # remove the children from the parent HSplit
        for index in range(
            self.index + len(self.__sql_object.children), self.index, -1
        ):
            del self.parent.children[index]

        self.__children = []

        # update the content of this object view to show it as collapsed
        self.content = self._get_text_content(collapsed=True)

        # propagate the new indices to all controls below this one
        for update_index in range(self.index + 1, len(self.parent.children)):
            self.parent.children[update_index].index = update_index

    def collapse_or_find_parent(self: "SqlObjectView", layout: Layout) -> int:
        if self.__expanded:
            self._collapse()
            self.__expanded = False
        else:
            parent_index: int = self.index
            while parent_index > 0 and (
                self.parent.get_children()[parent_index].indent_level
                == self.indent_level
            ):
                parent_index -= 1

            if parent_index >= 0:
                layout.focus(self.parent.get_children()[parent_index])
                return parent_index

        return self.index

    def _expand(self: "SqlObjectView") -> None:
        self.content = self._get_text_content(collapsed=False)

        for offset, child_object in enumerate(
            sorted(
                self.__sql_object.children,
                key=lambda sql_object: (sql_object.type, sql_object.name.lower()),
            ),
            start=1,
        ):
            self.parent.children.insert(
                self.index + offset,
                new_child := SqlObjectView(
                    child_object,
                    index=self.index + offset,
                    parent=self.parent,
                    indent_level=self.indent_level + 1,
                ),
            )

            self.__children.append(new_child)

        for update_index in range(
            self.index + len(self.__sql_object.children), len(self.parent.children)
        ):
            self.parent.children[update_index].index = update_index

    def expand_if_collapsed(self: "SqlObjectView") -> None:
        if self.__expanded:
            return

        self._expand()
        self.__expanded = True

    def _get_sql_object_label(
        self: "SqlObjectView", sql_object: SqlObject
    ) -> List[Tuple[str, str]]:
        if sql_object.type in _sql_object_type_characters:
            return [
                (
                    (
                        _sql_object_type_format_classes[sql_object.type]
                        if sql_object.type in _sql_object_type_format_classes
                        else ""
                    ),
                    f"{_sql_object_type_characters[sql_object.type]} ",
                ),
                ("class:object-browser.object-name", f"{sql_object.name}"),
            ]

        return [("", "   "), ("class:object-browser.object-name", f"{sql_object.name}")]

    def _get_text_content(
        self: "SqlObjectView", collapsed: bool
    ) -> FormattedTextControl:
        if len(self.__sql_object.children) == 0:
            return FormattedTextControl(
                FormattedText(
                    [
                        (
                            "",
                            " "
                            * (
                                self.indent_level * self.indent_length
                                + len(constants.TREE_VIEW_EXPANDED_CHAR)
                                + 1
                            ),
                        ),
                        *self._get_sql_object_label(self.__sql_object),
                    ]
                )
            )

        if not collapsed:
            return FormattedTextControl(
                FormattedText(
                    [
                        ("", " " * self.indent_level * self.indent_length),
                        (
                            "class:object-browser.icon-expand",
                            constants.TREE_VIEW_EXPANDED_CHAR,
                        ),
                        ("", " "),
                        *self._get_sql_object_label(self.__sql_object),
                    ]
                )
            )

        return FormattedTextControl(
            FormattedText(
                [
                    ("", " " * self.indent_level * self.indent_length),
                    (
                        "class:object-browser.icon-collapse",
                        constants.TREE_VIEW_COLLAPSED_CHAR,
                    ),
                    ("", " "),
                    *self._get_sql_object_label(self.__sql_object),
                ]
            )
        )

    def toggle_collapse(self: "SqlObjectView") -> None:
        if len(self.__sql_object.children) == 0:
            return

        if self.__expanded:
            self._collapse()
        else:
            self._expand()

        self.__expanded = not self.__expanded
