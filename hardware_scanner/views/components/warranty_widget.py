"""
Component: Warranty lookup widget.
Hiển thị ô nhập IMEI/Serial + kết quả tra cứu bảo hành thegioididong.com.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from controllers.warranty_controller import WarrantyResult, WarrantyItem, WARRANTY_PAGE
from views.components.theme import C


class WarrantyWidget:
    def __init__(self, page: ft.Page, on_lookup: Callable[[str, int], None]):
        self._page = page
        self._on_lookup = on_lookup
        self._result: Optional[WarrantyResult] = None
        self._loading = False
        self._keyword_field = ft.TextField(
            hint_text="Nhập IMEI hoặc serial number...",
            text_size=12,
            height=38,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_color=C["border"],
            focused_border_color=C["accent"],
            expand=True,
            on_submit=self._on_submit,
        )
        self._type_group = ft.RadioGroup(
            value="2",
            content=ft.Row([
                ft.Radio(value="2", label="IMEI / Serial", label_style=ft.TextStyle(size=10)),
                ft.Radio(value="1", label="Số điện thoại", label_style=ft.TextStyle(size=10)),
                ft.Radio(value="3", label="Jobcard",       label_style=ft.TextStyle(size=10)),
            ], spacing=8),
        )
        self._container = ft.Container()

    def set_keyword(self, keyword: str):
        """Pre-fill với serial từ scan."""
        self._keyword_field.value = keyword
        try:
            self._keyword_field.update()
        except Exception:
            pass

    def set_loading(self):
        self._loading = True
        self._result = None
        self._rebuild()

    def set_result(self, result: WarrantyResult):
        self._loading = False
        self._result = result
        self._rebuild()
        try:
            self._page.update()
        except Exception:
            pass

    def build(self) -> ft.Control:
        self._rebuild()
        return self._container

    # ── Private ───────────────────────────────────────────────────────────────

    def _open_browser(self, keyword: str = ""):
        import webbrowser
        webbrowser.open(WARRANTY_PAGE)
        if keyword:
            try:
                self._page.set_clipboard(keyword)
            except Exception:
                pass

    def _on_submit(self, _=None):
        kw = (self._keyword_field.value or "").strip()
        if not kw:
            return
        try:
            search_type = int(self._type_group.value or "2")
        except ValueError:
            search_type = 2
        self._on_lookup(kw, search_type)

    def _rebuild(self):
        rows: list = []

        # ── Input row ──
        rows.append(ft.Container(
            content=ft.Column([
                self._type_group,
                ft.Row([
                    self._keyword_field,
                    ft.ElevatedButton(
                        "Tra cứu",
                        on_click=self._on_submit,
                        bgcolor=C["accent"],
                        color="white",
                        height=38,
                        style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=12)),
                    ),
                ], spacing=6),
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
        ))

        # ── State: loading ──
        if self._loading:
            rows.append(ft.Container(
                content=ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color=C["accent"]),
                    ft.Text("AI đang thẩm định...", size=10, color=C["accent"]),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
            ))

        # ── State: result ──
        elif self._result is not None:
            rows.append(self._result_view(self._result))

        self._container.content = ft.Column(rows, spacing=0)

    def _result_view(self, r: WarrantyResult) -> ft.Control:
        items: list = []

        if r.error:
            icon = ft.Icons.OPEN_IN_BROWSER if r.need_browser else ft.Icons.WIFI_OFF_ROUNDED
            items.append(ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=14, color=C["yellow"] if r.need_browser else C["red"]),
                    ft.Text(r.error, size=10,
                            color=C["yellow"] if r.need_browser else C["red"]),
                ], spacing=6),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ))
            if r.need_browser:
                kw = r.keyword or ""
                items.append(ft.Container(
                    content=ft.ElevatedButton(
                        "🌐  Mở trang bảo hành trên trình duyệt",
                        on_click=lambda _, k=kw: self._open_browser(k),
                        bgcolor=C["accent"],
                        color="white",
                        height=34,
                        style=ft.ButtonStyle(
                            padding=ft.padding.symmetric(horizontal=12)),
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                ))
                items.append(ft.Container(
                    content=ft.Text(
                        f"Nhập serial  {kw}  vào ô tìm kiếm trên trang web",
                        size=9, color=C["dim"], italic=True,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                ))
            return ft.Column(items, spacing=0)

        if r.raw_message:
            color = C["dim"]
            icon = ft.Icons.INFO_OUTLINE_ROUNDED
            msg = r.raw_message
            # Phát hiện "không tìm thấy"
            if any(k in msg.lower() for k in ("không tìm", "not found", "không có")):
                color = C["yellow"]
                icon = ft.Icons.SEARCH_OFF_ROUNDED
            items.append(ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=14, color=color),
                    ft.Text(msg[:200], size=10, color=color),
                ], spacing=6),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
            ))
            return ft.Column(items, spacing=0)

        if not r.items:
            items.append(ft.Container(
                content=ft.Text("Không tìm thấy thông tin bảo hành.",
                                size=10, color=C["dim"]),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
            ))
            return ft.Column(items, spacing=0)

        for w in r.items:
            items.append(_warranty_card(w))

        return ft.Column(items, spacing=6)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _warranty_card(w: WarrantyItem) -> ft.Control:
    color_map = {"green": C["green"], "yellow": C["yellow"],
                 "red": C["red"], "dim": C["dim"]}
    sc = color_map.get(w.status_color, C["dim"])

    rows: list = []

    if w.product_name:
        rows.append(ft.Text(w.product_name, size=11,
                            weight=ft.FontWeight.BOLD, color=C["text"]))
    if w.warranty_status:
        rows.append(ft.Row([
            ft.Icon(ft.Icons.SHIELD_ROUNDED, size=13, color=sc),
            ft.Text(w.warranty_status, size=11,
                    weight=ft.FontWeight.BOLD, color=sc),
        ], spacing=4))

    def info_row(label: str, val: str):
        if val:
            rows.append(ft.Row([
                ft.Text(f"{label}:", size=9, color=C["dim"], width=90),
                ft.Text(val, size=9, color=C["text"]),
            ], spacing=4))

    info_row("Serial",      w.serial)
    info_row("IMEI",        w.imei)
    info_row("Ngày mua",    w.purchase_date)
    info_row("Hết BH",      w.warranty_end)
    info_row("Cửa hàng",    w.store)

    # Fallback raw text
    if not rows:
        raw = getattr(w, "raw_text", "")
        if raw:
            rows.append(ft.Text(raw, size=9, color=C["dim"]))

    border_color = sc if w.status_color != "dim" else C["border"]
    return ft.Container(
        content=ft.Column(rows, spacing=3),
        bgcolor=C["card2"],
        border=ft.border.all(1, border_color),
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        margin=ft.margin.symmetric(horizontal=8, vertical=2),
    )
