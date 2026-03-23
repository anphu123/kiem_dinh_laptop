"""
View: Tab 2 — Checklist kiểm định ngoại quan.
Dùng ChecklistCard từ components. Tab chỉ quản lý list cards + reset.
"""
from __future__ import annotations

import flet as ft

from controllers.checklist_controller import ChecklistController
from views.components.checklist_card import ChecklistCard
from views.components.theme import C


class ChecklistTab:
    def __init__(self, controller: ChecklistController, page: ft.Page):
        self._ctrl = controller
        self._page = page
        self._cards: dict = {}   # {qid: ChecklistCard}

    def build(self) -> ft.Control:
        controls = []
        for item in self._ctrl.checklist:
            card = ChecklistCard(item, on_answer=self._on_answer)
            self._cards[item.id] = card
            controls.append(card.control)

        controls.append(ft.Container(
            content=ft.Row(
                [ft.TextButton(
                    "↺  Reset câu trả lời",
                    on_click=self._on_reset,
                    style=ft.ButtonStyle(color=C["dim"]),
                )],
                alignment=ft.MainAxisAlignment.END,
            ),
            padding=ft.padding.only(right=10, top=4, bottom=12),
        ))

        return ft.Column(
            controls=controls,
            spacing=4,
        )

    # ── Handlers ──────────────────────────────────────────────────────────────

    def reset_visual(self):
        """Xóa visual state radio buttons (không đụng controller)."""
        for card in self._cards.values():
            card.reset()

    def auto_answer(self, qid: str, idx: int):
        """Tự động chọn đáp án (gọi từ scan callback)."""
        if qid not in self._cards:
            return
        self._cards[qid].radio_group.value = str(idx)
        self._ctrl.answer(qid, idx)
        self._sync_borders()

    def _on_answer(self, qid: str, idx: int):
        # Cập nhật visual state cho card vừa click
        if qid in self._cards:
            self._cards[qid].radio_group.value = str(idx)

        # Ghi trực tiếp vào controller — không scan toàn bộ cards
        # (scan-replace gây mất câu đã trả lời nếu rg.value chưa được sync)
        self._ctrl.answer(qid, idx)
        self._sync_borders()
        self._page.update()

    def _on_reset(self, _):
        self._ctrl.reset()
        for card in self._cards.values():
            card.reset()
        self._page.update()

    def _sync_borders(self):
        for qid, card in self._cards.items():
            card.set_answered(self._ctrl.answers.get(qid) is not None)
