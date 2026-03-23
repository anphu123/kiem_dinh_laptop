"""
Component: AI pricing panel — redesigned.
Layout: header → 2 price cards (thu mua / bán ra) → phân tích → copy button.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from models.pricing import PricingResult
from views.components.theme import C


def price_panel(
    pricing: Optional[PricingResult],
    is_loading: bool,
    retry_cb: Optional[Callable],
    copy_cb: Optional[Callable],
) -> ft.Control:
    return ft.Column([
        _header(retry_cb if (pricing and not is_loading) else None),
        _body(pricing, is_loading, copy_cb),
    ], spacing=0)


# ── Header ────────────────────────────────────────────────────────────────────

def _header(retry_cb: Optional[Callable]) -> ft.Control:
    actions = []
    if retry_cb:
        actions.append(ft.IconButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            icon_size=15,
            icon_color="white",
            tooltip="Định giá lại",
            on_click=lambda _: retry_cb(),
            style=ft.ButtonStyle(padding=ft.padding.all(2)),
        ))

    return ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Text("✦", size=12, color="#DDD6FE"),
                ft.Text("AI  ĐỊNH  GIÁ", size=10,
                        weight=ft.FontWeight.BOLD, color="white"),
            ], spacing=5),
            *actions,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=["#5B21B6", "#7C3AED"],
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=7),
    )


# ── Body ──────────────────────────────────────────────────────────────────────

def _body(
    pricing: Optional[PricingResult],
    is_loading: bool,
    copy_cb: Optional[Callable],
) -> ft.Control:
    if is_loading or pricing is None:
        return _loading()
    if pricing.error:
        return _error(pricing.error)
    if pricing.has_prices:
        return _result(pricing, copy_cb)
    return _raw_fallback(pricing.raw)


def _loading() -> ft.Control:
    return ft.Container(
        content=ft.Column([
            ft.ProgressRing(width=28, height=28, stroke_width=3, color=C["accent"]),
            ft.Text("AI đang thẩm định...", size=10,
                    color=C["accent"], text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=20),
        bgcolor="#FFF7ED",
    )


def _error(error: str) -> ft.Control:
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, size=14, color=C["red"]),
                ft.Text("Không định giá được", size=10,
                        weight=ft.FontWeight.BOLD, color=C["red"]),
            ], spacing=5),
            ft.Text(error[:120], size=9, color=C["dim"]),
        ], spacing=4),
        padding=ft.padding.all(12),
        bgcolor="#FEF2F2",
        border=ft.border.only(left=ft.border.BorderSide(3, C["red"])),
    )


def _result(p: PricingResult, copy_cb: Optional[Callable]) -> ft.Control:
    items: list = []

    # ── 2 price cards ────────────────────────────────────────────────────────
    buy_card  = _price_card(
        label="THU MUA",
        icon=ft.Icons.ARROW_DOWNWARD_ROUNDED,
        lo=p.buy_min, hi=p.buy_max,
        bg="#DCFCE7", border_color="#86EFAC",
        text_color="#15803D", sub_color="#166534",
    )
    sell_card = _price_card(
        label="BÁN RA",
        icon=ft.Icons.ARROW_UPWARD_ROUNDED,
        lo=p.sell_min, hi=p.sell_max,
        bg="#EFF6FF", border_color="#93C5FD",
        text_color="#1D4ED8", sub_color="#1E40AF",
    )
    items.append(ft.Container(
        content=ft.Row([buy_card, sell_card], spacing=6,
                       expand=True),
        padding=ft.padding.only(left=8, right=8, top=8, bottom=4),
    ))

    # ── Summary ───────────────────────────────────────────────────────────────
    if p.summary:
        items.append(ft.Container(
            content=ft.Text(p.summary, size=9, color=C["text"], italic=True),
            padding=ft.padding.only(left=10, right=10, top=4, bottom=2),
        ))

    items.append(ft.Divider(height=1, color=C["border"]))

    # ── Điểm cộng / điểm trừ ─────────────────────────────────────────────────
    if p.strengths:
        items.append(_tag_row("✅", p.strengths, "#15803D", "#DCFCE7"))
    if p.weaknesses:
        items.append(_tag_row("⚠️", p.weaknesses, "#92400E", "#FEF9C3"))

    # ── Reasoning ────────────────────────────────────────────────────────────
    if p.reasoning:
        items.append(ft.Container(
            content=ft.Text(p.reasoning, size=9, color=C["dim"], italic=True),
            padding=ft.padding.only(left=10, right=10, top=4, bottom=4),
        ))

    # ── Copy button ──────────────────────────────────────────────────────────
    items.append(ft.Divider(height=1, color=C["border"]))
    copy_text = p.copy_text
    items.append(ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.COPY_ALL_ROUNDED, size=13, color="white"),
                ft.Text("Copy kết quả", size=10, color="white",
                        weight=ft.FontWeight.BOLD),
            ], spacing=5, tight=True),
            on_click=lambda _, t=copy_text: copy_cb(t) if copy_cb else None,
            bgcolor="#6D28D9",
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=12, vertical=7),
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=7),
    ))

    return ft.Column(items, spacing=0)


def _price_card(
    label: str, icon, lo: Optional[int], hi: Optional[int],
    bg: str, border_color: str, text_color: str, sub_color: str,
) -> ft.Control:
    lo_str = _fmt(lo)
    hi_str = _fmt(hi)
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(icon, size=11, color=text_color),
                ft.Text(label, size=8, weight=ft.FontWeight.BOLD,
                        color=text_color),
            ], spacing=3),
            ft.Text(lo_str, size=16, weight=ft.FontWeight.BOLD,
                    color=text_color),
            ft.Row([
                ft.Text("đến", size=8, color=sub_color),
                ft.Text(f"{hi_str} đ", size=10,
                        weight=ft.FontWeight.BOLD, color=sub_color),
            ], spacing=3),
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.START),
        bgcolor=bg,
        border=ft.border.all(1, border_color),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        expand=True,
    )


def _tag_row(emoji: str, items: list, text_color: str, bg: str) -> ft.Control:
    """Hiển thị list điểm mạnh/yếu dạng tags nhỏ."""
    tags = []
    for item in items[:3]:          # tối đa 3 tags
        tags.append(ft.Container(
            content=ft.Text(f"{emoji} {item}", size=8, color=text_color),
            bgcolor=bg,
            border_radius=4,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
        ))
    return ft.Container(
        content=ft.Column(tags, spacing=3),
        padding=ft.padding.only(left=10, right=8, top=4, bottom=2),
    )


def _raw_fallback(raw: str) -> ft.Control:
    """Hiển thị khi Gemini trả về text không parse được."""
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=13, color=C["yellow"]),
                ft.Text("Kết quả thô từ Gemini", size=9,
                        color=C["yellow"], weight=ft.FontWeight.BOLD),
            ], spacing=5),
            ft.Container(
                content=ft.Text(raw[:300] if raw else "Không có dữ liệu",
                                size=8, color=C["dim"]),
                bgcolor=C["card2"],
                border_radius=5,
                padding=ft.padding.all(7),
            ),
        ], spacing=5),
        padding=ft.padding.all(10),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(val: Optional[int]) -> str:
    if val is None:
        return "—"
    return f"{val:,.0f}".replace(",", ".")
