from typing import Any
from prompt_toolkit.application import Application
from prompt_toolkit.cursor_shapes import CursorShape, CursorShapeConfig


class SelectionCursorShapeConfig(CursorShapeConfig):
    # pylint: disable=too-few-public-methods

    def get_cursor_shape(
        self: "SelectionCursorShapeConfig", application: Application[Any]
    ) -> CursorShape:
        if application.current_buffer.selection_state is None:
            # if not selecting, keep the default cursor shape
            application.output.reset_cursor_shape()
            return None  # type: ignore

        return CursorShape.BEAM
