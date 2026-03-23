"""
Component: Hardware info section header + data row.
Pure functions, không có state.
"""
from __future__ import annotations

from typing import Optional, List
import flet as ft

from views.components.theme import C


def hw_section(title: str) -> List[ft.Control]:
    """Header dòng tiêu đề + divider cho một nhóm thông tin phần cứng."""
    return [
        ft.Container(
            content=ft.Text(
                title, color=C["accent"], size=11,
                weight=ft.FontWeight.BOLD,
            ),
            padding=ft.padding.only(left=8, top=12, bottom=2),
        ),
        ft.Divider(height=1, color=C["border"]),
    ]


def hw_row(
    label: str,
    value: str,
    bold: bool = False,
    mono: bool = False,
    dim: bool = False,
    color: Optional[str] = None,
) -> ft.Control:
    """Một dòng label + value trong bảng thông tin phần cứng."""
    fg = color or (C["dim"] if dim else C["text"])
    weight = ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL
    font_family = "Courier New" if mono else None
    return ft.Container(
        content=ft.Row([
            ft.Text(
                label, color=C["dim"], size=10, width=130,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Text(
                str(value) if value else "—",
                color=fg, size=10,
                weight=weight,
                font_family=font_family,
                expand=True,
                no_wrap=False,
            ),
        ]),
        bgcolor=C["card"],
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        margin=ft.margin.only(left=4, right=4, bottom=1),
        border_radius=4,
    )
