"""
app.py — Entry point (Flet).
Wires controllers ↔ WizardView + Sidebar.
Flow tự động từng bước: Scan → Bảo hành → Màn hình → Camera → Bàn phím → Checklist → AI giá.
"""
from __future__ import annotations

import platform
import threading
import time
import uuid
from datetime import datetime

import flet as ft

from controllers.scan_controller import ScanController
from controllers.checklist_controller import ChecklistController
from controllers.pricing_controller import PricingController
from controllers.cam_mic_controller import CamMicController
from views.wizard import WizardView
from views.sidebar import Sidebar
from views.components.theme import C


def _request_permissions_macos():
    """
    macOS: probe camera + mic ngay lúc khởi động để trigger permission dialog sớm.
    Chạy trong background thread, không block UI.
    """
    if platform.system() != "Darwin":
        return

    def _probe():
        # Probe camera → trigger NSCameraUsageDescription dialog
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            cap.release()
        except Exception:
            pass
        # Probe mic → trigger NSMicrophoneUsageDescription dialog
        try:
            import sounddevice as sd
            sd.query_devices()
            sd.rec(1, samplerate=8000, channels=1, dtype="float32", blocking=False)
            sd.stop()
        except Exception:
            pass

    threading.Thread(target=_probe, daemon=True).start()


def main(page: ft.Page):
    page.title = "O2O Laptop Inspection"
    page.bgcolor = C["bg"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    try:
        page.window.width = 1160
        page.window.height = 740
        page.window.min_width = 960
        page.window.min_height = 640
    except Exception:
        pass

    # Xin quyền camera + mic sớm (macOS permission dialog)
    _request_permissions_macos()

    # ── Controllers ───────────────────────────────────────────────────────────
    scan_ctrl    = ScanController()
    cl_ctrl      = ChecklistController()
    price_ctrl   = PricingController()
    cam_mic_ctrl = CamMicController()

    # ── Views ─────────────────────────────────────────────────────────────────
    sidebar = Sidebar(page)

    wizard = WizardView(
        page,
        cl_ctrl=cl_ctrl,
        on_cam_mic_test=cam_mic_ctrl.test,
        on_speaker_test=cam_mic_ctrl.test_speaker,
        # on_screen_result wired sau khi status_text có
    )

    # ── Footer controls ───────────────────────────────────────────────────────
    status_text = ft.Text("Đang khởi động...", color=C["dim"], size=10)

    def start_scan(_=None):
        rescan_btn.disabled = True
        txn_text.value = _new_txn_id()
        # Reset toàn bộ trạng thái transaction cũ
        scan_ctrl.reset()
        price_ctrl.reset()
        cam_mic_ctrl.reset()
        cl_ctrl.reset()
        wizard.reset()                          # reset toàn bộ wizard về pending
        wizard.show_scan_loading()              # activate step scan
        sidebar.reset()
        status_text.value = "Đang thu thập dữ liệu phần cứng..."
        try:
            page.update()
        except Exception:
            pass
        scan_ctrl.start_scan()

    rescan_btn = ft.ElevatedButton(
        "⟳  Quét lại",
        disabled=True,
        bgcolor=C["accent"],
        color="white",
        on_click=start_scan,
    )

    # ── Transaction ID ────────────────────────────────────────────────────────
    txn_text = ft.Text("", color=C["dim"], size=10, font_family="monospace")

    def _new_txn_id() -> str:
        return "TXN-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4].upper()

    # ── Live clock ────────────────────────────────────────────────────────────
    clock_text = ft.Text("", color=C["dim"], size=10)

    def _tick():
        while True:
            try:
                clock_text.value = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
                page.update()
            except Exception:
                continue
            time.sleep(1)

    threading.Thread(target=_tick, daemon=True).start()

    # ── Page layout ───────────────────────────────────────────────────────────
    page.add(
        # Header
        ft.Container(
            content=ft.Row([
                ft.Text(
                    "O2O  LAPTOP  INSPECTION",
                    size=20, weight=ft.FontWeight.BOLD, color=C["accent"],
                ),
                ft.Container(content=txn_text, expand=True, alignment=ft.alignment.center),
                ft.Container(
                    content=clock_text,
                    alignment=ft.alignment.center_right,
                ),
            ]),
            bgcolor=C["card"],
            padding=ft.padding.symmetric(horizontal=24, vertical=12),
        ),
        ft.Container(bgcolor=C["accent"], height=2, margin=ft.margin.all(0)),
        # Body: wizard (left) + sidebar (right)
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=wizard.build(), expand=3, bgcolor=C["bg"]),
                    ft.Container(
                        content=sidebar.build(),
                        expand=2,
                        bgcolor=C["card"],
                        border=ft.border.only(
                            left=ft.border.BorderSide(1, C["border"])
                        ),
                    ),
                ],
                expand=True,
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            expand=True,
            padding=0,
        ),
        # Footer
        ft.Container(
            content=ft.Row([
                status_text,
                ft.Row(
                    [rescan_btn],
                    alignment=ft.MainAxisAlignment.END,
                    expand=True,
                ),
            ]),
            bgcolor=C["card"],
            padding=ft.padding.symmetric(horizontal=20, vertical=8),
            border=ft.border.only(top=ft.border.BorderSide(1, C["border"])),
        ),
    )

    # ── Wire screen result (cần status_text + wizard) ─────────────────────────

    def _on_screen_result(passed: bool):
        if not passed:
            wizard.auto_answer_checklist("screen", 2)
        status_text.value = (
            "✅ Màn hình bình thường" if passed
            else "⚠ Màn hình: phát hiện điểm chết / sọc"
        )
        try:
            page.update()
        except Exception:
            pass

    wizard._ext_screen_cb = _on_screen_result

    # ── Wire scan callbacks ───────────────────────────────────────────────────

    def on_scan_progress(msg: str):
        wizard.update_scan_progress(msg)
        try:
            page.update()
        except Exception:
            pass

    def on_scan_done(data):
        sidebar.set_hardware(data)

        # Auto-fill camera checklist từ device detection
        cam = data.camera
        if cam.camera_ok:
            wizard.auto_answer_checklist("camera", 0)
        elif not cam.cameras:
            wizard.auto_answer_checklist("camera", 2)

        wizard.on_scan_done(data)   # marks scan done + advance to screen

        sn = data.system.serial_number
        status_text.value = f"✓ Quét xong  •  SN: {sn}"
        rescan_btn.disabled = False
        try:
            page.update()
        except Exception:
            pass

    def on_scan_error(err: str):
        status_text.value = f"❌ Lỗi quét: {err}"
        rescan_btn.disabled = False
        try:
            page.update()
        except Exception:
            pass

    scan_ctrl.set_callbacks(
        on_progress=on_scan_progress,
        on_done=on_scan_done,
        on_error=on_scan_error,
    )

    # ── Wire checklist callbacks ──────────────────────────────────────────────

    def on_checklist_change(answers, grade):
        sidebar.update_grade(
            grade,
            cl_ctrl.answered_count,
            cl_ctrl.total_count,
            cl_ctrl.answers_as_labels(),
        )
        wizard.on_checklist_change(answers, grade)
        try:
            page.update()
        except Exception:
            pass
        if cl_ctrl.is_complete and scan_ctrl.data and grade:
            price_ctrl.request(scan_ctrl.data, answers, cl_ctrl.checklist, grade)

    cl_ctrl.set_on_change(on_checklist_change)

    # ── Wire pricing callbacks ────────────────────────────────────────────────

    def on_pricing_start():
        status_text.value = "🤖 Gemini đang phân tích định giá..."
        sidebar.show_pricing_loading()
        try:
            page.update()
        except Exception:
            pass

    def on_pricing_result(result):
        sn = scan_ctrl.data.system.serial_number if scan_ctrl.data else ""
        status_text.value = f"✓ Hoàn tất  •  SN: {sn}"
        sidebar.show_pricing(result)
        try:
            page.update()
        except Exception:
            pass

    price_ctrl.set_callbacks(on_start=on_pricing_start, on_result=on_pricing_result)

    def retry_pricing():
        if scan_ctrl.data and cl_ctrl.is_complete:
            grade = cl_ctrl.current_grade()
            if grade:
                price_ctrl.retry(
                    scan_ctrl.data, cl_ctrl.answers, cl_ctrl.checklist, grade)

    sidebar.set_retry_callback(retry_pricing)

    def copy_result(text: str):
        page.set_clipboard(text)
        status_text.value = "✓ Đã copy kết quả AI"
        try:
            page.update()
        except Exception:
            pass

    sidebar.set_copy_callback(copy_result)

    # ── Wire cam/mic callbacks ────────────────────────────────────────────────

    def on_cam_mic_start():
        status_text.value = "🎥 Đang kiểm tra camera & mic..."
        wizard.set_cam_mic_loading()
        try:
            page.update()
        except Exception:
            pass

    def on_cam_mic_result(result):
        wizard.set_cam_mic_result(result)
        idx = result.checklist_camera_idx
        if idx is not None:
            wizard.auto_answer_checklist("camera", idx)
        status_text.value = (
            f"✓ Camera: {result.camera_quality or '?'}  •  Mic: {result.mic_quality or '?'}"
        )
        try:
            page.update()
        except Exception:
            pass

    def on_speaker_start():
        wizard.set_speaker_loading()
        try:
            page.update()
        except Exception:
            pass

    def on_speaker_done(ok: bool):
        wizard.set_speaker_done(ok)
        status_text.value = "✓ Loa OK" if ok else "❌ Lỗi loa"
        try:
            page.update()
        except Exception:
            pass

    cam_mic_ctrl.set_callbacks(
        on_start=on_cam_mic_start,
        on_result=on_cam_mic_result,
        on_speaker_done=on_speaker_done,
        on_speaker_start=on_speaker_start,
    )

    # ── Kick off first scan ───────────────────────────────────────────────────
    start_scan()


if __name__ == "__main__":
    ft.app(target=main)
