"""
Components: Grade badge + Red flags banner.
Pure functions — không có state, không có side effects.
"""
from __future__ import annotations

from typing import List

import flet as ft

from models.checklist import GradeResult
from views.components.theme import C


def grade_badge(grade: GradeResult, answered: int, total: int) -> ft.Control:
    """
    Hiển thị grade to (A/B/C/D/REJECT), mô tả, điểm phạt,
    và progress bar đếm số câu đã trả lời.
    """
    pct = answered / max(total, 1)
    prog_color = C["green"] if answered == total else C["yellow"]

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    grade.grade, size=52, weight=ft.FontWeight.BOLD,
                    color=grade.color, text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    grade.description, size=11, color=grade.color,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    f"Tổng điểm phạt: {grade.score}",
                    size=10, color=C["dim"], text_align=ft.TextAlign.CENTER,
                ) if not grade.is_rejected else ft.Container(height=0),
                ft.Text(
                    f"{answered}/{total} câu đã trả lời",
                    size=10, color=prog_color, text_align=ft.TextAlign.CENTER,
                ),
                ft.ProgressBar(
                    value=pct, color=prog_color,
                    bgcolor=C["border"], height=5,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        bgcolor=C["card"],
        padding=ft.padding.symmetric(vertical=16, horizontal=12),
    )


def red_flags_banner(flags: List[str]) -> ft.Control:
    """Banner đỏ liệt kê các lỗi nghiêm trọng (red_flag = True)."""
    items: List[ft.Control] = [
        ft.Text(
            "🚩  LỖI NGHIÊM TRỌNG",
            size=11, weight=ft.FontWeight.BOLD, color="white",
            text_align=ft.TextAlign.CENTER,
        )
    ]
    for flag in flags:
        items.append(ft.Text(
            flag, size=10, color="white", text_align=ft.TextAlign.CENTER,
        ))
    return ft.Container(
        content=ft.Column(
            items,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        ),
        bgcolor=C["red"],
        padding=ft.padding.symmetric(vertical=8, horizontal=12),
    )
