"""
O2O Laptop Inspection - Hardware Scanner
Chạy trên laptop cần test (Windows), thu thập cấu hình và sinh QR Code.
Không cần cài đặt, không cần mạng - chạy từ USB.
"""

import json
import subprocess
import platform
import re
import sys
import os
import tempfile
from datetime import datetime


def get_system_info():
    """Thu thập thông tin hệ điều hành và model máy."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "hostname": platform.node(),
    }

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()

            # Model & Serial Number từ BIOS/System
            for cs in c.Win32_ComputerSystem():
                info["manufacturer"] = cs.Manufacturer.strip()
                info["model"] = cs.Model.strip()

            for bios in c.Win32_BIOS():
                info["serial_number"] = bios.SerialNumber.strip()
                info["bios_version"] = bios.SMBIOSBIOSVersion.strip()

        except ImportError:
            # Fallback nếu không có wmi
            info.update(_wmic_fallback_system())
    elif platform.system() == "Darwin":
        mac = _get_mac_system_info()
        info["manufacturer"] = "Apple"
        info["model"]         = mac.get("model", platform.machine())
        info["serial_number"] = mac.get("serial", "Unknown")
        info["bios_version"]  = mac.get("firmware", "N/A")
    else:
        info["manufacturer"] = "Unknown"
        info["model"]         = platform.machine()
        info["serial_number"] = "Unknown"
        info["bios_version"]  = "N/A"

    return info


def _wmic_fallback_system():
    """Dùng wmic command khi không có thư viện wmi."""
    result = {}
    try:
        out = subprocess.check_output(
            ["wmic", "computersystem", "get", "Manufacturer,Model", "/format:csv"],
            text=True, stderr=subprocess.DEVNULL
        )
        lines = [l for l in out.strip().splitlines() if l.strip() and l.strip() != "Node,Manufacturer,Model"]
        if lines:
            parts = lines[0].split(",")
            if len(parts) >= 3:
                result["manufacturer"] = parts[1].strip()
                result["model"] = parts[2].strip()

        out = subprocess.check_output(
            ["wmic", "bios", "get", "SerialNumber,SMBIOSBIOSVersion", "/format:csv"],
            text=True, stderr=subprocess.DEVNULL
        )
        lines = [l for l in out.strip().splitlines() if l.strip() and "SerialNumber" not in l and l.strip()]
        if lines:
            parts = lines[0].split(",")
            if len(parts) >= 3:
                result["serial_number"] = parts[2].strip()
                result["bios_version"] = parts[1].strip()
    except Exception:
        result.setdefault("manufacturer", "Unknown")
        result.setdefault("model", "Unknown")
        result.setdefault("serial_number", "Unknown")
        result.setdefault("bios_version", "Unknown")
    return result


def _get_mac_system_info() -> dict:
    """Parse system_profiler SPHardwareDataType → model, serial, firmware."""
    result = {}
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPHardwareDataType"],
            text=True, stderr=subprocess.DEVNULL
        )
        def _field(pattern):
            m = re.search(pattern, out, re.IGNORECASE)
            return m.group(1).strip() if m else None

        name       = _field(r"Model Name\s*:\s*(.+)")
        identifier = _field(r"Model Identifier\s*:\s*(\S+)")
        serial     = _field(r"Serial Number.*?:\s*(\S+)")
        firmware   = _field(r"System Firmware Version\s*:\s*(.+)")

        # Ghép "MacBook Air (MacBookAir10,1)"
        if name and identifier:
            result["model"] = f"{name} ({identifier})"
        elif name:
            result["model"] = name
        elif identifier:
            result["model"] = identifier

        if serial:
            result["serial"] = serial
        if firmware:
            result["firmware"] = firmware
    except Exception:
        pass
    return result


def get_cpu_info():
    """Thu thập thông tin CPU."""
    import psutil

    info = {
        "name": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_freq_ghz": None,
    }

    freq = psutil.cpu_freq()
    if freq:
        info["max_freq_ghz"] = round(freq.max / 1000, 2) if freq.max else round(freq.current / 1000, 2)

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for cpu in c.Win32_Processor():
                info["name"] = cpu.Name.strip()
                info["max_freq_ghz"] = round(cpu.MaxClockSpeed / 1000, 2)
                break
        except ImportError:
            try:
                out = subprocess.check_output(
                    ["wmic", "cpu", "get", "Name,MaxClockSpeed", "/format:csv"],
                    text=True, stderr=subprocess.DEVNULL
                )
                lines = [l for l in out.strip().splitlines() if l.strip() and "Name" not in l and l.strip()]
                if lines:
                    parts = lines[0].split(",")
                    if len(parts) >= 3:
                        info["max_freq_ghz"] = round(int(parts[1].strip()) / 1000, 2)
                        info["name"] = parts[2].strip()
            except Exception:
                pass
    elif platform.system() == "Darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True, stderr=subprocess.DEVNULL
            )
            info["name"] = out.strip()
        except Exception:
            pass

    return info


def get_ram_info():
    """Thu thập thông tin RAM."""
    import psutil

    vm = psutil.virtual_memory()
    info = {
        "total_gb": round(vm.total / (1024 ** 3), 1),
        "slots": [],
    }

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for stick in c.Win32_PhysicalMemory():
                info["slots"].append({
                    "capacity_gb": round(int(stick.Capacity) / (1024 ** 3), 1),
                    "speed_mhz": stick.Speed,
                    "type": _ram_type_name(stick.MemoryType),
                    "manufacturer": (stick.Manufacturer or "Unknown").strip(),
                })
        except ImportError:
            try:
                out = subprocess.check_output(
                    ["wmic", "memorychip", "get", "Capacity,Speed,MemoryType,Manufacturer", "/format:csv"],
                    text=True, stderr=subprocess.DEVNULL
                )
                for line in out.strip().splitlines():
                    if not line.strip() or "Capacity" in line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 5:
                        try:
                            info["slots"].append({
                                "capacity_gb": round(int(parts[1].strip()) / (1024 ** 3), 1),
                                "speed_mhz": parts[3].strip(),
                                "type": _ram_type_name(int(parts[4].strip()) if parts[4].strip().isdigit() else 0),
                                "manufacturer": parts[2].strip(),
                            })
                        except Exception:
                            pass
            except Exception:
                pass

    return info


def _ram_type_name(type_id):
    """Map mã loại RAM sang tên."""
    types = {0: "Unknown", 20: "DDR", 21: "DDR2", 22: "DDR2 FB-DIMM",
             24: "DDR3", 26: "DDR4", 34: "DDR5"}
    return types.get(type_id, f"Type-{type_id}")


def get_storage_info():
    """Thu thập thông tin ổ cứng."""
    import psutil

    drives = []

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                drives.append({
                    "name": disk.Caption.strip(),
                    "size_gb": round(int(disk.Size) / (1024 ** 3), 1) if disk.Size else 0,
                    "interface": disk.InterfaceType.strip() if disk.InterfaceType else "Unknown",
                    "serial": (disk.SerialNumber or "Unknown").strip(),
                })
        except ImportError:
            try:
                out = subprocess.check_output(
                    ["wmic", "diskdrive", "get", "Caption,Size,InterfaceType,SerialNumber", "/format:csv"],
                    text=True, stderr=subprocess.DEVNULL
                )
                for line in out.strip().splitlines():
                    if not line.strip() or "Caption" in line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 5:
                        try:
                            drives.append({
                                "name": parts[1].strip(),
                                "size_gb": round(int(parts[4].strip()) / (1024 ** 3), 1) if parts[4].strip().isdigit() else 0,
                                "interface": parts[3].strip(),
                                "serial": parts[2].strip(),  # Note: wmic thường ẩn serial
                            })
                        except Exception:
                            pass
            except Exception:
                pass
    elif platform.system() == "Darwin":
        drives = _get_mac_disks()
    else:
        # Linux fallback
        seen = set()
        for part in psutil.disk_partitions():
            if part.device in seen:
                continue
            seen.add(part.device)
            try:
                usage = psutil.disk_usage(part.mountpoint)
                drives.append({
                    "name": part.device,
                    "size_gb": round(usage.total / (1024 ** 3), 1),
                    "interface": part.fstype,
                    "serial": "N/A",
                })
            except Exception:
                pass

    return drives


def _get_mac_disks():
    """Lấy danh sách physical disk trên macOS (chỉ physical, không virtual/image)."""
    drives = []
    try:
        import plistlib
        out = subprocess.check_output(
            ["diskutil", "list", "-plist"],
            text=True, stderr=subprocess.DEVNULL
        )
        plist = plistlib.loads(out.encode())
        whole_disks = plist.get("WholeDisks", [])

        for disk_id in whole_disks:
            try:
                info_out = subprocess.check_output(
                    ["diskutil", "info", "-plist", disk_id],
                    text=True, stderr=subprocess.DEVNULL
                )
                info = plistlib.loads(info_out.encode())

                # Chỉ giữ physical disk: Virtual = "Virtual" thì bỏ, Disk Image thì bỏ
                virtual = info.get("VirtualOrPhysical", "Unknown")
                if virtual.lower() == "virtual":
                    continue
                bus = info.get("BusProtocol", "")
                if bus == "Disk Image":
                    continue

                size_bytes = info.get("TotalSize", 0)
                drives.append({
                    "name": info.get("MediaName", disk_id),
                    "size_gb": round(size_bytes / (1024 ** 3), 1),
                    "interface": bus or "Unknown",
                    "serial": info.get("DiskSerialNumber", "N/A"),
                })
            except Exception:
                pass
    except Exception:
        pass
    return drives


def get_battery_info():
    """
    Thu thập thông tin pin.
    Windows: dùng powercfg /batteryreport để lấy Design & Full Charge Capacity.
    """
    battery = {
        "present": False,
        "design_capacity_mwh": None,
        "full_charge_capacity_mwh": None,
        "health_percent": None,
        "cycle_count": None,
    }

    if platform.system() == "Darwin":
        # macOS: psutil không reliable cho M1, dùng system_profiler luôn
        mac_info = _parse_mac_battery()
        if mac_info:
            battery["present"] = True
            battery.update(mac_info)
            # Tính health nếu chưa có
            if not battery.get("health_percent") and battery.get("design_capacity_mwh") and battery.get("full_charge_capacity_mwh"):
                d = battery["design_capacity_mwh"]
                f = battery["full_charge_capacity_mwh"]
                if d > 0:
                    battery["health_percent"] = round((f / d) * 100, 1)
        return battery

    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt is None:
            return battery
        battery["present"] = True
    except Exception:
        return battery

    if platform.system() == "Windows":
        battery.update(_parse_windows_battery_report())

    # Tính % chai pin
    if battery.get("design_capacity_mwh") and battery.get("full_charge_capacity_mwh"):
        d = battery["design_capacity_mwh"]
        f = battery["full_charge_capacity_mwh"]
        if d > 0:
            battery["health_percent"] = round((f / d) * 100, 1)

    return battery


def _parse_windows_battery_report():
    """Chạy powercfg, parse HTML report để lấy capacity."""
    result = {}
    tmp_path = os.path.join(tempfile.gettempdir(), "batteryreport_o2o.html")

    try:
        subprocess.run(
            ["powercfg", "/batteryreport", "/output", tmp_path],
            capture_output=True, timeout=30
        )

        if not os.path.exists(tmp_path):
            return result

        with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        # Parse Design Capacity
        design_match = re.search(
            r"DESIGN CAPACITY.*?(\d[\d,]+)\s*mWh",
            html, re.IGNORECASE | re.DOTALL
        )
        if design_match:
            result["design_capacity_mwh"] = int(design_match.group(1).replace(",", ""))

        # Parse Full Charge Capacity
        full_match = re.search(
            r"FULL CHARGE CAPACITY.*?(\d[\d,]+)\s*mWh",
            html, re.IGNORECASE | re.DOTALL
        )
        if full_match:
            result["full_charge_capacity_mwh"] = int(full_match.group(1).replace(",", ""))

        # Parse Cycle Count
        cycle_match = re.search(
            r"CYCLE COUNT.*?(\d+)",
            html, re.IGNORECASE | re.DOTALL
        )
        if cycle_match:
            result["cycle_count"] = int(cycle_match.group(1))

        os.remove(tmp_path)

    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    return result


def _parse_mac_battery():
    """Lấy thông tin pin trên macOS dùng system_profiler."""
    result = {}
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPPowerDataType"],
            text=True, stderr=subprocess.DEVNULL
        )

        design = re.search(r"Maximum Capacity.*?:\s*(\d+)%", out)
        if design:
            result["health_percent"] = float(design.group(1))

        cycle = re.search(r"Cycle Count.*?:\s*(\d+)", out)
        if cycle:
            result["cycle_count"] = int(cycle.group(1))

        # Thử lấy capacity tuyệt đối
        full = re.search(r"Full Charge Capacity \(mAh\).*?:\s*(\d+)", out)
        design_cap = re.search(r"Design Capacity.*?:\s*(\d+)", out)
        if full:
            result["full_charge_capacity_mwh"] = int(full.group(1))
        if design_cap:
            result["design_capacity_mwh"] = int(design_cap.group(1))

    except Exception:
        pass
    return result


def get_gpu_info():
    """Thu thập thông tin card đồ họa (GPU)."""
    gpus = []

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for gpu in c.Win32_VideoController():
                vram_mb = None
                if gpu.AdapterRAM:
                    vram_mb = round(int(gpu.AdapterRAM) / (1024 ** 2))
                gpus.append({
                    "name": gpu.Caption.strip(),
                    "vram_mb": vram_mb,
                    "vram_gb": round(vram_mb / 1024, 1) if vram_mb else None,
                    "driver_version": (gpu.DriverVersion or "").strip(),
                    "resolution": (
                        f"{gpu.CurrentHorizontalResolution}x{gpu.CurrentVerticalResolution}"
                        if gpu.CurrentHorizontalResolution else None
                    ),
                    "type": _gpu_type(gpu.Caption or ""),
                })
        except ImportError:
            try:
                out = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController",
                     "get", "Caption,AdapterRAM,DriverVersion,CurrentHorizontalResolution,CurrentVerticalResolution",
                     "/format:csv"],
                    text=True, stderr=subprocess.DEVNULL
                )
                for line in out.strip().splitlines():
                    if not line.strip() or "Caption" in line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 6:
                        try:
                            vram_mb = round(int(parts[2].strip()) / (1024 ** 2)) if parts[2].strip().isdigit() else None
                            gpus.append({
                                "name": parts[1].strip(),
                                "vram_mb": vram_mb,
                                "vram_gb": round(vram_mb / 1024, 1) if vram_mb else None,
                                "driver_version": parts[3].strip(),
                                "resolution": f"{parts[4].strip()}x{parts[5].strip()}" if parts[4].strip() else None,
                                "type": _gpu_type(parts[1]),
                            })
                        except Exception:
                            pass
            except Exception:
                pass

    elif platform.system() == "Darwin":
        gpus = _get_mac_gpu()

    return gpus


def _gpu_type(name):
    """Phân loại GPU: Integrated / Dedicated."""
    name_lower = name.lower()
    integrated_keywords = ["intel", "uhd", "iris", "hd graphics", "apple m", "amd radeon(tm)"]
    dedicated_keywords  = ["nvidia", "geforce", "rtx", "gtx", "quadro",
                           "radeon rx", "radeon pro", "arc"]
    for k in dedicated_keywords:
        if k in name_lower:
            return "Dedicated"
    for k in integrated_keywords:
        if k in name_lower:
            return "Integrated"
    return "Unknown"


def _get_mac_gpu():
    """Lấy thông tin GPU trên macOS qua system_profiler."""
    gpus = []
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType"],
            text=True, stderr=subprocess.DEVNULL
        )

        # Mỗi GPU bắt đầu bằng tên chip (dòng đầu trong block)
        # system_profiler trả về dạng text có indent
        current = {}
        for line in out.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # Dòng tên GPU (không có dấu ':' ở cuối)
            if not stripped.endswith(":") and ":" not in stripped and len(stripped) > 3:
                if current:
                    gpus.append(current)
                current = {"name": stripped, "type": _gpu_type(stripped)}
                continue

            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip().lower()
                val = val.strip()

                if "vram" in key or "memory" in key:
                    # "VRAM (Total): 16 GB" hoặc "Chipset Model: Apple M1"
                    num = re.search(r"(\d+)\s*(gb|mb)", val, re.IGNORECASE)
                    if num:
                        amount = int(num.group(1))
                        unit   = num.group(2).upper()
                        current["vram_gb"] = amount if unit == "GB" else round(amount / 1024, 1)
                        current["vram_mb"] = amount * 1024 if unit == "GB" else amount

                elif "chipset model" in key:
                    current["name"] = val
                    current["type"] = _gpu_type(val)

                elif "metal" in key:
                    current["metal"] = val

                elif "resolution" in key and "resolution" not in current:
                    current["resolution"] = val

        if current:
            gpus.append(current)

        # Deduplicate nếu GPU xuất hiện nhiều lần (tích hợp + built-in display)
        seen = set()
        unique = []
        for g in gpus:
            if g.get("name") and g["name"] not in seen:
                seen.add(g["name"])
                unique.append(g)
        gpus = unique

    except Exception:
        pass
    return gpus


def get_display_info():
    """Thu thập thông tin màn hình (Windows)."""
    displays = []

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for monitor in c.Win32_VideoController():
                displays.append({
                    "name": monitor.Caption.strip(),
                    "resolution": f"{monitor.CurrentHorizontalResolution}x{monitor.CurrentVerticalResolution}",
                    "vram_mb": round(int(monitor.AdapterRAM) / (1024 ** 2)) if monitor.AdapterRAM else None,
                })
        except Exception:
            pass

    return displays


def get_wifi_bluetooth_info():
    """Tự động phát hiện WiFi và Bluetooth."""
    if platform.system() == "Darwin":
        return _mac_wifi_bluetooth()
    if platform.system() == "Windows":
        return _win_wifi_bluetooth()
    return {"wifi": {}, "bluetooth": {}}


def _mac_wifi_bluetooth():
    result = {"wifi": {}, "bluetooth": {}}

    # ── WiFi ──────────────────────────────────────────────────────────────────
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPAirPortDataType"],
            text=True, stderr=subprocess.DEVNULL
        )
        wifi = {"present": True}
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("Card Type:"):
                wifi["card_type"] = s.split(":", 1)[1].strip()
            elif s.startswith("MAC Address:"):
                wifi["mac"] = s.split(":", 1)[1].strip()
            elif s.startswith("Supported PHY Modes:"):
                wifi["phy_modes"] = s.split(":", 1)[1].strip()
            elif s.startswith("Status:"):
                wifi["status"] = s.split(":", 1)[1].strip()
            elif s.startswith("PHY Mode:") and "current_phy" not in wifi:
                wifi["current_phy"] = s.split(":", 1)[1].strip()
            elif s.startswith("Signal / Noise:") and "signal" not in wifi:
                parts = s.split(":", 1)[1].strip().split("/")
                try:
                    wifi["signal_dbm"] = int(parts[0].strip().split()[0])
                    wifi["noise_dbm"] = int(parts[1].strip().split()[0])
                except Exception:
                    pass
            elif s.startswith("Transmit Rate:") and "tx_rate" not in wifi:
                wifi["tx_rate"] = s.split(":", 1)[1].strip()
        result["wifi"] = wifi
    except Exception:
        result["wifi"] = {"present": False}

    # ── Bluetooth ──────────────────────────────────────────────────────────────
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPBluetoothDataType"],
            text=True, stderr=subprocess.DEVNULL
        )
        bt = {"present": True, "connected_devices": []}
        in_connected = False
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("State:"):
                bt["state"] = s.split(":", 1)[1].strip()
            elif s.startswith("Chipset:"):
                bt["chipset"] = s.split(":", 1)[1].strip()
            elif s.startswith("Address:") and "address" not in bt:
                bt["address"] = s.split(":", 1)[1].strip()
            elif s.startswith("Firmware Version:") and "firmware" not in bt:
                bt["firmware"] = s.split(":", 1)[1].strip()
            elif s == "Connected:":
                in_connected = True
            elif s == "Not Connected:":
                in_connected = False
            elif in_connected and s.endswith(":") and s not in ("Connected:", "Not Connected:"):
                dev_name = s.rstrip(":")
                if dev_name:
                    bt["connected_devices"].append(dev_name)
        result["bluetooth"] = bt
    except Exception:
        result["bluetooth"] = {"present": False}

    return result


def _win_wifi_bluetooth():
    result = {"wifi": {"present": False}, "bluetooth": {"present": False}}
    try:
        import wmi
        c = wmi.WMI()
        for adapter in c.Win32_NetworkAdapter():
            name = (adapter.Name or "").lower()
            if "wi-fi" in name or "wireless" in name or "802.11" in name or "wifi" in name:
                result["wifi"] = {
                    "present": True,
                    "card_type": adapter.Name,
                    "mac": adapter.MACAddress or "",
                    "status": "Connected" if adapter.NetConnectionStatus == 2 else "Disconnected",
                }
                break
        for dev in c.Win32_PnPEntity():
            if (dev.PNPClass or "").lower() == "bluetooth":
                result["bluetooth"] = {
                    "present": True,
                    "state": "On",
                    "card_type": dev.Name,
                    "connected_devices": [],
                }
                break
    except Exception:
        try:
            out = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                text=True, stderr=subprocess.DEVNULL
            )
            if "Name" in out:
                wifi = {"present": True, "connected_devices": []}
                for line in out.splitlines():
                    s = line.strip()
                    if s.startswith("SSID") and "BSSID" not in s:
                        wifi["ssid"] = s.split(":", 1)[1].strip()
                    elif s.startswith("Signal"):
                        wifi["signal_pct"] = s.split(":", 1)[1].strip()
                    elif s.startswith("Radio type"):
                        wifi["phy_modes"] = s.split(":", 1)[1].strip()
                result["wifi"] = wifi
        except Exception:
            pass
    return result


def get_camera_mic_info():
    """Tự động phát hiện camera và microphone."""
    cameras, mics = [], []

    if platform.system() == "Darwin":
        cameras = _mac_cameras()
        mics = _mac_mics()
    elif platform.system() == "Windows":
        cameras, mics = _win_camera_mic()

    return {
        "cameras": cameras,
        "mics": mics,
        "camera_ok": len(cameras) > 0,
        "mic_ok": len(mics) > 0,
    }


def _mac_cameras():
    """Liệt kê camera trên macOS qua system_profiler."""
    cameras = []
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPCameraDataType"],
            text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            s = line.strip()
            if s.endswith(":") and s not in ("Camera:", "Cameras:") and len(s) > 2:
                cameras.append(s.rstrip(":"))
    except Exception:
        pass
    return cameras


def _mac_mics():
    """Liệt kê microphone (input device) trên macOS."""
    mics = []
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPAudioDataType"],
            text=True, stderr=subprocess.DEVNULL
        )
        current = None
        is_input = False
        for line in out.splitlines():
            s = line.strip()
            if s.endswith(":") and s not in ("Audio:", "Devices:"):
                # Save previous device if it was an input device
                if current and is_input:
                    mics.append(current)
                current = s.rstrip(":")
                is_input = False
            elif current and ("Input Channels" in s or "Default Input Device" in s):
                is_input = True
        if current and is_input:
            mics.append(current)
    except Exception:
        pass
    return mics


def _win_camera_mic():
    """Liệt kê camera và mic trên Windows."""
    cameras, mics = [], []
    try:
        import wmi
        c = wmi.WMI()
        for dev in c.Win32_PnPEntity():
            cls = (dev.PNPClass or "").lower()
            if cls in ("camera", "image"):
                cameras.append(dev.Name.strip())
        for dev in c.Win32_SoundDevice():
            mics.append(dev.Name.strip())
    except ImportError:
        try:
            # wmic fallback
            out = subprocess.check_output(
                ["wmic", "path", "Win32_PnPEntity",
                 "where", "PNPClass='Camera' OR PNPClass='Image'",
                 "get", "Name", "/format:csv"],
                text=True, stderr=subprocess.DEVNULL
            )
            for line in out.strip().splitlines():
                parts = line.split(",")
                if len(parts) >= 2 and parts[1].strip() and "Name" not in parts[1]:
                    cameras.append(parts[1].strip())
            out = subprocess.check_output(
                ["wmic", "sounddev", "get", "Name", "/format:csv"],
                text=True, stderr=subprocess.DEVNULL
            )
            for line in out.strip().splitlines():
                parts = line.split(",")
                if len(parts) >= 2 and parts[1].strip() and "Name" not in parts[1]:
                    mics.append(parts[1].strip())
        except Exception:
            pass
    except Exception:
        pass
    return cameras, mics


def collect_all():
    """Thu thập toàn bộ thông tin phần cứng."""
    print("Đang thu thập thông tin phần cứng...")

    data = {
        "scan_timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "storage": get_storage_info(),
        "battery": get_battery_info(),
        "gpu": get_gpu_info(),
        "display": get_display_info(),
        "camera_mic": get_camera_mic_info(),
    }

    return data


def print_summary(data):
    """In tóm tắt thông tin ra console."""
    s = data["system"]
    cpu = data["cpu"]
    ram = data["ram"]
    batt = data["battery"]
    storage = data["storage"]

    print("\n" + "=" * 60)
    print("  O2O LAPTOP INSPECTION - KẾT QUẢ QUÉT CẤU HÌNH")
    print("=" * 60)
    print(f"  Hãng    : {s.get('manufacturer', 'N/A')}")
    print(f"  Model   : {s.get('model', 'N/A')}")
    print(f"  Serial  : {s.get('serial_number', 'N/A')}")
    print(f"  BIOS    : {s.get('bios_version', 'N/A')}")
    print("-" * 60)
    print(f"  CPU     : {cpu.get('name', 'N/A')}")
    print(f"           {cpu.get('physical_cores', '?')} lõi vật lý / {cpu.get('logical_cores', '?')} luồng | {cpu.get('max_freq_ghz', '?')} GHz")
    print("-" * 60)
    print(f"  RAM     : {ram.get('total_gb', '?')} GB tổng")
    for i, slot in enumerate(ram.get("slots", []), 1):
        print(f"           Khe {i}: {slot['capacity_gb']} GB {slot['type']} {slot['speed_mhz']} MHz ({slot['manufacturer']})")
    print("-" * 60)
    print(f"  Ổ cứng  :")
    for disk in storage:
        print(f"           {disk['name']} | {disk['size_gb']} GB | {disk['interface']}")
    print("-" * 60)
    if batt.get("present"):
        if batt.get("health_percent"):
            health = batt["health_percent"]
            health_icon = "🟢" if health >= 80 else ("🟡" if health >= 60 else "🔴")
            print(f"  Pin     : {health}% sức khỏe {health_icon}")
        if batt.get("design_capacity_mwh"):
            print(f"           Thiết kế: {batt['design_capacity_mwh']} mWh | Hiện tại: {batt.get('full_charge_capacity_mwh', 'N/A')} mWh")
        if batt.get("cycle_count"):
            print(f"           Số lần sạc: {batt['cycle_count']} lần")
    else:
        print(f"  Pin     : Không có (máy bàn / pin đã tháo)")
    print("=" * 60)


def generate_qr(data):
    """Sinh mã QR từ dữ liệu JSON và hiển thị lên màn hình."""
    try:
        import qrcode
    except ImportError:
        print("\n[!] Thiếu thư viện qrcode. Chạy: pip install qrcode[pil]")
        print("    QR Code không được tạo, nhưng dữ liệu JSON đã có.")
        return None

    # Tạo payload gọn để QR không quá nặng
    payload = {
        "v": 1,  # version schema
        "ts": data["scan_timestamp"],
        "mfr": data["system"].get("manufacturer", ""),
        "mdl": data["system"].get("model", ""),
        "sn": data["system"].get("serial_number", ""),
        "cpu": data["cpu"].get("name", ""),
        "cpu_cores": data["cpu"].get("physical_cores"),
        "cpu_ghz": data["cpu"].get("max_freq_ghz"),
        "ram_gb": data["ram"].get("total_gb"),
        "ram_slots": [
            {"gb": s["capacity_gb"], "type": s["type"], "mhz": s["speed_mhz"]}
            for s in data["ram"].get("slots", [])
        ],
        "disks": [
            {"name": d["name"], "gb": d["size_gb"], "iface": d["interface"]}
            for d in data["storage"]
        ],
        "batt_health": data["battery"].get("health_percent"),
        "batt_cycles": data["battery"].get("cycle_count"),
        "batt_design_mwh": data["battery"].get("design_capacity_mwh"),
        "batt_full_mwh": data["battery"].get("full_charge_capacity_mwh"),
    }

    json_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    qr = qrcode.QRCode(
        version=None,  # tự động chọn version
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(json_str)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Lưu file và mở
    qr_path = os.path.join(tempfile.gettempdir(), "o2o_laptop_qr.png")
    img.save(qr_path)

    print(f"\n  QR Code đã lưu tại: {qr_path}")

    # Mở ảnh QR bằng viewer mặc định
    try:
        if platform.system() == "Windows":
            os.startfile(qr_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", qr_path])
        else:
            subprocess.run(["xdg-open", qr_path])
        print("  [✓] QR Code đang hiển thị - Dùng app mobile để quét!")
    except Exception as e:
        print(f"  [!] Không thể tự mở ảnh: {e}")
        print(f"      Mở thủ công tại: {qr_path}")

    return qr_path


def save_json(data, output_path=None):
    """Lưu kết quả JSON ra file."""
    if output_path is None:
        output_path = os.path.join(
            tempfile.gettempdir(),
            f"o2o_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  JSON đã lưu: {output_path}")
    return output_path


def main():
    print("O2O Laptop Inspection - Hardware Scanner v1.0")
    print("Đang khởi động...\n")

    try:
        import psutil
    except ImportError:
        print("[LỖI] Thiếu thư viện psutil. Chạy: pip install psutil")
        sys.exit(1)

    data = collect_all()
    print_summary(data)
    save_json(data)
    generate_qr(data)

    print("\n[✓] Hoàn tất! Giữ màn hình để app mobile quét QR Code.")
    if platform.system() == "Windows":
        input("\nNhấn Enter để thoát...")


if __name__ == "__main__":
    main()
