"""
View: Tab 1 — Cấu hình phần cứng (chỉ hiển thị thông tin, không test).
"""
from __future__ import annotations

import flet as ft

from models.hardware import HardwareData
from views.components.theme import C
from views.components.hw_info import hw_section, hw_row
from views.components.loading_spinner import LoadingSpinner


class HardwareTab:
    def __init__(self, page: ft.Page):
        self._page = page
        self._spinner = LoadingSpinner()
        self._main_col = ft.Column(
            controls=[self._centered_spinner()],
            spacing=0,
        )

    def build(self) -> ft.Control:
        return ft.Container(
            content=self._main_col,
            expand=True,
            bgcolor=C["bg"],
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def show_loading(self):
        self._spinner.set_progress("")
        self._main_col.controls = [self._centered_spinner()]

    def update_progress(self, msg: str):
        self._spinner.set_progress(msg)

    def show_data(self, data: HardwareData):
        self._main_col.controls = self._build_rows(data)

    # ── Private ───────────────────────────────────────────────────────────────

    def _centered_spinner(self) -> ft.Control:
        return ft.Container(
            content=self._spinner.build(),
            expand=True,
            alignment=ft.alignment.center,
        )

    def _build_rows(self, data: HardwareData) -> list:
        rows: list = []

        def sec(title: str):
            rows.extend(hw_section(title))

        def row(*args, **kwargs):
            rows.append(hw_row(*args, **kwargs))

        s = data.system
        sec("💻  THÔNG TIN MÁY")
        row("Hãng",   s.manufacturer)
        row("Model",  s.model,          bold=True)
        row("Serial", s.serial_number,  mono=True, color=C["accent"])
        row("BIOS",   s.bios_version,   dim=True)
        row("OS",     f"{s.os}  {s.os_version[:40]}", dim=True)

        sec("🔲  CPU")
        row("Tên",   data.cpu.name, bold=True)
        row("Cores", (
            f"{data.cpu.physical_cores} lõi vật lý  /  "
            f"{data.cpu.logical_cores} luồng  •  "
            f"{data.cpu.max_freq_ghz} GHz"
        ))

        sec("📦  RAM")
        row("Tổng", f"{data.ram.total_gb} GB", bold=True)
        for i, sl in enumerate(data.ram.slots, 1):
            row(f"Khe {i}",
                f"{sl.capacity_gb} GB  {sl.type}  {sl.speed_mhz} MHz  ({sl.manufacturer})")

        sec("💾  Ổ CỨNG")
        if data.storage:
            for d in data.storage:
                row(d.name, f"{d.size_gb} GB  •  {d.interface}")
        else:
            row("—", "Không phát hiện ổ cứng", dim=True)

        sec("🎮  CARD ĐỒ HỌA")
        if data.gpu:
            for g in data.gpu:
                parts = []
                if g.vram_gb:    parts.append(f"{g.vram_gb} GB VRAM")
                elif g.vram_mb:  parts.append(f"{g.vram_mb} MB VRAM")
                if g.type:       parts.append(g.type)
                if g.resolution: parts.append(g.resolution)
                row(g.name, "  •  ".join(parts) or "—",
                    color=C["accent"] if g.type == "Dedicated" else None)
        else:
            row("—", "Không phát hiện GPU", dim=True)

        sec("🔋  PIN")
        batt = data.battery
        if batt.present:
            if batt.health_percent is not None:
                h = batt.health_percent
                hc = C["green"] if h >= 80 else (C["yellow"] if h >= 60 else C["red"])
                row("Sức khỏe", f"{h}%", bold=True, color=hc)
            if batt.design_capacity_mwh:
                row("Dung lượng TK", f"{batt.design_capacity_mwh:,} mWh")
            if batt.full_charge_capacity_mwh:
                row("Hiện tại", f"{batt.full_charge_capacity_mwh:,} mWh")
            if batt.cycle_count:
                cc = batt.cycle_count
                row("Số lần sạc", f"{cc} lần",
                    color=C["green"] if cc < 300 else (C["yellow"] if cc < 600 else C["red"]))
        else:
            row("—", "Không có pin / pin đã tháo", dim=True)

        sec("📶  WIFI & BLUETOOTH")
        w = data.wifi
        if w.present:
            row("WiFi", w.card_type or "Phát hiện", bold=True, color=C["green"])
            if w.phy_modes:
                row("Chuẩn", w.phy_modes)
            status = w.status if w.status else "Không kết nối"
            if status.lower() == "connected":
                sc = C["green"]
            elif not w.status:
                sc = C["yellow"]
            else:
                sc = C["red"] if status.lower() == "off" else C["yellow"]
            row("Trạng thái", status, color=sc)
            if w.status.lower() == "connected":
                if w.current_phy:
                    row("Đang dùng", w.current_phy)
                if w.signal_dbm is not None:
                    sq = (C["green"] if w.signal_dbm >= -60
                          else C["yellow"] if w.signal_dbm >= -75 else C["red"])
                    row("Tín hiệu", f"{w.signal_dbm} dBm", color=sq)
                if w.tx_rate:
                    row("Tốc độ TX", f"{w.tx_rate} Mbps")
        else:
            row("WiFi", "Không phát hiện card", color=C["red"])

        bt = data.bluetooth
        if bt.present:
            bt_on = bt.state.lower() == "on"
            bt_color = C["green"] if bt_on else C["yellow"]
            label = f"{bt.state}  {'• ' + bt.chipset if bt.chipset else ''}".strip()
            row("Bluetooth", label, bold=True, color=bt_color)
            if bt_on:
                if bt.connected_devices:
                    for dev in bt.connected_devices:
                        row("Đã kết nối", dev, color=C["accent"])
                else:
                    row("Đã kết nối", "Không có thiết bị", dim=True)
            else:
                row("", "Bật Bluetooth để kiểm tra thiết bị", dim=True)
        else:
            row("Bluetooth", "Không phát hiện", color=C["red"])

        sec("📷  CAMERA & MICROPHONE")
        cam = data.camera
        if cam.cameras:
            for name in cam.cameras:
                row("Camera", name, bold=True, color=C["green"])
        else:
            row("Camera", "Không phát hiện", color=C["red"])
        if cam.mics:
            for name in cam.mics:
                row("Microphone", name, color=C["green"])
        else:
            row("Microphone", "Không phát hiện", color=C["red"])

        rows.append(ft.Container(height=20))
        return rows
