"""
Component: Camera & Mic live test widget.
Hiển thị nút test, spinner khi đang test, kết quả ảnh camera + chất lượng mic.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from controllers.cam_mic_controller import CamMicTestResult
from views.components.theme import C


class CamMicWidget:
    """
    Stateful widget — giữ trạng thái test.
    Gọi on_refresh() + page.update() khi kết quả về.
    """

    def __init__(self, page: ft.Page, on_refresh: Callable, on_test: Callable,
                 on_speaker_test: Callable):
        self._page = page
        self._on_refresh = on_refresh
        self._on_test = on_test
        self._on_speaker_test = on_speaker_test
        self._result: Optional[CamMicTestResult] = None
        self._loading = False
        self._speaker_loading = False
        self._speaker_ok: Optional[bool] = None

    def set_loading(self):
        self._loading = True
        self._result = None
        self._on_refresh()

    def set_result(self, result: CamMicTestResult):
        self._loading = False
        self._result = result
        self._on_refresh()
        try:
            self._page.update()
        except Exception:
            pass

    def set_speaker_loading(self):
        self._speaker_loading = True
        self._speaker_ok = None
        self._on_refresh()

    def set_speaker_done(self, ok: bool):
        self._speaker_loading = False
        self._speaker_ok = ok
        self._on_refresh()
        try:
            self._page.update()
        except Exception:
            pass

    def reset(self):
        self._loading = False
        self._result = None
        self._speaker_loading = False
        self._speaker_ok = None

    def build(self) -> ft.Control:
        if self._loading:
            cam_mic_part = self._spinner()
        elif self._result is not None:
            cam_mic_part = self._result_view(self._result)
        else:
            cam_mic_part = self._idle_button()

        return ft.Column([cam_mic_part, self._speaker_section()], spacing=0)

    # ── Private ───────────────────────────────────────────────────────────────

    def _speaker_section(self) -> ft.Control:
        if self._speaker_loading:
            content = ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=C["accent"]),
                ft.Text("Đang phát âm thanh...", size=10, color=C["dim"]),
            ], spacing=8)
        elif self._speaker_ok is True:
            content = ft.Row([
                ft.Text("🔊", size=12),
                ft.Text("Loa OK", size=10, color=C["green"], weight=ft.FontWeight.BOLD),
                ft.TextButton("↺ Test lại", on_click=lambda _: self._on_speaker_test(),
                              style=ft.ButtonStyle(color=C["dim"])),
            ], spacing=4)
        elif self._speaker_ok is False:
            content = ft.Row([
                ft.Text("🔊", size=12),
                ft.Text("Loa lỗi", size=10, color=C["red"], weight=ft.FontWeight.BOLD),
                ft.TextButton("↺ Test lại", on_click=lambda _: self._on_speaker_test(),
                              style=ft.ButtonStyle(color=C["dim"])),
            ], spacing=4)
        else:
            content = ft.ElevatedButton(
                "🔊  Test Loa  (to → nhỏ → to)",
                on_click=lambda _: self._on_speaker_test(),
                bgcolor=C["card2"],
                color=C["text"],
            )
        return ft.Container(
            content=content,
            padding=ft.padding.only(left=8, top=4, bottom=6),
        )

    def _idle_button(self) -> ft.Control:
        return ft.Container(
            content=ft.ElevatedButton(
                "▶  Kiểm tra Camera & Mic",
                on_click=lambda _: self._on_test(),
                bgcolor=C["accent"],
                color="white",
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=8),
        )

    def _spinner(self) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.ProgressRing(width=18, height=18, stroke_width=2, color=C["accent"]),
                    ft.Text("Đang mở camera & mic...", size=10, color=C["dim"]),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(vertical=8, horizontal=8),
        )

    def _result_view(self, r: CamMicTestResult) -> ft.Control:
        items: list = []

        # ── Camera ────────────────────────────────────────────────────────────
        cam_badge, cam_color = _quality_badge(r.camera_quality)
        items.append(ft.Container(
            content=ft.Row([
                ft.Text("📷 Camera:", size=10, weight=ft.FontWeight.BOLD, color=C["text"]),
                ft.Text(cam_badge, size=10, weight=ft.FontWeight.BOLD, color=cam_color),
            ], spacing=6),
            padding=ft.padding.only(left=8, top=6, bottom=2),
        ))

        if r.camera_frame_b64:
            items.append(ft.Container(
                content=ft.Image(
                    src_base64=r.camera_frame_b64,
                    width=240, height=160,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=ft.border_radius.all(6),
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ))

        if r.camera_accessible:
            items.append(ft.Container(
                content=ft.Row([
                    ft.Text(f"Độ sáng: {r.camera_brightness}", size=9, color=C["dim"]),
                    ft.Text("•", size=9, color=C["dim"]),
                    ft.Text(f"Độ nét: {r.camera_sharpness}", size=9, color=C["dim"]),
                ], spacing=6),
                padding=ft.padding.only(left=8, bottom=4),
            ))
        else:
            items.append(ft.Container(
                content=ft.Text("Không thể mở camera", size=9, color=C["red"]),
                padding=ft.padding.only(left=8, bottom=4),
            ))

        # ── Mic ───────────────────────────────────────────────────────────────
        mic_badge, mic_color = _quality_badge(r.mic_quality)
        items.append(ft.Divider(height=1, color=C["border"]))
        items.append(ft.Container(
            content=ft.Row([
                ft.Text("🎤 Microphone:", size=10, weight=ft.FontWeight.BOLD, color=C["text"]),
                ft.Text(mic_badge, size=10, weight=ft.FontWeight.BOLD, color=mic_color),
            ], spacing=6),
            padding=ft.padding.only(left=8, top=4, bottom=2),
        ))

        if r.mic_accessible and r.mic_rms is not None:
            # Volume bar — 0%=fail(<0.0003), 50%=good threshold(0.005), 100%=0.01+
            vol_pct = min(r.mic_rms / 0.01, 1.0)
            bar_color = C["green"] if r.mic_quality == "good" else (
                C["yellow"] if r.mic_quality == "low" else C["red"]
            )
            items.append(ft.Container(
                content=ft.Column([
                    ft.ProgressBar(
                        value=vol_pct, color=bar_color,
                        bgcolor=C["border"], height=8,
                    ),
                    ft.Text(
                        f"RMS: {r.mic_rms:.5f}  •  Peak: {r.mic_peak:.4f}",
                        size=9, color=C["dim"],
                    ),
                ], spacing=4),
                padding=ft.padding.only(left=8, right=8, bottom=6),
            ))
        else:
            items.append(ft.Container(
                content=ft.Text("Không thu được tín hiệu", size=9, color=C["red"]),
                padding=ft.padding.only(left=8, bottom=6),
            ))

        if r.error:
            items.append(ft.Container(
                content=ft.Text(f"⚠ {r.error}", size=9, color=C["yellow"]),
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
            ))

        # Nút test lại
        items.append(ft.Container(
            content=ft.TextButton(
                "↺  Test lại",
                on_click=lambda _: self._on_test(),
                style=ft.ButtonStyle(color=C["dim"]),
            ),
            padding=ft.padding.only(left=4, bottom=4),
        ))

        return ft.Column(items, spacing=0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _quality_badge(quality: str) -> tuple:
    """Trả về (text, color) theo quality string."""
    if quality == "good":
        return "✅ Tốt", C["green"]
    if quality == "poor":
        return "⚠ Kém", C["yellow"]
    if quality == "low":
        return "⚠ Yếu", C["yellow"]
    return "❌ Lỗi", C["red"]
