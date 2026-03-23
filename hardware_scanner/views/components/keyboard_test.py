"""
Component: Keyboard test widget — full-screen overlay khi test.
Tự phát hiện layout thiết bị (MacBook / laptop), hiện phím sáng khi nhấn.
Dùng page.overlay để chặn focus leak sang widget khác.
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from views.components.theme import C

# ── Keyboard layouts ──────────────────────────────────────────────────────────

_MACBOOK = [
    ["esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
    ["`",   "1",  "2",  "3",  "4",  "5",  "6",  "7",  "8",  "9",  "0",  "-",  "=",  "del"],
    ["tab", "Q",  "W",  "E",  "R",  "T",  "Y",  "U",  "I",  "O",  "P",  "[",  "]",  "\\"],
    ["caps","A",  "S",  "D",  "F",  "G",  "H",  "J",  "K",  "L",  ";",  "'",  "return"],
    ["⇧",   "Z",  "X",  "C",  "V",  "B",  "N",  "M",  ",",  ".",  "/",  "⇧"],
    ["fn",  "ctrl","opt","⌘",  "space",              "⌘",  "opt","←",  "↑","↓", "→"],
]

_LAPTOP = [
    ["Esc","F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12","Del"],
    ["`",  "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",  "-",  "=", "⌫"],
    ["Tab","Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",  "[",  "]", "\\"],
    ["Caps","A","S", "D", "F", "G", "H", "J", "K", "L", ";",  "'",  "↵"],
    ["⇧",  "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/",  "⇧"],
    ["Ctrl","Win","Alt","Space",            "Alt","Fn","Ctrl","←","↑","↓","→"],
]

# Chiều rộng đặc biệt theo label
_W: dict[str, int] = {
    "space": 160, "Space": 160,
    "⌫": 56, "del": 52, "return": 60, "↵": 60,
    "tab": 52, "Tab": 52,
    "caps": 64, "Caps": 64,
    "⇧": 76, "Ctrl": 44, "ctrl": 44,
    "Alt": 40, "opt": 40,
    "⌘": 44, "Win": 44, "Fn": 36, "fn": 36,
    "\\": 44,
}

# Flet key name → label trong layout
_KEY_MAP: dict[str, str] = {
    "Escape": "esc", "Backspace": "⌫", "Delete": "del",
    "Tab": "tab", "Caps Lock": "caps", "Enter": "return",
    " ": "space", "Shift": "⇧", "Control": "ctrl",
    "Alt": "opt", "Meta": "⌘",
    **{f"F{i}": f"F{i}" for i in range(1, 13)},
    # Laptop mapping
    "BackSpace": "⌫",
}
_KEY_MAP_LAPTOP: dict[str, str] = {
    "Escape": "Esc", "Backspace": "⌫", "Delete": "Del",
    "Tab": "Tab", "Caps Lock": "Caps", "Enter": "↵",
    " ": "Space", "Shift": "⇧", "Control": "Ctrl",
    "Alt": "Alt", "Meta": "Win", "Super_L": "Win", "Super_R": "Win",
    **{f"F{i}": f"F{i}" for i in range(1, 13)},
}


def detect_layout(model: str) -> str:
    """Trả về 'macbook' hoặc 'laptop' dựa theo tên model."""
    m = model.lower()
    if any(k in m for k in ("macbook", "mac book")):
        return "macbook"
    return "laptop"


class KeyboardTestWidget:
    """
    Hiển thị nút test inline.
    Khi test bắt đầu → push full-screen overlay lên page.overlay,
    tránh Tab/Space/Enter kích hoạt widget bên dưới.
    """

    def __init__(self, page: ft.Page, on_refresh: Callable,
                 model: str = ""):
        self._page = page
        self._on_refresh = on_refresh
        self._layout = detect_layout(model)
        self._rows = _MACBOOK if self._layout == "macbook" else _LAPTOP
        self._key_map = _KEY_MAP if self._layout == "macbook" else _KEY_MAP_LAPTOP
        self._all_labels: set[str] = {lbl for row in self._rows for lbl in row}
        self._total = len(self._all_labels)
        self._pressed: set[str] = set()
        self._active = False
        self._prev_kb = None
        self._overlay_ref: Optional[ft.Control] = None

    # ── Public ────────────────────────────────────────────────────────────────

    def set_model(self, model: str):
        """Gọi sau khi biết model thiết bị."""
        self._layout = detect_layout(model)
        self._rows = _MACBOOK if self._layout == "macbook" else _LAPTOP
        self._key_map = _KEY_MAP if self._layout == "macbook" else _KEY_MAP_LAPTOP
        self._all_labels = {lbl for row in self._rows for lbl in row}
        self._total = len(self._all_labels)

    def start(self):
        self._pressed = set()
        self._active = True
        self._prev_kb = self._page.on_keyboard_event
        self._page.on_keyboard_event = self._on_key
        self._push_overlay()

    def stop(self):
        self._active = False
        self._page.on_keyboard_event = self._prev_kb
        self._pop_overlay()
        self._on_refresh()

    def reset(self):
        if self._active:
            self.stop()
        self._pressed = set()

    def build(self) -> ft.Control:
        """Inline widget (chỉ nút bấm) — overlay là toàn màn hình riêng."""
        pressed = len(self._pressed)
        if pressed == 0:
            label = "⌨  Kiểm tra bàn phím"
        else:
            pct = int(pressed * 100 / self._total)
            label = f"⌨  Mở lại test bàn phím  ({pressed}/{self._total} = {pct}%)"

        btn_color = C["green"] if pressed > 0 else C["accent"]
        return ft.Container(
            content=ft.Column([
                ft.ElevatedButton(
                    label,
                    on_click=lambda _: self.start(),
                    bgcolor=btn_color, color="white",
                ),
                *([ft.Text(
                    f"✅ {len(self._pressed)}/{self._total} phím đã nhấn",
                    size=9, color=C["dim"],
                )] if self._pressed else []),
            ], spacing=4),
            padding=ft.padding.symmetric(vertical=6, horizontal=8),
        )

    # ── Overlay ───────────────────────────────────────────────────────────────

    def _push_overlay(self):
        overlay = ft.Container(
            content=self._overlay_content(),
            bgcolor=C["bg"],
            expand=True,
        )
        self._overlay_ref = overlay
        self._page.overlay.append(overlay)
        try:
            self._page.update()
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

    def _rebuild_overlay(self):
        """Cập nhật nội dung overlay khi có phím mới."""
        if self._overlay_ref:
            self._overlay_ref.content = self._overlay_content()
            try:
                self._overlay_ref.update()
            except Exception:
                pass

    def _overlay_content(self) -> ft.Control:
        pressed = len(self._pressed)
        pct = pressed / max(self._total, 1)
        bar_c = C["green"] if pct >= 0.9 else (C["yellow"] if pct >= 0.5 else C["accent"])
        layout_label = "MacBook" if self._layout == "macbook" else "Laptop"

        header = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(
                        f"⌨  Kiểm tra bàn phím  —  Layout: {layout_label}",
                        size=14, weight=ft.FontWeight.BOLD, color=C["text"],
                    ),
                    ft.Text(
                        "⚠  Phím Win/Cmd hoạt động ở cấp hệ điều hành, không thể chặn",
                        size=9, color=C["yellow"], italic=True,
                    ),
                ], spacing=2, expand=True),
                ft.ElevatedButton(
                    "✕  Xong",
                    on_click=lambda _: self.stop(),
                    bgcolor=C["accent"], color="white",
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=C["card"],
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border=ft.border.only(bottom=ft.border.BorderSide(1, C["border"])),
        )

        progress = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"{pressed}/{self._total} phím đã nhấn", size=10, color=C["dim"]),
                    ft.Text(f"{int(pct*100)}%", size=10,
                            color=bar_c, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.ProgressBar(value=pct, color=bar_c, bgcolor=C["border"], height=6),
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
        )

        kbd_rows = []
        for row in self._rows:
            key_cells = []
            for label in row:
                is_on = label in self._pressed
                bg = C["green"] if is_on else C["card"]
                tc = "white" if is_on else C["dim"]
                brd = ft.border.all(1, C["green"] if is_on else C["border"])
                w = _W.get(label, max(32, len(label) * 9 + 14))
                key_cells.append(ft.Container(
                    content=ft.Text(label, size=10, color=tc,
                                    text_align=ft.TextAlign.CENTER, no_wrap=True),
                    bgcolor=bg, width=w, height=32,
                    border_radius=5, border=brd,
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(right=3, bottom=3),
                ))
            kbd_rows.append(ft.Container(
                content=ft.Row(key_cells, spacing=0, scroll=ft.ScrollMode.AUTO),
                padding=ft.padding.only(left=0),
            ))

        hint = ft.Container(
            content=ft.Text(
                "Nhấn từng phím để kiểm tra  •  Màu xanh = hoạt động  •  Phím chưa nhấn = chưa rõ",
                size=9, color=C["dim"], italic=True,
            ),
            padding=ft.padding.only(top=8),
        )

        kbd_area = ft.Container(
            content=ft.Column([*kbd_rows, hint], spacing=0),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        )

        return ft.Column([header, progress, kbd_area], spacing=0, expand=True)

    # ── Keyboard handler ──────────────────────────────────────────────────────

    def _on_key(self, e: ft.KeyboardEvent):
        label = self._normalize(e.key)
        if label and label in self._all_labels:
            self._pressed.add(label)
            self._rebuild_overlay()

    def _normalize(self, key: str) -> str:
        if key in self._key_map:
            return self._key_map[key]
        if len(key) == 1:
            return key.upper()
        return ""
