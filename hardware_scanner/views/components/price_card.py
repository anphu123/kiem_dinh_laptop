"""
Component: AI pricing panel — giao diện định giá thu mua laptop cũ.
Thiết kế rõ ràng, phân cấp thông tin: Giá thu mua (chính) → Giá bán ra → Phân tích.
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
            icon_size=16,
            icon_color="white",
            tooltip="Định giá lại",
            on_click=lambda _: retry_cb(),
            style=ft.ButtonStyle(padding=ft.padding.all(4)),
        ))

    return ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Text("✦", size=13, color="#E9D5FF"),
                ft.Text("AI  ĐỊNH  GIÁ", size=11,
                        weight=ft.FontWeight.BOLD, color="white",
                        letter_spacing=1.2),
            ], spacing=6),
            *actions,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor="#6D28D9",
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
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
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(
                        width=32, height=32, stroke_width=3,
                        color="#7C3AED",
                    ),
                    ft.Text("Gemini đang phân tích...", size=10,
                            color="#7C3AED", text_align=ft.TextAlign.CENTER),
                    ft.Text("Vui lòng chờ vài giây",
                            size=9, color=C["dim"],
                            text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=24),
            ),
        ]),
        bgcolor="#F5F3FF",
        border=ft.border.only(
            left=ft.border.BorderSide(3, "#7C3AED"),
        ),
    )


def _error(error: str) -> ft.Control:
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, size=16, color=C["red"]),
                ft.Text("Không định giá được", size=10,
                        weight=ft.FontWeight.BOLD, color=C["red"]),
            ], spacing=6),
            ft.Text(error[:120], size=9, color=C["dim"]),
        ], spacing=4),
        padding=ft.padding.all(12),
        bgcolor="#FEF2F2",
        border=ft.border.only(left=ft.border.BorderSide(3, C["red"])),
    )


def _result(p: PricingResult, copy_cb: Optional[Callable]) -> ft.Control:
    items: list = []

    # ── Giá thu mua (hero) ────────────────────────────────────────────────────
    buy_lo = _fmt(p.buy_min)
    buy_hi = _fmt(p.buy_max)
    items.append(ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.ARROW_DOWNWARD_ROUNDED,
                        size=13, color="#15803D"),
                ft.Text("GIÁ THU MUA", size=9,
                        weight=ft.FontWeight.BOLD,
                        color="#15803D", letter_spacing=0.8),
            ], spacing=4),
            ft.Row([
                ft.Text(buy_lo, size=22,
                        weight=ft.FontWeight.BOLD, color="#15803D"),
                ft.Text("đ", size=13, color="#15803D",
                        weight=ft.FontWeight.BOLD),
            ], spacing=3, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([
                ft.Text("đến", size=10, color="#166534"),
                ft.Text(f"{buy_hi} đ", size=13,
                        weight=ft.FontWeight.BOLD, color="#166534"),
            ], spacing=4),
        ], spacing=2),
        bgcolor="#DCFCE7",
        border=ft.border.all(1, "#86EFAC"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        margin=ft.margin.only(left=8, right=8, top=8, bottom=4),
    ))

    # ── Divider ───────────────────────────────────────────────────────────────
    items.append(ft.Divider(height=1, color=C["border"]))

    # ── Tóm tắt ───────────────────────────────────────────────────────────────
    if p.summary:
        items.append(ft.Container(
            content=ft.Text(p.summary, size=10, color=C["text"],
                            italic=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        ))

    # ── Điểm cộng ─────────────────────────────────────────────────────────────
    if p.strengths:
        items.append(_section_label("✅  Điểm cộng", "#15803D"))
        for s in p.strengths:
            items.append(_bullet(s, C["green"], "•"))

    # ── Điểm trừ ──────────────────────────────────────────────────────────────
    if p.weaknesses:
        items.append(_section_label("⚠️  Điểm trừ", "#92400E"))
        for w in p.weaknesses:
            items.append(_bullet(w, C["yellow"], "•"))

    # ── Lý do định giá (collapsible) ──────────────────────────────────────────
    if p.reasoning:
        items.append(ft.Divider(height=1, color=C["border"]))
        items.append(ft.Container(
            content=ft.Text(p.reasoning, size=9, color=C["dim"],
                            italic=True),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        ))

    # ── Copy button ───────────────────────────────────────────────────────────
    items.append(ft.Divider(height=1, color=C["border"]))
    copy_text = p.copy_text
    items.append(ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.COPY_ALL_ROUNDED, size=14, color="white"),
                ft.Text("Copy kết quả", size=10, color="white",
                        weight=ft.FontWeight.BOLD),
            ], spacing=6, tight=True),
            on_click=lambda _, t=copy_text: copy_cb(t) if copy_cb else None,
            bgcolor="#6D28D9",
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                shape=ft.RoundedRectangleBorder(radius=6),
            ),
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=8),
    ))

    return ft.Column(items, spacing=0)


def _raw_fallback(raw: str) -> ft.Control:
    """Hiển thị khi Gemini trả về text không parse được."""
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,
                        size=14, color=C["yellow"]),
                ft.Text("Kết quả thô từ Gemini", size=10,
                        color=C["yellow"], weight=ft.FontWeight.BOLD),
            ], spacing=6),
            ft.Container(
                content=ft.Text(raw[:400] if raw else "Không có dữ liệu",
                                size=9, color=C["dim"]),
                bgcolor=C["card2"],
                border_radius=6,
                padding=ft.padding.all(8),
            ),
        ], spacing=6),
        padding=ft.padding.all(10),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(val: Optional[int]) -> str:
    if val is None:
        return "—"
    return f"{val:,.0f}".replace(",", ".")


def _section_label(text: str, color: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(text, size=9, weight=ft.FontWeight.BOLD,
                        color=color),
        padding=ft.padding.only(left=10, top=6, bottom=2),
    )


def _bullet(text: str, color: str, symbol: str = "•") -> ft.Control:
    return ft.Container(
        content=ft.Row([
            ft.Text(symbol, size=10, color=color),
            ft.Text(text, size=9, color=C["text"], expand=True),
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
        padding=ft.padding.only(left=14, right=8, bottom=3),
    )
