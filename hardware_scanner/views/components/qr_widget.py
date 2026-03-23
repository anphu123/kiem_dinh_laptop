"""
Component: QR code generator + display widget.
Tạo QR trong background thread, cache base64, hiện ảnh + nút lưu.
"""
from __future__ import annotations

import base64
import io
import json
import os
import platform
import subprocess
import tempfile
import threading
from typing import Callable, Optional

import flet as ft

from models.hardware import HardwareData
from models.checklist import GradeResult
from views.components.theme import C


class QrWidget:
    """
    Stateful component — giữ cache base64 QR codes.
    Gọi on_refresh() + page.update() sau khi generate xong.
    """

    def __init__(self, page: ft.Page, on_refresh: Callable):
        """
        on_refresh: callback để Sidebar biết cần rebuild (_refresh).
        """
        self._page = page
        self._on_refresh = on_refresh
        self._cache: dict = {}   # cache_key → base64 str | "__ERROR__..."

    def invalidate(self):
        """Xoá cache khi grade thay đổi."""
        self._cache = {}

    def build(
        self,
        hw: HardwareData,
        grade: Optional[GradeResult],
        answer_labels: dict,
    ) -> ft.Control:
        """Trả về control phù hợp với trạng thái cache hiện tại."""
        key = self._cache_key(hw, grade)
        if key not in self._cache:
            self._start_generation(hw, grade, answer_labels, key)
            return self._spinner()
        return self._display(key, hw.system.serial_number)

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(hw: HardwareData, grade: Optional[GradeResult]) -> str:
        grade_str = grade.grade if grade else "none"
        score = grade.score if grade else 0
        return f"{hw.system.serial_number}|{grade_str}|{score}"

    def _start_generation(
        self,
        hw: HardwareData,
        grade: Optional[GradeResult],
        answer_labels: dict,
        key: str,
    ):
        def _gen():
            try:
                import qrcode
                from PIL import Image as PILImage

                payload = hw.to_qr_payload(
                    grade.grade if grade else None,
                    grade.score if grade else None,
                    answer_labels,
                )
                json_str = json.dumps(
                    payload, ensure_ascii=False, separators=(",", ":"))
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=6, border=2,
                )
                qr.add_data(json_str)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                pil_img = img.get_image().resize((200, 200), PILImage.NEAREST)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                self._cache[key] = base64.b64encode(buf.getvalue()).decode()
            except Exception as e:
                self._cache[key] = f"__ERROR__{e}"

            self._on_refresh()
            try:
                self._page.update()
            except Exception:
                pass

        threading.Thread(target=_gen, daemon=True).start()

    def _spinner(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "📱  Quét để nhập vào App",
                        size=11, weight=ft.FontWeight.BOLD, color=C["text"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.ProgressRing(
                        width=32, height=32, stroke_width=3, color=C["accent"],
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.padding.symmetric(vertical=16),
        )

    def _display(self, key: str, sn: str) -> ft.Control:
        b64 = self._cache.get(key, "")

        if b64.startswith("__ERROR__"):
            return ft.Container(
                content=ft.Text(
                    f"QR lỗi: {b64[9:]}", size=10, color=C["red"],
                    text_align=ft.TextAlign.CENTER,
                ),
                padding=ft.padding.symmetric(vertical=16),
            )

        def save_qr(_):
            try:
                path = os.path.join(tempfile.gettempdir(), f"o2o_qr_{sn}.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(b64))
                if platform.system() == "Windows":
                    os.startfile(path)
                elif platform.system() == "Darwin":
                    subprocess.run(["open", path])
            except Exception:
                pass

        return ft.Column(
            [
                ft.Text(
                    "📱  Quét để nhập vào App",
                    size=11, weight=ft.FontWeight.BOLD, color=C["text"],
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Image(
                    src_base64=b64, width=200, height=200,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.Text(
                    sn, size=10, color=C["accent"],
                    font_family="Courier New",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.ElevatedButton(
                    "💾  Lưu QR",
                    on_click=save_qr,
                    bgcolor=C["border"],
                    color=C["text"],
                ),
                ft.Container(height=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )
