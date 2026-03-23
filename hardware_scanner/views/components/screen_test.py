"""
Component: Screen Test — kiểm tra điểm chết & sọc màn hình.
Đẩy fullscreen overlay (qua page.overlay) với 7 màu chuẩn.
User click hoặc nhấn phím bất kỳ để chuyển màu, ESC để thoát.
Sau khi xem hết → hiện nút kết quả Bình thường / Có lỗi.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from views.components.theme import C

# (label, bg_hex, text_hex)
_COLORS = [
    ("⬛  Đen",          "#000000", "#FFFFFF"),
    ("⬜  Trắng",        "#FFFFFF", "#000000"),
    ("🔴  Đỏ",           "#FF0000", "#FFFFFF"),
    ("🟢  Xanh lá",     "#00CC00", "#000000"),
    ("🔵  Xanh dương",  "#0000CC", "#FFFFFF"),
    ("🟡  Vàng",         "#FFFF00", "#000000"),
    ("🟣  Tím",          "#AA00CC", "#FFFFFF"),
]


class ScreenTestWidget:
    """
    Inline widget nhỏ trong TestTab.
    Khi bấm "Bắt đầu" → push fullscreen overlay; khi xong → pop overlay,
    hiện nút Bình thường / Có lỗi.
    on_result(passed: bool) được gọi khi user xác nhận kết quả.
    """

    def __init__(
        self,
        page: ft.Page,
        on_refresh: Callable,
        on_result: Optional[Callable[[bool], None]] = None,
    ):
        self._page = page
        self._on_refresh = on_refresh
        self._on_result = on_result

        self._idx = 0
        self._active = False
        self._state = "idle"      # "idle" | "result"
        self._passed: Optional[bool] = None

        self._prev_kb = None
        self._overlay_ref: Optional[ft.Container] = None

        self._container = ft.Container()

    # ── Public ────────────────────────────────────────────────────────────────

    @property
    def control(self) -> ft.Container:
        return self._container

    def build(self) -> ft.Control:
        self._container.content = self._build_panel()
        return self._container

    def start(self):
        """Tự động bắt đầu fullscreen test (gọi từ bên ngoài)."""
        if not self._active and self._state == "idle":
            self._start()

    def reset(self):
        if self._active:
            self._cancel()
        self._state = "idle"
        self._passed = None
        self._idx = 0
        self._container.content = self._build_panel()

    # ── Panel (inline) ────────────────────────────────────────────────────────

    def _build_panel(self) -> ft.Control:
        if self._state == "result":
            return self._result_panel()
        return self._idle_panel()

    def _idle_panel(self) -> ft.Control:
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    "Hiển thị 7 màu toàn màn hình để kiểm tra\n"
                    "điểm chết (dead pixel) và sọc màu.",
                    size=10, color=C["dim"],
                ),
                ft.ElevatedButton(
                    "🖥️  Bắt đầu kiểm tra màn hình",
                    on_click=lambda _: self._start(),
                    bgcolor=C["accent"],
                    color="white",
                ),
            ], spacing=6),
            padding=ft.padding.symmetric(vertical=6),
        )

    def _result_panel(self) -> ft.Control:
        if self._passed is None:
            # Sau khi xem hết màu, chờ user xác nhận
            return ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Bạn có thấy điểm chết hoặc sọc màu không?",
                        size=11, color=C["text"],
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "✅  Bình thường",
                            on_click=lambda _: self._set_result(True),
                            bgcolor=C["green"], color="white",
                        ),
                        ft.ElevatedButton(
                            "❌  Có điểm chết / sọc",
                            on_click=lambda _: self._set_result(False),
                            bgcolor=C["red"], color="white",
                        ),
                    ], spacing=8, wrap=True),
                ], spacing=8),
                padding=ft.padding.symmetric(vertical=6),
            )

        # Đã xác nhận kết quả
        if self._passed:
            badge_bg = C["green"]
            badge_text = "✅  Màn hình bình thường"
        else:
            badge_bg = C["red"]
            badge_text = "❌  Phát hiện điểm chết / sọc màu"

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(
                        badge_text, size=11, color="white",
                        weight=ft.FontWeight.BOLD,
                    ),
                    bgcolor=badge_bg, border_radius=6,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                ),
                ft.TextButton(
                    "↺  Test lại",
                    on_click=lambda _: self._retry(),
                    style=ft.ButtonStyle(color=C["dim"]),
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.START, spacing=4),
            padding=ft.padding.symmetric(vertical=6),
        )

    # ── Fullscreen overlay ─────────────────────────────────────────────────────

    def _start(self):
        self._idx = 0
        self._active = True
        self._prev_kb = self._page.on_keyboard_event
        self._page.on_keyboard_event = self._on_key
        try:
            self._page.window.full_screen = True
            self._page.update()
        except Exception:
            pass
        self._push_overlay()

    def _push_overlay(self):
        label, bg, fg = _COLORS[self._idx]
        step = self._idx + 1
        total = len(_COLORS)

        overlay = ft.Container(
            bgcolor=bg,
            expand=True,
            on_click=lambda _: self._advance(),
            content=ft.Column(
                [
                    ft.Text(
                        label,
                        size=26, weight=ft.FontWeight.BOLD,
                        color=fg, text_align=ft.TextAlign.CENTER,
                        no_wrap=True,
                    ),
                    ft.Text(
                        f"{step} / {total}",
                        size=16, color=fg,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Click hoặc nhấn phím bất kỳ để chuyển màu",
                        size=11, color=fg,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "ESC để thoát",
                        size=10, color=fg,
                        text_align=ft.TextAlign.CENTER,
                        italic=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            alignment=ft.alignment.center,
        )

        self._overlay_ref = overlay
        self._page.overlay.append(overlay)
        try:
            self._page.update()
        except Exception:
            pass

    def _update_overlay(self):
        """Cập nhật màu và text mà không pop/push lại."""
        if not self._overlay_ref:
            return
        label, bg, fg = _COLORS[self._idx]
        step = self._idx + 1
        total = len(_COLORS)

        self._overlay_ref.bgcolor = bg
        self._overlay_ref.content = ft.Column(
            [
                ft.Text(
                    label,
                    size=26, weight=ft.FontWeight.BOLD,
                    color=fg, text_align=ft.TextAlign.CENTER,
                    no_wrap=True,
                ),
                ft.Text(
                    f"{step} / {total}",
                    size=16, color=fg,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                ft.Text(
                    "Click hoặc nhấn phím bất kỳ để chuyển màu",
                    size=11, color=fg,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "ESC để thoát",
                    size=10, color=fg,
                    text_align=ft.TextAlign.CENTER,
                    italic=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )
        try:
            self._overlay_ref.update()
        except Exception:
            pass

    def _pop_overlay(self):
        if self._overlay_ref and self._overlay_ref in self._page.overlay:
            self._page.overlay.remove(self._overlay_ref)
        self._overlay_ref = None
        try:
            self._page.update()
        except Exception:
            pass

    # ── Navigation ────────────────────────────────────────────────────────────

    def _advance(self):
        if not self._active:
            return
        self._idx += 1
        if self._idx >= len(_COLORS):
            self._finish()
        else:
            self._update_overlay()

    def _exit_fullscreen(self):
        try:
            self._page.window.full_screen = False
            self._page.update()
        except Exception:
            pass

    def _finish(self):
        """Đã xem hết màu — pop overlay, chờ user xác nhận kết quả."""
        self._active = False
        self._page.on_keyboard_event = self._prev_kb
        self._prev_kb = None
        self._exit_fullscreen()
        self._pop_overlay()
        self._state = "result"
        self._container.content = self._build_panel()
        self._on_refresh()

    def _cancel(self):
        """ESC hoặc rescan — thoát không lưu kết quả."""
        self._active = False
        self._page.on_keyboard_event = self._prev_kb
        self._prev_kb = None
        self._exit_fullscreen()
        self._pop_overlay()

    def _set_result(self, passed: bool):
        self._passed = passed
        self._container.content = self._build_panel()
        try:
            self._container.update()
        except Exception:
            pass
        if self._on_result:
            self._on_result(passed)

    def _retry(self):
        self._state = "idle"
        self._passed = None
        self._idx = 0
        self._container.content = self._build_panel()
        try:
            self._container.update()
        except Exception:
            pass

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def _on_key(self, e: ft.KeyboardEvent):
        if not self._active:
            return
        if e.key == "Escape":
            self._cancel()
        else:
            self._advance()
