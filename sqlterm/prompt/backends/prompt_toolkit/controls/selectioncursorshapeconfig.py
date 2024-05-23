"""
module sqlterm.prompt.backends.prompt_toolkit.controls.selectioncursorshapeconfig

Contains the definition of the SelectionCursorShapeConfig class, a CursorShape config
subclass that is used to contextually set the terminal cursor whenever the user is
selecting text a the prompt
"""

from typing import Any
from prompt_toolkit.application import Application
from prompt_toolkit.cursor_shapes import CursorShape, CursorShapeConfig


class SelectionCursorShapeConfig(CursorShapeConfig):
    """
    class SelectionCursorShapeConfig

    A CursorShape config subclass that is used to contextually set the terminal cursor
    whenever the user is selecting text a the prompt
    """

    # pylint: disable=too-few-public-methods

    def get_cursor_shape(
        self: "SelectionCursorShapeConfig", application: Application[Any]
    ) -> CursorShape:
        if application.current_buffer.selection_state is None:
            # if not selecting, keep the default cursor shape
            application.output.reset_cursor_shape()
            return None  # type: ignore

        return CursorShape.BEAM
