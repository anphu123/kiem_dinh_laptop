"""
O2O Laptop Inspection - Hardware Scanner UI
Giao diện đồ họa: quét cấu hình + hiển thị kết quả + QR Code trong 1 cửa sổ.
"""

import tkinter as tk
from tkinter import ttk
import threading
import json
import io
import os
import tempfile
import platform
from datetime import datetime

import scanner  # module logic chính


# ── Bảng màu ────────────────────────────────────────────────────────────────
BG        = "#0F1117"   # nền tổng
CARD      = "#1A1D27"   # nền card
BORDER    = "#2A2D3E"   # viền card
ACCENT    = "#4F8EF7"   # xanh dương chính
ACCENT2   = "#00D4AA"   # xanh lá nhấn (pin tốt)
WARN      = "#F5A623"   # vàng (pin trung)
DANGER    = "#E74C3C"   # đỏ (pin yếu / lỗi)
TEXT      = "#E8EAED"   # text chính
TEXT_DIM  = "#6B7280"   # text mờ
TEXT_HEAD = "#FFFFFF"   # tiêu đề

FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_HEAD   = ("Segoe UI", 11, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_MONO   = ("Consolas", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_BIG    = ("Segoe UI", 36, "bold")


class ScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("O2O Laptop Inspection")
        self.configure(bg=BG)
        self.resizable(True, True)

        # Center cửa sổ
        w, h = 1100, 700
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(900, 600)

        self._data = None
        self._qr_img = None  # PhotoImage giữ reference

        self._build_header()
        self._build_body()
        self._build_footer()

        # Bắt đầu scan sau khi UI render xong
        self.after(200, self._start_scan)

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=CARD, pady=14)
        hdr.pack(fill="x")

        tk.Label(hdr, text="O2O  LAPTOP  INSPECTION",
                 font=FONT_TITLE, fg=TEXT_HEAD, bg=CARD).pack(side="left", padx=24)

        self._lbl_time = tk.Label(hdr, text="", font=FONT_SMALL,
                                   fg=TEXT_DIM, bg=CARD)
        self._lbl_time.pack(side="right", padx=24)

        sep = tk.Frame(self, bg=ACCENT, height=2)
        sep.pack(fill="x")

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ── Cột trái: thông tin phần cứng ──
        self._left = tk.Frame(body, bg=BG)
        self._left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # ── Cột phải: QR Code ──
        self._right = tk.Frame(body, bg=CARD, bd=0,
                                highlightthickness=1,
                                highlightbackground=BORDER)
        self._right.grid(row=0, column=1, sticky="nsew")

        self._build_loading_state()

    def _build_footer(self):
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

        foot = tk.Frame(self, bg=CARD, pady=8)
        foot.pack(fill="x")

        self._status = tk.Label(foot, text="Đang khởi động...",
                                 font=FONT_SMALL, fg=TEXT_DIM, bg=CARD)
        self._status.pack(side="left", padx=20)

        self._btn_rescan = tk.Button(
            foot, text="⟳  Quét lại", font=FONT_SMALL,
            bg=ACCENT, fg=TEXT_HEAD, activebackground="#3A6ED8",
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self._start_scan
        )
        self._btn_rescan.pack(side="right", padx=16)
        self._btn_rescan.config(state="disabled")

    # ── Loading state ────────────────────────────────────────────────────────

    def _build_loading_state(self):
        """Xóa nội dung cũ, hiển thị spinner text."""
        for w in self._left.winfo_children():
            w.destroy()
        for w in self._right.winfo_children():
            w.destroy()

        center = tk.Frame(self._left, bg=BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        self._spinner_label = tk.Label(center, text="⬤", font=FONT_BIG,
                                        fg=ACCENT, bg=BG)
        self._spinner_label.pack()

        self._scan_label = tk.Label(center, text="Đang quét cấu hình máy...",
                                     font=FONT_HEAD, fg=TEXT, bg=BG)
        self._scan_label.pack(pady=(12, 0))

        self._progress_lbl = tk.Label(center, text="",
                                       font=FONT_SMALL, fg=TEXT_DIM, bg=BG)
        self._progress_lbl.pack(pady=(4, 0))

        self._animate_spinner()

        # QR placeholder
        tk.Label(self._right, text="QR", font=("Segoe UI", 48, "bold"),
                 fg=BORDER, bg=CARD).place(relx=0.5, rely=0.5, anchor="center")

    def _animate_spinner(self, step=0):
        chars = ["◐", "◓", "◑", "◒"]
        if hasattr(self, "_spinner_label") and self._spinner_label.winfo_exists():
            self._spinner_label.config(text=chars[step % len(chars)])
            self._anim_id = self.after(200, self._animate_spinner, step + 1)

    # ── Scan thread ──────────────────────────────────────────────────────────

    def _start_scan(self):
        self._btn_rescan.config(state="disabled")
        self._build_loading_state()
        self._set_status("Đang thu thập dữ liệu...")
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        steps = [
            ("Thông tin hệ thống...", scanner.get_system_info),
            ("CPU...",               scanner.get_cpu_info),
            ("RAM...",               scanner.get_ram_info),
            ("Ổ cứng...",            scanner.get_storage_info),
            ("Pin...",               scanner.get_battery_info),
            ("Màn hình...",          scanner.get_display_info),
        ]
        keys   = ["system", "cpu", "ram", "storage", "battery", "display"]
        result = {"scan_timestamp": datetime.now().isoformat()}

        for (msg, fn), key in zip(steps, keys):
            self.after(0, lambda m=msg: self._update_progress(m))
            result[key] = fn()

        self._data = result
        self.after(0, self._on_scan_done)

    def _update_progress(self, msg):
        if hasattr(self, "_progress_lbl") and self._progress_lbl.winfo_exists():
            self._progress_lbl.config(text=msg)

    def _on_scan_done(self):
        if hasattr(self, "_anim_id"):
            self.after_cancel(self._anim_id)

        self._render_results(self._data)
        self._render_qr(self._data)
        self._set_status(
            f"Hoàn tất lúc {datetime.now().strftime('%H:%M:%S')}  •  "
            f"Serial: {self._data['system'].get('serial_number', 'N/A')}"
        )
        ts = self._data["scan_timestamp"][:19].replace("T", " ")
        self._lbl_time.config(text=ts)
        self._btn_rescan.config(state="normal")

    # ── Render kết quả ───────────────────────────────────────────────────────

    def _render_results(self, data):
        for w in self._left.winfo_children():
            w.destroy()

        canvas = tk.Canvas(self._left, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self._left, orient="vertical", command=canvas.yview)
        frame  = tk.Frame(canvas, bg=BG)

        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        s = data["system"]
        cpu = data["cpu"]
        ram = data["ram"]
        batt = data["battery"]
        disks = data["storage"]

        # ── Hệ thống ──
        self._section(frame, "💻  THÔNG TIN MÁY")
        self._row(frame, "Hãng",   s.get("manufacturer", "—"))
        self._row(frame, "Model",  s.get("model", "—"), bold=True)
        self._row(frame, "Serial", s.get("serial_number", "—"),
                  mono=True, accent=True)
        self._row(frame, "BIOS",   s.get("bios_version", "—"), dim=True)
        self._row(frame, "OS",     s.get("os", "—") + " " + s.get("os_version", "")[:40],
                  dim=True)

        # ── CPU ──
        self._section(frame, "🔲  CPU")
        self._row(frame, "Tên", cpu.get("name", "—"), bold=True)
        cores_str = (f"{cpu.get('physical_cores', '?')} lõi vật lý  /  "
                     f"{cpu.get('logical_cores', '?')} luồng  •  "
                     f"{cpu.get('max_freq_ghz', '?')} GHz")
        self._row(frame, "Cores", cores_str)

        # ── RAM ──
        self._section(frame, "📦  RAM")
        self._row(frame, "Tổng", f"{ram.get('total_gb', '?')} GB", bold=True)
        for i, slot in enumerate(ram.get("slots", []), 1):
            val = (f"{slot['capacity_gb']} GB  {slot['type']}  "
                   f"{slot['speed_mhz']} MHz  ({slot['manufacturer']})")
            self._row(frame, f"Khe {i}", val)

        # ── Ổ cứng ──
        self._section(frame, "💾  Ổ CỨNG")
        if disks:
            for disk in disks:
                val = f"{disk['size_gb']} GB  •  {disk['interface']}"
                self._row(frame, disk["name"], val)
        else:
            self._row(frame, "—", "Không phát hiện ổ cứng", dim=True)

        # ── Pin ──
        self._section(frame, "🔋  PIN")
        if batt.get("present"):
            health = batt.get("health_percent")
            if health is not None:
                color = ACCENT2 if health >= 80 else (WARN if health >= 60 else DANGER)
                icon  = "●" if health >= 80 else ("●" if health >= 60 else "●")
                self._row(frame, "Sức khỏe", f"{health}%", color=color, bold=True)
            if batt.get("design_capacity_mwh"):
                self._row(frame, "Dung lượng TK",
                           f"{batt['design_capacity_mwh']:,} mWh")
            if batt.get("full_charge_capacity_mwh"):
                self._row(frame, "Hiện tại",
                           f"{batt['full_charge_capacity_mwh']:,} mWh")
            if batt.get("cycle_count"):
                c = batt["cycle_count"]
                c_color = ACCENT2 if c < 300 else (WARN if c < 600 else DANGER)
                self._row(frame, "Số lần sạc", f"{c} lần", color=c_color)
        else:
            self._row(frame, "—", "Không có pin / pin đã tháo", dim=True)

    def _section(self, parent, title):
        """Header mỗi nhóm thông tin."""
        frm = tk.Frame(parent, bg=BG, pady=4)
        frm.pack(fill="x", padx=4, pady=(12, 2))
        tk.Label(frm, text=title, font=FONT_HEAD,
                 fg=ACCENT, bg=BG).pack(side="left")
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=4)

    def _row(self, parent, label, value,
             bold=False, mono=False, dim=False, accent=False, color=None):
        """Một dòng key-value."""
        row = tk.Frame(parent, bg=CARD, pady=5)
        row.pack(fill="x", padx=4, pady=1)

        lbl_font = FONT_BODY
        val_font = FONT_MONO if mono else (FONT_HEAD if bold else FONT_BODY)
        val_fg = (color if color else
                  (ACCENT if accent else (TEXT_DIM if dim else TEXT)))

        tk.Label(row, text=label, font=lbl_font, fg=TEXT_DIM, bg=CARD,
                 width=14, anchor="w").pack(side="left", padx=(10, 4))
        tk.Label(row, text=value, font=val_font, fg=val_fg, bg=CARD,
                 anchor="w", wraplength=420, justify="left").pack(side="left", padx=(0, 8))

    # ── Render QR ────────────────────────────────────────────────────────────

    def _render_qr(self, data):
        for w in self._right.winfo_children():
            w.destroy()

        try:
            import qrcode
            from PIL import Image, ImageTk

            payload = {
                "v": 1,
                "ts": data["scan_timestamp"],
                "mfr": data["system"].get("manufacturer", ""),
                "mdl": data["system"].get("model", ""),
                "sn":  data["system"].get("serial_number", ""),
                "cpu": data["cpu"].get("name", ""),
                "cpu_cores": data["cpu"].get("physical_cores"),
                "cpu_ghz":   data["cpu"].get("max_freq_ghz"),
                "ram_gb":    data["ram"].get("total_gb"),
                "ram_slots": [
                    {"gb": s["capacity_gb"], "type": s["type"], "mhz": s["speed_mhz"]}
                    for s in data["ram"].get("slots", [])
                ],
                "disks": [
                    {"name": d["name"], "gb": d["size_gb"], "iface": d["interface"]}
                    for d in data["storage"]
                ],
                "batt_health":      data["battery"].get("health_percent"),
                "batt_cycles":      data["battery"].get("cycle_count"),
                "batt_design_mwh":  data["battery"].get("design_capacity_mwh"),
                "batt_full_mwh":    data["battery"].get("full_charge_capacity_mwh"),
            }

            json_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=7,
                border=2,
            )
            qr.add_data(json_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Resize QR vừa khung phải
            self._right.update_idletasks()
            rw = max(self._right.winfo_width() - 32, 280)
            rh = max(self._right.winfo_height() - 120, 280)
            size = min(rw, rh)

            pil_img = img.get_image().resize((size, size), Image.NEAREST)
            photo = ImageTk.PhotoImage(pil_img)
            self._qr_img = photo  # giữ reference tránh GC

            tk.Label(self._right, text="Quét để nhập vào App",
                     font=FONT_HEAD, fg=TEXT, bg=CARD).pack(pady=(16, 8))

            tk.Label(self._right, image=photo, bg=CARD).pack()

            sn = data["system"].get("serial_number", "")
            tk.Label(self._right, text=sn, font=FONT_MONO,
                     fg=ACCENT, bg=CARD).pack(pady=(8, 4))

            # Nút lưu QR
            tk.Button(
                self._right, text="💾  Lưu QR ra file",
                font=FONT_SMALL, bg=BORDER, fg=TEXT,
                activebackground=ACCENT, relief="flat",
                padx=10, pady=4, cursor="hand2",
                command=lambda: self._save_qr(img, sn)
            ).pack(pady=(4, 12))

        except Exception as e:
            tk.Label(self._right, text=f"Không thể tạo QR:\n{e}",
                     font=FONT_SMALL, fg=DANGER, bg=CARD,
                     wraplength=220, justify="center").place(
                relx=0.5, rely=0.5, anchor="center")

    def _save_qr(self, img, sn):
        path = os.path.join(
            tempfile.gettempdir(),
            f"o2o_qr_{sn or 'unknown'}_{datetime.now().strftime('%H%M%S')}.png"
        )
        img.save(path)
        self._set_status(f"Đã lưu QR: {path}")

        import subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
        except Exception:
            pass

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _set_status(self, msg):
        self._status.config(text=msg)


def main():
    app = ScannerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
