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
    else:
        # macOS / Linux fallback (để dev/test)
        info["manufacturer"] = "Apple" if platform.system() == "Darwin" else "Unknown"
        info["model"] = platform.machine()
        info["serial_number"] = _get_mac_serial()
        info["bios_version"] = "N/A"

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


def _get_mac_serial():
    """Lấy serial trên macOS (dùng để dev)."""
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPHardwareDataType"],
            text=True, stderr=subprocess.DEVNULL
        )
        match = re.search(r"Serial Number.*?:\s*(\S+)", out)
        return match.group(1) if match else "Unknown"
    except Exception:
        return "Unknown"


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
    elif platform.system() == "Darwin":
        battery.update(_parse_mac_battery())

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
        "display": get_display_info(),
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
