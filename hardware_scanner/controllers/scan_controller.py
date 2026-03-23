"""
Controller: Hardware scanning.
Runs scanner.py functions in a background thread, fires callbacks on main thread.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable, Optional

import scanner
from models.hardware import HardwareData


class ScanController:
    def __init__(self):
        self._data: Optional[HardwareData] = None
        self._on_progress: Optional[Callable[[str], None]] = None
        self._on_done: Optional[Callable[[HardwareData], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    def set_callbacks(
        self,
        on_progress: Optional[Callable[[str], None]] = None,
        on_done: Optional[Callable[[HardwareData], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._on_progress = on_progress
        self._on_done = on_done
        self._on_error = on_error

    @property
    def data(self) -> Optional[HardwareData]:
        return self._data

    def reset(self):
        self._data = None

    def start_scan(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        steps = [
            ("Thông tin hệ thống...", "system",     scanner.get_system_info),
            ("CPU...",               "cpu",         scanner.get_cpu_info),
            ("RAM...",               "ram",         scanner.get_ram_info),
            ("Ổ cứng...",            "storage",     scanner.get_storage_info),
            ("Pin...",               "battery",     scanner.get_battery_info),
            ("Card đồ họa...",       "gpu",         scanner.get_gpu_info),
            ("Camera & Mic...",      "camera_mic",       scanner.get_camera_mic_info),
            ("WiFi & Bluetooth...",  "wifi_bluetooth",   scanner.get_wifi_bluetooth_info),
        ]
        result = {"scan_timestamp": datetime.now().isoformat()}
        try:
            for msg, key, fn in steps:
                if self._on_progress:
                    self._on_progress(msg)
                result[key] = fn()
            self._data = HardwareData.from_raw(result)
            if self._on_done:
                self._on_done(self._data)
        except Exception as e:
            if self._on_error:
                self._on_error(str(e))
