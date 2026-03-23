"""
Model: Hardware data structures.
Pure data — no UI, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SystemInfo:
    os: str = ""
    os_version: str = ""
    hostname: str = ""
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    bios_version: str = ""


@dataclass
class CpuInfo:
    name: str = ""
    physical_cores: Optional[int] = None
    logical_cores: Optional[int] = None
    max_freq_ghz: Optional[float] = None


@dataclass
class RamSlot:
    capacity_gb: float = 0.0
    speed_mhz: str = ""
    type: str = ""
    manufacturer: str = ""


@dataclass
class RamInfo:
    total_gb: float = 0.0
    slots: list = field(default_factory=list)  # list[RamSlot]


@dataclass
class DiskInfo:
    name: str = ""
    size_gb: float = 0.0
    interface: str = ""
    serial: str = ""


@dataclass
class BatteryInfo:
    present: bool = False
    design_capacity_mwh: Optional[int] = None
    full_charge_capacity_mwh: Optional[int] = None
    health_percent: Optional[float] = None
    cycle_count: Optional[int] = None


@dataclass
class GpuInfo:
    name: str = ""
    vram_mb: Optional[int] = None
    vram_gb: Optional[float] = None
    driver_version: str = ""
    resolution: Optional[str] = None
    type: str = ""


@dataclass
class WifiInfo:
    present: bool = False
    card_type: str = ""
    mac: str = ""
    phy_modes: str = ""      # "802.11 a/b/g/n/ac/ax"
    status: str = ""         # "Connected" / "Disconnected"
    current_phy: str = ""    # "802.11ax"
    signal_dbm: Optional[int] = None
    noise_dbm: Optional[int] = None
    tx_rate: str = ""


@dataclass
class BluetoothInfo:
    present: bool = False
    state: str = ""          # "On" / "Off"
    chipset: str = ""
    address: str = ""
    firmware: str = ""
    connected_devices: list = field(default_factory=list)  # list[str]


@dataclass
class CameraInfo:
    cameras: list = field(default_factory=list)   # list[str] tên camera
    mics: list = field(default_factory=list)       # list[str] tên mic
    camera_ok: bool = False
    mic_ok: bool = False


@dataclass
class HardwareData:
    scan_timestamp: str = ""
    system: SystemInfo = field(default_factory=SystemInfo)
    cpu: CpuInfo = field(default_factory=CpuInfo)
    ram: RamInfo = field(default_factory=RamInfo)
    storage: list = field(default_factory=list)   # list[DiskInfo]
    battery: BatteryInfo = field(default_factory=BatteryInfo)
    gpu: list = field(default_factory=list)        # list[GpuInfo]
    camera: CameraInfo = field(default_factory=CameraInfo)
    wifi: WifiInfo = field(default_factory=WifiInfo)
    bluetooth: BluetoothInfo = field(default_factory=BluetoothInfo)

    @classmethod
    def from_raw(cls, raw: dict) -> "HardwareData":
        """Convert raw dict from scanner.py to HardwareData."""
        s = raw.get("system", {})
        cpu_r = raw.get("cpu", {})
        ram_r = raw.get("ram", {})
        batt_r = raw.get("battery", {})
        return cls(
            scan_timestamp=raw.get("scan_timestamp", ""),
            system=SystemInfo(
                os=s.get("os", ""),
                os_version=s.get("os_version", ""),
                hostname=s.get("hostname", ""),
                manufacturer=s.get("manufacturer", ""),
                model=s.get("model", ""),
                serial_number=s.get("serial_number", ""),
                bios_version=s.get("bios_version", ""),
            ),
            cpu=CpuInfo(
                name=cpu_r.get("name", ""),
                physical_cores=cpu_r.get("physical_cores"),
                logical_cores=cpu_r.get("logical_cores"),
                max_freq_ghz=cpu_r.get("max_freq_ghz"),
            ),
            ram=RamInfo(
                total_gb=ram_r.get("total_gb", 0.0),
                slots=[
                    RamSlot(
                        capacity_gb=sl.get("capacity_gb", 0.0),
                        speed_mhz=str(sl.get("speed_mhz", "")),
                        type=sl.get("type", ""),
                        manufacturer=sl.get("manufacturer", ""),
                    )
                    for sl in ram_r.get("slots", [])
                ],
            ),
            storage=[
                DiskInfo(
                    name=d.get("name", ""),
                    size_gb=d.get("size_gb", 0.0),
                    interface=d.get("interface", ""),
                    serial=d.get("serial", ""),
                )
                for d in raw.get("storage", [])
            ],
            battery=BatteryInfo(
                present=batt_r.get("present", False),
                design_capacity_mwh=batt_r.get("design_capacity_mwh"),
                full_charge_capacity_mwh=batt_r.get("full_charge_capacity_mwh"),
                health_percent=batt_r.get("health_percent"),
                cycle_count=batt_r.get("cycle_count"),
            ),
            gpu=[
                GpuInfo(
                    name=g.get("name", ""),
                    vram_mb=g.get("vram_mb"),
                    vram_gb=g.get("vram_gb"),
                    driver_version=g.get("driver_version", ""),
                    resolution=g.get("resolution"),
                    type=g.get("type", ""),
                )
                for g in raw.get("gpu", [])
            ],
            camera=CameraInfo(
                cameras=raw.get("camera_mic", {}).get("cameras", []),
                mics=raw.get("camera_mic", {}).get("mics", []),
                camera_ok=raw.get("camera_mic", {}).get("camera_ok", False),
                mic_ok=raw.get("camera_mic", {}).get("mic_ok", False),
            ),
            wifi=WifiInfo(
                **{k: v for k, v in raw.get("wifi_bluetooth", {}).get("wifi", {}).items()
                   if k in WifiInfo.__dataclass_fields__}
            ),
            bluetooth=BluetoothInfo(
                **{k: v for k, v in raw.get("wifi_bluetooth", {}).get("bluetooth", {}).items()
                   if k in BluetoothInfo.__dataclass_fields__}
            ),
        )

    def to_raw(self) -> dict:
        """Convert back to raw dict (for gemini_pricer compatibility)."""
        return {
            "scan_timestamp": self.scan_timestamp,
            "system": {
                "os": self.system.os,
                "os_version": self.system.os_version,
                "hostname": self.system.hostname,
                "manufacturer": self.system.manufacturer,
                "model": self.system.model,
                "serial_number": self.system.serial_number,
                "bios_version": self.system.bios_version,
            },
            "cpu": {
                "name": self.cpu.name,
                "physical_cores": self.cpu.physical_cores,
                "logical_cores": self.cpu.logical_cores,
                "max_freq_ghz": self.cpu.max_freq_ghz,
            },
            "ram": {
                "total_gb": self.ram.total_gb,
                "slots": [
                    {
                        "capacity_gb": sl.capacity_gb,
                        "speed_mhz": sl.speed_mhz,
                        "type": sl.type,
                        "manufacturer": sl.manufacturer,
                    }
                    for sl in self.ram.slots
                ],
            },
            "storage": [
                {"name": d.name, "size_gb": d.size_gb,
                 "interface": d.interface, "serial": d.serial}
                for d in self.storage
            ],
            "battery": {
                "present": self.battery.present,
                "design_capacity_mwh": self.battery.design_capacity_mwh,
                "full_charge_capacity_mwh": self.battery.full_charge_capacity_mwh,
                "health_percent": self.battery.health_percent,
                "cycle_count": self.battery.cycle_count,
            },
            "gpu": [
                {
                    "name": g.name,
                    "vram_mb": g.vram_mb,
                    "vram_gb": g.vram_gb,
                    "driver_version": g.driver_version,
                    "resolution": g.resolution,
                    "type": g.type,
                }
                for g in self.gpu
            ],
        }

    def to_qr_payload(
        self,
        grade: Optional[str] = None,
        score: Optional[int] = None,
        checklist_answers: Optional[dict] = None,
    ) -> dict:
        return {
            "v": 1,
            "ts": self.scan_timestamp,
            "mfr": self.system.manufacturer,
            "mdl": self.system.model,
            "sn": self.system.serial_number,
            "cpu": self.cpu.name,
            "cpu_cores": self.cpu.physical_cores,
            "cpu_ghz": self.cpu.max_freq_ghz,
            "ram_gb": self.ram.total_gb,
            "ram_slots": [
                {"gb": sl.capacity_gb, "type": sl.type, "mhz": sl.speed_mhz}
                for sl in self.ram.slots
            ],
            "disks": [
                {"name": d.name, "gb": d.size_gb, "iface": d.interface}
                for d in self.storage
            ],
            "batt_health": self.battery.health_percent,
            "batt_cycles": self.battery.cycle_count,
            "batt_design_mwh": self.battery.design_capacity_mwh,
            "batt_full_mwh": self.battery.full_charge_capacity_mwh,
            "gpus": [
                {"name": g.name, "vram_gb": g.vram_gb, "type": g.type}
                for g in self.gpu
            ],
            "grade": grade,
            "score": score,
            "checklist": checklist_answers or {},
        }
