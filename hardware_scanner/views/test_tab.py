"""
View: Tab 2 — Kiểm thử phần cứng (Camera, Mic, Loa, Bàn phím, Bảo hành).
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from views.components.theme import C
from views.components.cam_mic_widget import CamMicWidget
from views.components.keyboard_test import KeyboardTestWidget
from views.components.warranty_widget import WarrantyWidget
from views.components.screen_test import ScreenTestWidget


class TestTab:
    def __init__(self, page: ft.Page, on_cam_mic_test: Callable,
                 on_speaker_test: Callable,
                 on_warranty_lookup: Callable[[str, int], None],
                 on_screen_result: Optional[Callable[[bool], None]] = None,
                 on_next_tab: Optional[Callable] = None):
        self._page = page
        self._on_next_tab = on_next_tab
        self._cam_mic = CamMicWidget(
            page,
            on_refresh=self._refresh_cam_mic,
            on_test=on_cam_mic_test,
            on_speaker_test=on_speaker_test,
        )
        self._keyboard = KeyboardTestWidget(page, on_refresh=self._refresh_keyboard)
        self._warranty = WarrantyWidget(page, on_lookup=on_warranty_lookup)
        self._screen = ScreenTestWidget(
            page,
            on_refresh=self._refresh_screen,
            on_result=on_screen_result,
        )

        self._cam_mic_placeholder = ft.Container(content=self._cam_mic.build())
        self._keyboard_placeholder = ft.Container(content=self._keyboard.build())
        self._warranty_placeholder = ft.Container(content=self._warranty.build())
        self._screen_placeholder = ft.Container(content=self._screen.build())

        self._waiting_label = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.HOURGLASS_TOP_ROUNDED,
                        color=C["dim"], size=32),
                ft.Text("Đang chờ quét phần cứng...",
                        size=13, color=C["dim"],
                        text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            alignment=ft.alignment.center,
            expand=True,
        )
        self._ready = False
        self._main_col = ft.Column(
            controls=[self._waiting_label],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

    def build(self) -> ft.Control:
        return ft.Container(
            content=self._main_col,
            expand=True,
            bgcolor=C["bg"],
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def on_scan_done(self, data):
        """Gọi từ app.py khi scan xong — unlock tab, set keyboard layout,
        pre-fill serial vào warranty widget."""
        self._keyboard.set_model(data.system.model)
        sn = data.system.serial_number or ""
        self._warranty.set_keyword(sn)
        self._ready = True
        self._cam_mic_placeholder.content = self._cam_mic.build()
        self._keyboard_placeholder.content = self._keyboard.build()
        self._warranty_placeholder.content = self._warranty.build()
        self._main_col.controls = self._build_content()

    def reset(self):
        self._cam_mic.reset()
        self._keyboard.reset()
        self._screen.reset()
        self._ready = False
        self._main_col.controls = [self._waiting_label]

    def set_cam_mic_loading(self):
        self._cam_mic.set_loading()

    def set_cam_mic_result(self, result):
        self._cam_mic.set_result(result)

    def set_speaker_loading(self):
        self._cam_mic.set_speaker_loading()

    def set_speaker_done(self, ok: bool):
        self._cam_mic.set_speaker_done(ok)

    def set_warranty_loading(self):
        self._warranty.set_loading()
        self._warranty_placeholder.content = self._warranty.build()
        try:
            self._warranty_placeholder.update()
        except Exception:
            pass

    def set_warranty_result(self, result):
        self._warranty.set_result(result)
        self._warranty_placeholder.content = self._warranty.build()
        try:
            self._warranty_placeholder.update()
        except Exception:
            pass

    # ── Private ───────────────────────────────────────────────────────────────

    def _refresh_cam_mic(self):
        self._cam_mic_placeholder.content = self._cam_mic.build()
        try:
            self._cam_mic_placeholder.update()
        except Exception:
            pass

    def _refresh_keyboard(self):
        self._keyboard_placeholder.content = self._keyboard.build()
        try:
            self._keyboard_placeholder.update()
        except Exception:
            pass

    def _refresh_screen(self):
        self._screen_placeholder.content = self._screen.build()
        try:
            self._screen_placeholder.update()
        except Exception:
            pass

    def _section_header(self, title: str) -> ft.Control:
        return ft.Container(
            content=ft.Text(
                title,
                size=11, weight=ft.FontWeight.BOLD,
                color=C["accent"],
            ),
            bgcolor=C["card2"],
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            border=ft.border.only(
                bottom=ft.border.BorderSide(1, C["border"]),
                top=ft.border.BorderSide(1, C["border"]),
            ),
        )

    def _build_content(self) -> list:
        controls = [
            self._section_header("🛡️  TRA CỨU BẢO HÀNH  (thegioididong.com)"),
            self._warranty_placeholder,
            self._section_header("🖥️  MÀN HÌNH — ĐIỂM CHẾT & SỌC MÀU"),
            ft.Container(
                content=self._screen_placeholder,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            ),
            self._section_header("📷  CAMERA, MICROPHONE & LOA"),
            ft.Container(
                content=self._cam_mic_placeholder,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ),
            self._section_header("⌨  BÀN PHÍM"),
            ft.Container(
                content=self._keyboard_placeholder,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ),
            ft.Container(height=8),
        ]

        if self._on_next_tab:
            controls.append(ft.Container(
                content=ft.ElevatedButton(
                    "✅  Xong — Sang Kiểm định  →",
                    on_click=lambda _: self._on_next_tab(),
                    bgcolor=C["accent"],
                    color="white",
                    width=260,
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=20),
            ))

        return controls
