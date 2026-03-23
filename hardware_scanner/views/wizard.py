"""
View: Wizard — bố cục kiểm định tự động từng bước.
Thay thế 3-tab layout bằng 5 step cards xếp dọc.

Flow tự động:
  ① Quét phần cứng   (auto-run)
  ② Màn hình          (user bắt đầu + xác nhận kết quả)
  ③ Camera, Mic & Loa (auto-run khi step activate)
  ④ Bàn phím          (user tự nhấn phím, bấm Tiếp theo)
  ⑤ Kiểm định ngoại quan (user điền, auto-done khi xong hết)
"""
from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from controllers.checklist_controller import ChecklistController
from models.hardware import HardwareData
from models.checklist import GradeResult
from views.hardware_tab import HardwareTab
from views.checklist_tab import ChecklistTab
from views.components.cam_mic_widget import CamMicWidget
from views.components.keyboard_test import KeyboardTestWidget
from views.components.screen_test import ScreenTestWidget
from views.components.theme import C

# ── Step definitions ──────────────────────────────────────────────────────────

_STEPS = [
    dict(id="scan",      num="①", icon="💻", title="Quét phần cứng"),
    dict(id="screen",    num="②", icon="🖥️", title="Màn hình"),
    dict(id="camera",    num="③", icon="📷", title="Camera, Mic & Loa"),
    dict(id="keyboard",  num="④", icon="⌨️", title="Bàn phím"),
    dict(id="checklist", num="⑤", icon="✅", title="Kiểm định ngoại quan"),
]

_STEP_ORDER = [s["id"] for s in _STEPS]

# Steps có nút "Tiếp theo →" để user tự advance
_MANUAL_NEXT = {"camera", "keyboard"}


class WizardView:
    def __init__(
        self,
        page: ft.Page,
        cl_ctrl: ChecklistController,
        on_cam_mic_test: Callable,
        on_speaker_test: Callable,
        on_screen_result: Optional[Callable[[bool], None]] = None,
    ):
        self._page = page
        self._cl_ctrl = cl_ctrl
        self._on_cam_mic_test = on_cam_mic_test
        self._ext_screen_cb = on_screen_result

        # ── State ──────────────────────────────────────────────────────────────
        self._status: dict[str, str] = {s["id"]: "pending" for s in _STEPS}
        self._serial = ""

        # ── Sub-widgets ────────────────────────────────────────────────────────
        self._hw_tab = HardwareTab(page)

        self._screen = ScreenTestWidget(
            page,
            on_refresh=self._noop,
            on_result=self._on_screen_done,
        )

        self._cam_mic = CamMicWidget(
            page,
            on_refresh=self._refresh_cam,
            on_test=on_cam_mic_test,
            on_speaker_test=on_speaker_test,
        )
        self._cam_placeholder = ft.Container(
            content=self._cam_mic.build()
        )

        self._keyboard = KeyboardTestWidget(page, on_refresh=self._refresh_kb)
        self._kb_placeholder = ft.Container(
            content=self._keyboard.build()
        )

        self._cl_tab = ChecklistTab(cl_ctrl, page)

        # ── UI refs (populated in _build_cards) ───────────────────────────────
        self._badge_refs:   dict[str, ft.Container] = {}
        self._title_refs:   dict[str, ft.Text]      = {}
        self._summary_refs: dict[str, ft.Text]      = {}
        self._content_refs: dict[str, ft.Container] = {}
        self._next_refs:    dict[str, ft.Container] = {}
        self._card_refs:    dict[str, ft.Container] = {}

        # ── Progress bar ──────────────────────────────────────────────────────
        self._prog_bar  = ft.ProgressBar(
            value=0, color=C["accent"], bgcolor=C["border"], height=4,
        )
        self._prog_text = ft.Text("0 / 5 bước hoàn thành", size=10, color=C["dim"])

        # ── Main column ───────────────────────────────────────────────────────
        self._col = ft.Column(
            controls=self._build_all_cards(),
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=4,
        )

    # ── Public build ──────────────────────────────────────────────────────────

    def build(self) -> ft.Control:
        return ft.Container(
            content=ft.Column([
                # Progress header
                ft.Container(
                    content=ft.Row([
                        self._prog_bar,
                        ft.Container(content=self._prog_text, width=130),
                    ], spacing=10),
                    bgcolor=C["card"],
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    border=ft.border.only(
                        bottom=ft.border.BorderSide(1, C["border"])
                    ),
                ),
                # Step cards
                ft.Container(content=self._col, expand=True),
            ], spacing=0, expand=True),
            expand=True,
            bgcolor=C["bg"],
        )

    # ── Public API (called from app.py) ───────────────────────────────────────

    def show_scan_loading(self):
        self._hw_tab.show_loading()
        self._activate_step("scan")

    def update_scan_progress(self, msg: str):
        self._hw_tab.update_progress(msg)

    def on_scan_done(self, data: HardwareData):
        self._hw_tab.show_data(data)
        self._serial = data.system.serial_number or ""
        model = data.system.model or ""

        # Set model cho keyboard layout
        self._keyboard.set_model(model)

        # Tóm tắt
        cpu = data.cpu.name.split("@")[0].strip() if data.cpu.name else "?"
        ram = f"{data.ram.total_gb:.0f}GB"
        disk = f"{data.storage[0].size_gb:.0f}GB" if data.storage else "?"
        summary = f"{data.system.model}  •  {cpu}  •  {ram} RAM  •  {disk} SSD"
        self._mark_done("scan", summary)

        # Auto-advance → màn hình + tự fullscreen luôn
        self._activate_step("screen")
        self._screen.start()

    def set_cam_mic_loading(self):
        self._cam_mic.set_loading()

    def set_cam_mic_result(self, result):
        self._cam_mic.set_result(result)

    def set_speaker_loading(self):
        self._cam_mic.set_speaker_loading()

    def set_speaker_done(self, ok: bool):
        self._cam_mic.set_speaker_done(ok)

    def auto_answer_checklist(self, qid: str, idx: int):
        self._cl_tab.auto_answer(qid, idx)

    def on_checklist_change(self, answers: dict, grade):
        """Gọi từ app.py khi có answer thay đổi."""
        if self._cl_ctrl.is_complete:
            done_text = f"⭐ {grade.grade}  •  {grade.description}" if grade else "Hoàn thành"
            if self._status["checklist"] != "done":
                self._mark_done("checklist", done_text)

    def reset(self):
        self._cam_mic.reset()
        self._keyboard.reset()
        self._screen.reset()
        self._serial = ""
        for sid in _STEP_ORDER:
            self._status[sid] = "pending"
            self._apply_pending(sid)
        self._cam_placeholder.content = self._cam_mic.build()
        self._kb_placeholder.content  = self._keyboard.build()
        self._update_progress()
        try:
            self._col.update()
        except Exception:
            pass

    # ── Step state machine ────────────────────────────────────────────────────

    def _activate_step(self, step_id: str):
        if self._status[step_id] == "done":
            return
        self._status[step_id] = "active"

        cfg = next(s for s in _STEPS if s["id"] == step_id)
        badge = self._badge_refs[step_id]
        badge.bgcolor = C["accent"]
        badge.content = ft.Text(
            cfg["num"], size=11, color="white", weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )

        t = self._title_refs[step_id]
        t.color  = C["accent"]
        t.weight = ft.FontWeight.BOLD

        self._content_refs[step_id].visible = True

        if step_id in _MANUAL_NEXT:
            self._next_refs[step_id].visible = True

        self._card_refs[step_id].border = ft.border.all(1, C["accent"])

        try:
            self._card_refs[step_id].update()
        except Exception:
            pass

        # Cuộn đến step đang active
        try:
            self._page.scroll_to(key=f"step_{step_id}", duration=400)
        except Exception:
            pass

    def _mark_done(self, step_id: str, summary: str = ""):
        self._status[step_id] = "done"

        badge = self._badge_refs[step_id]
        badge.bgcolor = C["green"]
        badge.content = ft.Text(
            "✓", size=11, color="white", weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )

        t = self._title_refs[step_id]
        t.color  = C["dim"]
        t.weight = ft.FontWeight.NORMAL

        self._summary_refs[step_id].value   = f"  {summary}"
        self._summary_refs[step_id].visible = True

        # Luôn giữ content visible sau khi done

        if step_id in _MANUAL_NEXT:
            self._next_refs[step_id].visible = False

        self._card_refs[step_id].border = ft.border.all(1, C["green"])

        self._update_progress()
        try:
            self._card_refs[step_id].update()
        except Exception:
            pass

    def _apply_pending(self, step_id: str):
        """Reset về trạng thái pending (dùng khi rescan)."""
        cfg = next(s for s in _STEPS if s["id"] == step_id)
        badge = self._badge_refs.get(step_id)
        if badge:
            badge.bgcolor = C["border"]
            badge.content = ft.Text(
                cfg["num"], size=11, color=C["dim"],
                text_align=ft.TextAlign.CENTER,
            )
        t = self._title_refs.get(step_id)
        if t:
            t.color  = C["dim"]
            t.weight = ft.FontWeight.NORMAL

        sr = self._summary_refs.get(step_id)
        if sr:
            sr.value   = ""
            sr.visible = False

        cr = self._content_refs.get(step_id)
        if cr:
            cr.visible = False

        nr = self._next_refs.get(step_id)
        if nr:
            nr.visible = False

        card = self._card_refs.get(step_id)
        if card:
            card.border = ft.border.all(1, C["border"])

    def _on_next_clicked(self, step_id: str):
        """User bấm "Tiếp theo" trên step thủ công."""
        idx = _STEP_ORDER.index(step_id)
        label_map = {
            "camera":   "✓ Camera, Mic & Loa đã kiểm tra",
            "keyboard": "✓ Bàn phím đã kiểm tra",
        }
        self._mark_done(step_id, label_map.get(step_id, "✓ Xong"))
        next_id = _STEP_ORDER[idx + 1] if idx + 1 < len(_STEP_ORDER) else None
        if next_id:
            self._activate_step(next_id)

    def _on_screen_done(self, passed: bool):
        """Callback từ ScreenTestWidget khi user xác nhận kết quả."""
        summary = "✅ Bình thường" if passed else "❌ Có điểm chết / sọc"
        self._mark_done("screen", summary)
        if self._ext_screen_cb:
            self._ext_screen_cb(passed)
        # Auto-advance → camera + auto-trigger test luôn
        self._activate_step("camera")
        self._on_cam_mic_test()

    def _update_progress(self):
        done  = sum(1 for s in _STEP_ORDER if self._status[s] == "done")
        total = len(_STEP_ORDER)
        self._prog_bar.value  = done / total if total else 0
        self._prog_text.value = f"{done} / {total} bước hoàn thành"
        try:
            self._prog_bar.update()
            self._prog_text.update()
        except Exception:
            pass

    # ── Card builders ─────────────────────────────────────────────────────────

    def _build_all_cards(self) -> list:
        cards = []
        for cfg in _STEPS:
            cards.append(self._build_card(cfg))
        return cards

    def _build_card(self, cfg: dict) -> ft.Control:
        sid = cfg["id"]

        # Badge
        badge = ft.Container(
            content=ft.Text(
                cfg["num"], size=11, color=C["dim"],
                text_align=ft.TextAlign.CENTER,
            ),
            bgcolor=C["border"],
            width=26, height=26,
            border_radius=13,
            alignment=ft.alignment.center,
        )
        self._badge_refs[sid] = badge

        # Title
        title = ft.Text(
            f"{cfg['icon']}  {cfg['title']}",
            size=12, color=C["dim"],
        )
        self._title_refs[sid] = title

        # Summary (hiện khi done)
        summary = ft.Text("", size=10, color=C["dim"], visible=False, expand=True)
        self._summary_refs[sid] = summary

        # Content (hidden by default)
        content_inner = self._build_content(sid)
        content = ft.Container(
            content=content_inner,
            visible=False,
            padding=ft.padding.only(left=34, right=8, top=2, bottom=8),
        )
        self._content_refs[sid] = content

        # Header row
        header = ft.Container(
            content=ft.Row(
                [badge, title, summary],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )

        card_children = [header, content]

        # "Tiếp theo" button (manual steps only)
        if sid in _MANUAL_NEXT:
            next_btn = ft.Container(
                content=ft.ElevatedButton(
                    "Tiếp theo  →",
                    on_click=lambda _, s=sid: self._on_next_clicked(s),
                    bgcolor=C["accent"],
                    color="white",
                    height=36,
                ),
                visible=False,
                padding=ft.padding.only(left=34, bottom=10),
            )
            self._next_refs[sid] = next_btn
            card_children.append(next_btn)

        # Outer card
        card = ft.Container(
            key=f"step_{sid}",
            content=ft.Column(card_children, spacing=0),
            bgcolor=C["card"],
            border=ft.border.all(1, C["border"]),
            border_radius=8,
            margin=ft.margin.symmetric(horizontal=6, vertical=2),
        )
        self._card_refs[sid] = card
        return card

    def _build_content(self, sid: str) -> ft.Control:
        if sid == "scan":
            return self._hw_tab.build()

        if sid == "screen":
            return self._screen.build()

        if sid == "camera":
            return self._cam_placeholder

        if sid == "keyboard":
            return self._kb_placeholder

        if sid == "checklist":
            return self._cl_tab.build()

        return ft.Container()

    # ── Refresh callbacks ─────────────────────────────────────────────────────

    def _refresh_cam(self):
        self._cam_placeholder.content = self._cam_mic.build()
        try:
            self._cam_placeholder.update()
        except Exception:
            pass

    def _refresh_kb(self):
        self._kb_placeholder.content = self._keyboard.build()
        try:
            self._kb_placeholder.update()
        except Exception:
            pass

    @staticmethod
    def _noop():
        pass
