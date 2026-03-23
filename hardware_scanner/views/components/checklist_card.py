"""
Component: Một card câu hỏi kiểm định.
Encapsulates RadioGroup + badge score + border highlight.
"""
from __future__ import annotations

from typing import Callable

import flet as ft

from models.checklist import ChecklistItem
from views.components.theme import C


class ChecklistCard:
    """
    Một card câu hỏi kiểm định.
    ChecklistTab giữ list[ChecklistCard] để reset / sync borders.
    """

    def __init__(self, item: ChecklistItem, on_answer: Callable):
        """on_answer(question_id: str, option_index: int)"""
        self._item = item
        self._on_answer = on_answer
        self._rg, self._container = self._build()

    @property
    def control(self) -> ft.Container:
        return self._container

    @property
    def radio_group(self) -> ft.RadioGroup:
        return self._rg

    def set_answered(self, answered: bool):
        """Highlight/unhighlight border."""
        self._container.border = ft.border.all(
            1, C["accent"] if answered else C["border"]
        )

    def reset(self):
        self._rg.value = None
        self.set_answered(False)

    # ── Builder ───────────────────────────────────────────────────────────────

    def _build(self) -> tuple:
        radio_rows = []
        for i, opt in enumerate(self._item.options):
            if opt.red_flag:
                badge, badge_color = "🚩 REJECT", C["red"]
            elif opt.score == 0:
                badge, badge_color = "0 đ", C["green"]
            elif opt.score <= 2:
                badge, badge_color = f"+{opt.score} đ", C["yellow"]
            else:
                badge, badge_color = f"+{opt.score} đ", C["red"]

            radio_rows.append(ft.Container(
                content=ft.Row([
                    ft.Radio(
                        value=str(i),
                        label=opt.label,
                        label_style=ft.TextStyle(color=C["text"], size=10),
                    ),
                    ft.Text(badge, color=badge_color, size=10),
                ]),
                margin=ft.margin.symmetric(vertical=1),
            ))

        rg = ft.RadioGroup(
            content=ft.Column(controls=radio_rows, spacing=0),
            on_change=lambda e: self._on_answer(self._item.id, int(e.data)),
        )

        container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Text(self._item.icon, size=14, color=C["accent"]),
                        ft.Text(
                            f"  {self._item.category}", size=11,
                            weight=ft.FontWeight.BOLD, color=C["accent"],
                        ),
                    ]),
                    ft.Text(self._item.question, size=10, color=C["text"]),
                    rg,
                ],
                spacing=6,
            ),
            bgcolor=C["card2"],
            border=ft.border.all(1, C["border"]),
            border_radius=8,
            padding=ft.padding.all(12),
            margin=ft.margin.symmetric(horizontal=6, vertical=2),
        )
        return rg, container
