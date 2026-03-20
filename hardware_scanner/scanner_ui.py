"""
O2O Laptop Inspection - Hardware Scanner UI
Tab 1: Cấu hình phần cứng (auto-scan)
Tab 2: Checklist kiểm định ngoại quan (trắc nghiệm)
Panel phải: Grade + QR Code
"""

import tkinter as tk
from tkinter import ttk
import threading
import json
import os
import tempfile
import platform
from datetime import datetime

import scanner
import gemini_pricer

# ── Màu sắc ─────────────────────────────────────────────────────────────────
BG       = "#0F1117"
CARD     = "#1A1D27"
CARD2    = "#222536"
BORDER   = "#2A2D3E"
ACCENT   = "#4F8EF7"
GREEN    = "#00D4AA"
YELLOW   = "#F5A623"
RED      = "#E74C3C"
PURPLE   = "#9B59B6"
TEXT     = "#E8EAED"
DIM      = "#6B7280"
WHITE    = "#FFFFFF"

FT = ("Segoe UI", 20, "bold")
FH = ("Segoe UI", 11, "bold")
FB = ("Segoe UI", 10)
FM = ("Consolas", 10)
FS = ("Segoe UI", 9)
FBG = ("Segoe UI", 42, "bold")

# ── Bộ câu hỏi kiểm định ─────────────────────────────────────────────────────
CHECKLIST = [
    {
        "id": "power", "icon": "⚡", "category": "NGUỒN & KHỞI ĐỘNG",
        "question": "Máy có khởi động được không?",
        "options": [
            {"label": "Khởi động bình thường",          "score": 0},
            {"label": "Khởi động chậm / lỗi phần mềm", "score": 2},
            {"label": "Chết nguồn hoàn toàn",           "score": 0, "red_flag": True},
        ],
    },
    {
        "id": "bios", "icon": "🔒", "category": "BIOS / BITLOCKER",
        "question": "Tình trạng khóa BIOS / BitLocker?",
        "options": [
            {"label": "Không khóa",                          "score": 0},
            {"label": "Khóa BitLocker (có thể mở được)",     "score": 0, "red_flag": True},
            {"label": "Khóa BIOS (không tháo được)",         "score": 0, "red_flag": True},
        ],
    },
    {
        "id": "screen", "icon": "🖥", "category": "MÀN HÌNH",
        "question": "Tình trạng màn hình?",
        "options": [
            {"label": "Hoàn hảo, không tì vết",              "score": 0},
            {"label": "Trầy nhẹ, không ảnh hưởng hiển thị", "score": 1},
            {"label": "Trầy nhiều / điểm chết pixel",        "score": 4},
            {"label": "Chảy mực / nứt vỡ",                   "score": 0, "red_flag": True},
        ],
    },
    {
        "id": "chassis", "icon": "📦", "category": "VỎ MÁY",
        "question": "Tình trạng vỏ máy (nắp, đáy, viền)?",
        "options": [
            {"label": "Nguyên vẹn",            "score": 0},
            {"label": "Trầy nhẹ",              "score": 1},
            {"label": "Móp / nứt nhẹ",         "score": 3},
            {"label": "Vỡ / biến dạng nặng",  "score": 7},
        ],
    },
    {
        "id": "keyboard", "icon": "⌨", "category": "BÀN PHÍM",
        "question": "Tình trạng bàn phím?",
        "options": [
            {"label": "Đầy đủ, hoạt động tốt",          "score": 0},
            {"label": "Mòn phím / bẩn nhẹ",             "score": 1},
            {"label": "Mất hoặc liệt 1-2 phím",         "score": 3},
            {"label": "Liệt nhiều phím / không dùng được", "score": 7},
        ],
    },
    {
        "id": "hinge", "icon": "🔩", "category": "BẢN LỀ",
        "question": "Tình trạng bản lề màn hình?",
        "options": [
            {"label": "Chắc chắn, mở đóng mượt", "score": 0},
            {"label": "Hơi lỏng",                "score": 1},
            {"label": "Lỏng nhiều / kêu",        "score": 3},
            {"label": "Gãy / vỡ bản lề",         "score": 7},
        ],
    },
    {
        "id": "touchpad", "icon": "🖱", "category": "TOUCHPAD",
        "question": "Tình trạng touchpad?",
        "options": [
            {"label": "Nhạy, hoạt động tốt",  "score": 0},
            {"label": "Giật / kém nhạy nhẹ",  "score": 2},
            {"label": "Không hoạt động",       "score": 4},
        ],
    },
    {
        "id": "ports", "icon": "🔌", "category": "CỔNG KẾT NỐI",
        "question": "Tình trạng cổng USB / HDMI / jack?",
        "options": [
            {"label": "Tất cả hoạt động",       "score": 0},
            {"label": "Hỏng 1 cổng phụ",        "score": 1},
            {"label": "Hỏng 2+ cổng",           "score": 3},
        ],
    },
    {
        "id": "camera", "icon": "📷", "category": "CAMERA & MIC",
        "question": "Tình trạng camera tích hợp?",
        "options": [
            {"label": "Hoạt động tốt",   "score": 0},
            {"label": "Chất lượng kém",  "score": 1},
            {"label": "Không hoạt động", "score": 2},
        ],
    },
    {
        "id": "speaker", "icon": "🔊", "category": "LOA & ÂM THANH",
        "question": "Tình trạng loa?",
        "options": [
            {"label": "Âm thanh to, rõ",    "score": 0},
            {"label": "Rè / méo tiếng nhẹ", "score": 1},
            {"label": "Không có âm thanh",  "score": 2},
        ],
    },
]

GRADE_TABLE = [
    (0,  2,  "A",      GREEN,  "Máy tốt — Thu mua / bán ra giá cao"),
    (3,  5,  "B",      ACCENT, "Máy khá — Giá trung bình"),
    (6,  9,  "C",      YELLOW, "Máy trung bình — Giảm giá"),
    (10, 99, "D",      RED,    "Máy yếu — Giảm sâu / linh kiện"),
]


def calc_grade(answers: dict):
    """Tính điểm và xếp hạng từ dict {question_id: option_index}."""
    total = 0
    red_flags = []

    for item in CHECKLIST:
        qid = item["id"]
        idx = answers.get(qid)
        if idx is None:
            continue
        opt = item["options"][idx]
        if opt.get("red_flag"):
            red_flags.append(f'{item["icon"]} {item["category"]}: {opt["label"]}')
        else:
            total += opt["score"]

    if red_flags:
        return "REJECT", total, RED, "Có lỗi nghiêm trọng — Từ chối", red_flags

    for lo, hi, grade, color, desc in GRADE_TABLE:
        if lo <= total <= hi:
            return grade, total, color, desc, []

    return "D", total, RED, "Máy yếu — Giảm sâu / linh kiện", []


# ─────────────────────────────────────────────────────────────────────────────

class ScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("O2O Laptop Inspection")
        self.configure(bg=BG)
        self.resizable(True, True)

        w, h = 1160, 740
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(960, 640)

        self._data     = None
        self._qr_img   = None
        self._answers  = {}          # {qid: option_idx}
        self._vars     = {}          # {qid: IntVar}

        self._build_header()
        self._build_body()
        self._build_footer()

        self.after(200, self._start_scan)

    # ── Header ───────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=CARD, pady=12)
        hdr.pack(fill="x")

        tk.Label(hdr, text="O2O  LAPTOP  INSPECTION",
                 font=FT, fg=WHITE, bg=CARD).pack(side="left", padx=24)

        self._lbl_time = tk.Label(hdr, text="", font=FS, fg=DIM, bg=CARD)
        self._lbl_time.pack(side="right", padx=24)

        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

    # ── Body ─────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=10)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ── Trái: Notebook 2 tab ──
        nb_frame = tk.Frame(body, bg=BG)
        nb_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        nb_frame.rowconfigure(0, weight=1)
        nb_frame.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook",
                        background=BG, borderwidth=0, tabmargins=0)
        style.configure("Dark.TNotebook.Tab",
                        background=CARD, foreground=DIM,
                        padding=[16, 7], font=FH, borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", CARD2)],
                  foreground=[("selected", WHITE)])

        self._nb = ttk.Notebook(nb_frame, style="Dark.TNotebook")
        self._nb.grid(row=0, column=0, sticky="nsew")

        # Tab 1: Cấu hình
        self._tab_hw = tk.Frame(self._nb, bg=BG)
        self._nb.add(self._tab_hw, text="  📊  CẤU HÌNH  ")

        # Tab 2: Checklist
        self._tab_cl = tk.Frame(self._nb, bg=BG)
        self._nb.add(self._tab_cl, text="  ✅  KIỂM ĐỊNH  ")

        # ── Phải: Grade + QR ──
        self._right = tk.Frame(body, bg=CARD,
                                highlightthickness=1,
                                highlightbackground=BORDER)
        self._right.grid(row=0, column=1, sticky="nsew")

        self._build_loading_state()
        self._build_checklist()

    # ── Footer ───────────────────────────────────────────────────────────────

    def _build_footer(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        foot = tk.Frame(self, bg=CARD, pady=7)
        foot.pack(fill="x")

        self._status = tk.Label(foot, text="Đang khởi động...",
                                 font=FS, fg=DIM, bg=CARD)
        self._status.pack(side="left", padx=20)

        self._btn_rescan = tk.Button(
            foot, text="⟳  Quét lại", font=FS,
            bg=ACCENT, fg=WHITE, activebackground="#3A6ED8",
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self._start_scan, state="disabled"
        )
        self._btn_rescan.pack(side="right", padx=16)

    # ── Loading ───────────────────────────────────────────────────────────────

    def _build_loading_state(self):
        for w in self._tab_hw.winfo_children():
            w.destroy()
        for w in self._right.winfo_children():
            w.destroy()

        center = tk.Frame(self._tab_hw, bg=BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        self._spinner_label = tk.Label(center, text="◐", font=FBG, fg=ACCENT, bg=BG)
        self._spinner_label.pack()
        tk.Label(center, text="Đang quét cấu hình máy...",
                 font=FH, fg=TEXT, bg=BG).pack(pady=(12, 0))
        self._progress_lbl = tk.Label(center, text="", font=FS, fg=DIM, bg=BG)
        self._progress_lbl.pack(pady=(4, 0))
        self._animate_spinner()

        tk.Label(self._right, text="QR", font=("Segoe UI", 48, "bold"),
                 fg=BORDER, bg=CARD).place(relx=0.5, rely=0.5, anchor="center")

    def _animate_spinner(self, step=0):
        frames = ["◐", "◓", "◑", "◒"]
        if hasattr(self, "_spinner_label") and self._spinner_label.winfo_exists():
            self._spinner_label.config(text=frames[step % 4])
            self._anim_id = self.after(180, self._animate_spinner, step + 1)

    # ── Scan ─────────────────────────────────────────────────────────────────

    def _start_scan(self):
        self._btn_rescan.config(state="disabled")
        self._build_loading_state()
        self._status.config(text="Đang thu thập dữ liệu...")
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        steps = [
            ("Thông tin hệ thống...", "system",  scanner.get_system_info),
            ("CPU...",               "cpu",     scanner.get_cpu_info),
            ("RAM...",               "ram",     scanner.get_ram_info),
            ("Ổ cứng...",            "storage", scanner.get_storage_info),
            ("Pin...",               "battery", scanner.get_battery_info),
            ("Card đồ họa...",       "gpu",     scanner.get_gpu_info),
            ("Màn hình...",          "display", scanner.get_display_info),
        ]
        result = {"scan_timestamp": datetime.now().isoformat()}
        for msg, key, fn in steps:
            self.after(0, lambda m=msg: self._progress_lbl.config(text=m)
                       if self._progress_lbl.winfo_exists() else None)
            result[key] = fn()

        self._data = result
        self.after(0, self._on_scan_done)

    def _on_scan_done(self):
        if hasattr(self, "_anim_id"):
            self.after_cancel(self._anim_id)
        self._render_hw(self._data)
        self._refresh_right()
        ts = self._data["scan_timestamp"][:19].replace("T", " ")
        self._lbl_time.config(text=ts)
        sn = self._data["system"].get("serial_number", "N/A")
        self._status.config(
            text=f"Hoàn tất lúc {datetime.now().strftime('%H:%M:%S')}  •  Serial: {sn}")
        self._btn_rescan.config(state="normal")

    # ── Tab 1: Phần cứng ─────────────────────────────────────────────────────

    def _render_hw(self, data):
        for w in self._tab_hw.winfo_children():
            w.destroy()

        canvas = tk.Canvas(self._tab_hw, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self._tab_hw, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=BG)
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        s    = data["system"]
        cpu  = data["cpu"]
        ram  = data["ram"]
        batt = data["battery"]
        disks = data["storage"]
        gpus  = data.get("gpu", [])

        self._sec(frame, "💻  THÔNG TIN MÁY")
        self._row(frame, "Hãng",   s.get("manufacturer", "—"))
        self._row(frame, "Model",  s.get("model", "—"),           bold=True)
        self._row(frame, "Serial", s.get("serial_number", "—"),   mono=True, color=ACCENT)
        self._row(frame, "BIOS",   s.get("bios_version", "—"),    dim=True)
        self._row(frame, "OS",
                  s.get("os", "—") + "  " + s.get("os_version", "")[:40], dim=True)

        self._sec(frame, "🔲  CPU")
        self._row(frame, "Tên", cpu.get("name", "—"), bold=True)
        self._row(frame, "Cores",
                  f"{cpu.get('physical_cores','?')} lõi vật lý  /  "
                  f"{cpu.get('logical_cores','?')} luồng  •  "
                  f"{cpu.get('max_freq_ghz','?')} GHz")

        self._sec(frame, "📦  RAM")
        self._row(frame, "Tổng", f"{ram.get('total_gb','?')} GB", bold=True)
        for i, sl in enumerate(ram.get("slots", []), 1):
            self._row(frame, f"Khe {i}",
                      f"{sl['capacity_gb']} GB  {sl['type']}  "
                      f"{sl['speed_mhz']} MHz  ({sl['manufacturer']})")

        self._sec(frame, "💾  Ổ CỨNG")
        if disks:
            for d in disks:
                self._row(frame, d["name"], f"{d['size_gb']} GB  •  {d['interface']}")
        else:
            self._row(frame, "—", "Không phát hiện ổ cứng", dim=True)

        self._sec(frame, "🎮  CARD ĐỒ HỌA")
        if gpus:
            for g in gpus:
                parts = []
                if g.get("vram_gb"):   parts.append(f"{g['vram_gb']} GB VRAM")
                elif g.get("vram_mb"): parts.append(f"{g['vram_mb']} MB VRAM")
                if g.get("type"):      parts.append(g["type"])
                if g.get("resolution"): parts.append(g["resolution"])
                c = ACCENT if g.get("type") == "Dedicated" else None
                self._row(frame, g.get("name","?"),
                          "  •  ".join(parts) or "—", color=c)
        else:
            self._row(frame, "—", "Không phát hiện GPU", dim=True)

        self._sec(frame, "🔋  PIN")
        if batt.get("present"):
            h = batt.get("health_percent")
            if h is not None:
                hc = GREEN if h >= 80 else (YELLOW if h >= 60 else RED)
                self._row(frame, "Sức khỏe", f"{h}%", bold=True, color=hc)
            if batt.get("design_capacity_mwh"):
                self._row(frame, "Dung lượng TK",
                           f"{batt['design_capacity_mwh']:,} mWh")
            if batt.get("full_charge_capacity_mwh"):
                self._row(frame, "Hiện tại",
                           f"{batt['full_charge_capacity_mwh']:,} mWh")
            if batt.get("cycle_count"):
                cc = batt["cycle_count"]
                self._row(frame, "Số lần sạc", f"{cc} lần",
                           color=GREEN if cc < 300 else (YELLOW if cc < 600 else RED))
        else:
            self._row(frame, "—", "Không có pin / pin đã tháo", dim=True)

    def _sec(self, p, title):
        f = tk.Frame(p, bg=BG, pady=3)
        f.pack(fill="x", padx=4, pady=(10, 2))
        tk.Label(f, text=title, font=FH, fg=ACCENT, bg=BG).pack(side="left")
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=4)

    def _row(self, p, label, value, bold=False, mono=False,
             dim=False, color=None):
        row = tk.Frame(p, bg=CARD, pady=5)
        row.pack(fill="x", padx=4, pady=1)
        fg  = color or (DIM if dim else TEXT)
        vf  = FM if mono else (FH if bold else FB)
        tk.Label(row, text=label, font=FB, fg=DIM, bg=CARD,
                 width=14, anchor="w").pack(side="left", padx=(10, 4))
        tk.Label(row, text=value, font=vf, fg=fg, bg=CARD,
                 anchor="w", wraplength=400, justify="left").pack(
            side="left", padx=(0, 8))

    # ── Tab 2: Checklist ──────────────────────────────────────────────────────

    def _build_checklist(self):
        for w in self._tab_cl.winfo_children():
            w.destroy()
        self._vars = {}

        canvas = tk.Canvas(self._tab_cl, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self._tab_cl, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=BG)
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # style radio buttons
        style = ttk.Style()
        style.configure("CL.TRadiobutton",
                        background=CARD2, foreground=TEXT,
                        font=FB, focuscolor=CARD2)
        style.map("CL.TRadiobutton",
                  background=[("active", CARD2)],
                  foreground=[("active", WHITE)])

        for item in CHECKLIST:
            qid = item["id"]
            var = tk.IntVar(value=-1)
            self._vars[qid] = var

            # Card câu hỏi
            card = tk.Frame(frame, bg=CARD2, pady=10,
                            highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill="x", padx=6, pady=5)

            # Tiêu đề câu hỏi
            hdr = tk.Frame(card, bg=CARD2)
            hdr.pack(fill="x", padx=12, pady=(0, 6))
            tk.Label(hdr, text=item["icon"], font=("Segoe UI", 14),
                     fg=ACCENT, bg=CARD2).pack(side="left")
            tk.Label(hdr, text=f"  {item['category']}",
                     font=FH, fg=ACCENT, bg=CARD2).pack(side="left")

            tk.Label(card, text=item["question"],
                     font=FB, fg=TEXT, bg=CARD2,
                     anchor="w").pack(fill="x", padx=14, pady=(0, 8))

            # Các lựa chọn
            for i, opt in enumerate(item["options"]):
                is_red = opt.get("red_flag", False)
                score  = opt["score"]

                row = tk.Frame(card, bg=CARD2)
                row.pack(fill="x", padx=14, pady=2)

                rb = ttk.Radiobutton(
                    row, text=opt["label"],
                    variable=var, value=i,
                    style="CL.TRadiobutton",
                    command=self._on_answer_change,
                )
                rb.pack(side="left")

                # Badge điểm / red flag
                if is_red:
                    badge_txt = "🚩 REJECT"
                    badge_clr = RED
                elif score == 0:
                    badge_txt = "0 đ"
                    badge_clr = GREEN
                elif score <= 2:
                    badge_txt = f"+{score} đ"
                    badge_clr = YELLOW
                else:
                    badge_txt = f"+{score} đ"
                    badge_clr = RED

                tk.Label(row, text=badge_txt, font=FS,
                         fg=badge_clr, bg=CARD2).pack(side="left", padx=(8, 0))

        # Nút reset
        btn_frame = tk.Frame(frame, bg=BG)
        btn_frame.pack(fill="x", padx=6, pady=(4, 10))
        tk.Button(btn_frame, text="↺  Reset câu trả lời",
                  font=FS, bg=BORDER, fg=DIM,
                  activebackground=CARD2, relief="flat",
                  padx=12, pady=4, cursor="hand2",
                  command=self._reset_checklist).pack(side="right")

    def _on_answer_change(self):
        self._answers = {
            qid: var.get()
            for qid, var in self._vars.items()
            if var.get() >= 0
        }
        self._refresh_right()

    def _reset_checklist(self):
        for var in self._vars.values():
            var.set(-1)
        self._answers = {}
        self._refresh_right()

    # ── Panel phải: Grade + QR ────────────────────────────────────────────────

    def _refresh_right(self):
        """Vẽ lại panel phải dựa trên answers hiện tại."""
        for w in self._right.winfo_children():
            w.destroy()

        answered = len(self._answers)
        total_q  = len(CHECKLIST)

        if answered == 0:
            # Chưa có câu trả lời nào
            self._render_qr_only()
            return

        grade, score, color, desc, flags = calc_grade(self._answers)

        # ── Grade badge ──
        badge = tk.Frame(self._right, bg=CARD, pady=16)
        badge.pack(fill="x")

        g_lbl = tk.Label(badge, text=grade,
                          font=("Segoe UI", 52, "bold"),
                          fg=color, bg=CARD)
        g_lbl.pack()

        tk.Label(badge, text=desc, font=FH, fg=color, bg=CARD,
                 wraplength=260, justify="center").pack(pady=(4, 0))

        # Tổng điểm
        if grade != "REJECT":
            tk.Label(badge, text=f"Tổng điểm phạt: {score}",
                     font=FS, fg=DIM, bg=CARD).pack(pady=(4, 0))

        # Progress câu hỏi
        prog_txt = f"{answered}/{total_q} câu đã trả lời"
        prog_clr = GREEN if answered == total_q else YELLOW
        tk.Label(badge, text=prog_txt, font=FS, fg=prog_clr, bg=CARD).pack()

        # ── Red flags ──
        if flags:
            flag_frame = tk.Frame(self._right, bg=RED, pady=8)
            flag_frame.pack(fill="x", padx=0)
            tk.Label(flag_frame, text="🚩  LỖI NGHIÊM TRỌNG",
                     font=FH, fg=WHITE, bg=RED).pack()
            for f in flags:
                tk.Label(flag_frame, text=f, font=FS,
                          fg=WHITE, bg=RED).pack()

        # ── Nút Định giá AI ──
        ai_btn = tk.Button(
            self._right, text="🤖  Định giá bằng AI",
            font=FH, bg="#7C3AED", fg=WHITE,
            activebackground="#6D28D9", relief="flat",
            padx=16, pady=8, cursor="hand2",
            command=lambda g=grade, sc=score: self._run_ai_pricing(g, sc)
        )
        ai_btn.pack(fill="x", padx=16, pady=(8, 4))

        tk.Frame(self._right, bg=BORDER, height=1).pack(fill="x", pady=(4, 0))

        # ── QR Code ──
        self._render_qr_section(grade=grade, score=score)

    def _run_ai_pricing(self, grade, score):
        """Gọi Gemini API trong background thread, hiện popup kết quả."""
        win = tk.Toplevel(self)
        win.title("🤖 Định giá AI")
        win.configure(bg=BG)
        win.geometry("620x500")
        win.resizable(True, True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"620x500+{(sw-620)//2}+{(sh-500)//2}")

        # Header
        hdr = tk.Frame(win, bg="#7C3AED", pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🤖  Gemini AI — Phân tích & Định giá",
                 font=FH, fg=WHITE, bg="#7C3AED").pack()

        # Body scroll
        canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        self._ai_frame = tk.Frame(canvas, bg=BG)
        self._ai_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._ai_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # Loading state
        self._ai_status = tk.Label(
            self._ai_frame, text="⏳  Đang kết nối Gemini AI...",
            font=FH, fg=YELLOW, bg=BG, pady=30)
        self._ai_status.pack()
        self._ai_win = win

        def worker():
            try:
                result = gemini_pricer.get_price_estimate(
                    self._data, self._answers, CHECKLIST, grade, score)
                self.after(0, lambda: self._show_ai_result(result, error=False))
            except Exception as e:
                self.after(0, lambda err=e: self._show_ai_result(str(err), error=True))

        threading.Thread(target=worker, daemon=True).start()

    def _show_ai_result(self, text, error=False):
        for w in self._ai_frame.winfo_children():
            w.destroy()

        if error:
            tk.Label(self._ai_frame, text="❌  Lỗi kết nối AI",
                     font=FH, fg=RED, bg=BG, pady=12).pack()
            tk.Label(self._ai_frame, text=text, font=FS, fg=YELLOW, bg=BG,
                     wraplength=560, justify="left",
                     padx=20).pack(anchor="w")
            return

        # Render từng dòng kết quả
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                tk.Frame(self._ai_frame, bg=BG, height=6).pack()
                continue

            # Dòng tiêu đề (bắt đầu bằng số. hoặc **)
            if (stripped[:2].rstrip(".").isdigit() or
                    stripped.startswith("**") or
                    stripped.startswith("##")):
                clean = stripped.lstrip("#").replace("**", "").strip()
                fg = ACCENT
                font = FH
            else:
                clean = stripped.lstrip("-•").strip()
                fg = TEXT
                font = FB

            tk.Label(self._ai_frame, text=clean, font=font, fg=fg,
                     bg=BG, anchor="w", wraplength=560,
                     justify="left", padx=20, pady=1).pack(fill="x")

        # Nút copy
        def copy_text():
            self.clipboard_clear()
            self.clipboard_append(text)
            self._status.config(text="Đã copy kết quả AI vào clipboard")

        tk.Button(self._ai_frame, text="📋  Copy kết quả",
                  font=FS, bg=BORDER, fg=TEXT,
                  activebackground=CARD2, relief="flat",
                  padx=12, pady=5, cursor="hand2",
                  command=copy_text).pack(pady=(12, 16))

    def _render_qr_only(self):
        """Chưa kiểm định — chỉ hiện QR cấu hình."""
        if self._data is None:
            tk.Label(self._right, text="QR", font=("Segoe UI", 48, "bold"),
                     fg=BORDER, bg=CARD).place(relx=0.5, rely=0.5, anchor="center")
            return

        tk.Label(self._right, text="Chưa kiểm định",
                 font=FH, fg=DIM, bg=CARD).pack(pady=(20, 4))
        tk.Label(self._right,
                 text="Chọn tab  ✅ KIỂM ĐỊNH\nđể trả lời câu hỏi ngoại quan",
                 font=FS, fg=DIM, bg=CARD,
                 justify="center").pack()
        tk.Frame(self._right, bg=BORDER, height=1).pack(fill="x", pady=10)
        self._render_qr_section()

    def _render_qr_section(self, grade=None, score=None):
        if self._data is None:
            return
        try:
            import qrcode
            from PIL import Image, ImageTk

            payload = {
                "v": 1,
                "ts": self._data["scan_timestamp"],
                "mfr": self._data["system"].get("manufacturer", ""),
                "mdl": self._data["system"].get("model", ""),
                "sn":  self._data["system"].get("serial_number", ""),
                "cpu": self._data["cpu"].get("name", ""),
                "cpu_cores": self._data["cpu"].get("physical_cores"),
                "cpu_ghz":   self._data["cpu"].get("max_freq_ghz"),
                "ram_gb":    self._data["ram"].get("total_gb"),
                "ram_slots": [
                    {"gb": s["capacity_gb"], "type": s["type"], "mhz": s["speed_mhz"]}
                    for s in self._data["ram"].get("slots", [])
                ],
                "disks": [
                    {"name": d["name"], "gb": d["size_gb"], "iface": d["interface"]}
                    for d in self._data["storage"]
                ],
                "batt_health":     self._data["battery"].get("health_percent"),
                "batt_cycles":     self._data["battery"].get("cycle_count"),
                "batt_design_mwh": self._data["battery"].get("design_capacity_mwh"),
                "batt_full_mwh":   self._data["battery"].get("full_charge_capacity_mwh"),
                "gpus": [
                    {"name": g.get("name",""), "vram_gb": g.get("vram_gb"),
                     "type": g.get("type","")}
                    for g in self._data.get("gpu", [])
                ],
                "grade": grade,
                "score": score,
                "checklist": {
                    qid: CHECKLIST[next(
                        i for i, c in enumerate(CHECKLIST) if c["id"] == qid
                    )]["options"][idx]["label"]
                    for qid, idx in self._answers.items()
                },
            }

            json_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

            qr = qrcode.QRCode(version=None,
                               error_correction=qrcode.constants.ERROR_CORRECT_M,
                               box_size=6, border=2)
            qr.add_data(json_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            self._right.update_idletasks()
            avail_h = max(self._right.winfo_height() - 260, 180)
            avail_w = max(self._right.winfo_width() - 24, 180)
            size = min(avail_w, avail_h)

            pil_img = img.get_image().resize((size, size), Image.NEAREST)
            photo = ImageTk.PhotoImage(pil_img)
            self._qr_img = photo

            tk.Label(self._right, text="Quét để nhập vào App",
                     font=FH, fg=TEXT, bg=CARD).pack(pady=(8, 4))
            tk.Label(self._right, image=photo, bg=CARD).pack()

            sn = self._data["system"].get("serial_number", "")
            tk.Label(self._right, text=sn, font=FM, fg=ACCENT, bg=CARD).pack(pady=(6, 2))

            tk.Button(self._right, text="💾  Lưu QR",
                      font=FS, bg=BORDER, fg=TEXT,
                      activebackground=ACCENT, relief="flat",
                      padx=10, pady=3, cursor="hand2",
                      command=lambda: self._save_qr(img, sn)).pack(pady=(2, 10))

        except Exception as e:
            tk.Label(self._right, text=f"QR lỗi:\n{e}",
                     font=FS, fg=RED, bg=CARD,
                     wraplength=220, justify="center").pack(pady=20)

    def _save_qr(self, img, sn):
        path = os.path.join(tempfile.gettempdir(),
                            f"o2o_qr_{sn or 'unknown'}_{datetime.now():%H%M%S}.png")
        img.save(path)
        self._status.config(text=f"Đã lưu QR: {path}")
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                import subprocess
                subprocess.run(["open", path])
        except Exception:
            pass


def main():
    app = ScannerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
