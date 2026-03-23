"""
View: Panel phải — Grade badge + AI pricing + QR Code.
Dùng grade_badge, red_flags_banner, price_panel, QrWidget từ components.
Sidebar chỉ orchestrate layout và state, không có UI logic.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from models.hardware import HardwareData
from models.checklist import GradeResult
from models.pricing import PricingResult
from views.components.theme import C
from views.components.grade_badge import grade_badge, red_flags_banner
from views.components.price_card import price_panel
from views.components.qr_widget import QrWidget


class Sidebar:
    def __init__(self, page: ft.Page):
        self._page = page
        self._hw: Optional[HardwareData] = None
        self._grade: Optional[GradeResult] = None
        self._answered = 0
        self._total = 0
        self._answer_labels: dict = {}
        self._pricing: Optional[PricingResult] = None
        self._pricing_loading = False
        self._retry_cb: Optional[Callable] = None
        self._copy_cb: Optional[Callable] = None

        self._qr = QrWidget(page, on_refresh=self._refresh)

        self._col = ft.Column(
            controls=[self._placeholder()],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

    def build(self) -> ft.Control:
        return ft.Container(
            content=self._col,
            expand=True,
            bgcolor=C["card"],
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_retry_callback(self, cb: Callable):
        self._retry_cb = cb

    def set_copy_callback(self, cb: Callable):
        self._copy_cb = cb

    def reset(self):
        self._hw = None
        self._grade = None
        self._answered = 0
        self._total = 0
        self._answer_labels = {}
        self._pricing = None
        self._pricing_loading = False
        self._qr.invalidate()
        self._col.controls = [self._placeholder()]

    def set_hardware(self, hw: HardwareData):
        self._hw = hw
        self._refresh()

    def update_grade(
        self,
        grade: Optional[GradeResult],
        answered: int,
        total: int,
        answer_labels: dict,
    ):
        self._grade = grade
        self._answered = answered
        self._total = total
        self._answer_labels = answer_labels
        self._pricing = None
        self._pricing_loading = False
        self._qr.invalidate()
        self._refresh()

    def show_pricing_loading(self):
        self._pricing = None
        self._pricing_loading = True
        self._refresh()

    def show_pricing(self, result: PricingResult):
        self._pricing = result
        self._pricing_loading = False
        self._refresh()

    # ── Core rebuild ──────────────────────────────────────────────────────────

    def _refresh(self):
        self._col.controls = self._build_content()

    def _build_content(self) -> list:
        controls = []

        # ── Grade hoặc hint ──
        if self._grade:
            controls.append(grade_badge(self._grade, self._answered, self._total))
        elif self._hw:
            controls.append(self._hint_not_inspected())

        # ── Red flags ──
        if self._grade and self._grade.red_flags:
            controls.append(red_flags_banner(self._grade.red_flags))

        controls.append(ft.Divider(height=1, color=C["border"]))

        # ── AI section ──
        controls.append(self._ai_section())

        controls.append(ft.Divider(height=1, color=C["border"]))

        # ── QR ──
        if self._hw:
            controls.append(self._qr.build(
                self._hw, self._grade, self._answer_labels,
            ))
        else:
            controls.append(self._placeholder())

        return controls

    # ── Sub-sections ──────────────────────────────────────────────────────────

    def _hint_not_inspected(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Chưa kiểm định", color=C["dim"], size=11,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        "Chọn tab ✅ KIỂM ĐỊNH\nđể trả lời câu hỏi ngoại quan",
                        color=C["dim"], size=10,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=12),
        )

    def _ai_section(self) -> ft.Control:
        if not self._grade or self._answered < self._total:
            remaining = self._total - self._answered
            msg = (
                f"🤖  Còn {remaining} câu nữa → AI tự định giá"
                if self._grade
                else "🤖  Hoàn thành kiểm định để AI định giá"
            )
            return ft.Container(
                content=ft.Text(msg, size=10, color=C["dim"],
                                text_align=ft.TextAlign.CENTER),
                padding=ft.padding.symmetric(vertical=10),
            )

        return price_panel(
            pricing=self._pricing,
            is_loading=self._pricing_loading,
            retry_cb=self._retry_cb,
            copy_cb=self._copy_cb,
        )

    def _placeholder(self) -> ft.Control:
        return ft.Container(
            content=ft.Text("QR", size=48, weight=ft.FontWeight.BOLD,
                            color=C["border"], text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center,
            expand=True,
            padding=ft.padding.symmetric(vertical=60),
        )
