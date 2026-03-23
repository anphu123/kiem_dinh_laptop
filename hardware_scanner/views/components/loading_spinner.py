"""
Component: Loading spinner + progress text.
Dùng trong HardwareTab khi đang quét.
"""
from __future__ import annotations

import flet as ft

from views.components.theme import C


class LoadingSpinner:
    """Spinner có thể update progress text mà không rebuild."""

    def __init__(self):
        self._progress = ft.Text("", color=C["dim"], size=10)

    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.ProgressRing(
                    width=48, height=48,
                    stroke_width=4, color=C["accent"],
                ),
                ft.Text(
                    "AI đang thẩm định...",
                    size=11, weight=ft.FontWeight.BOLD, color=C["accent"],
                ),
                self._progress,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )

    def set_progress(self, msg: str):
        """Cập nhật dòng trạng thái bên dưới spinner."""
        self._progress.value = msg
