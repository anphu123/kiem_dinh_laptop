"""
Model: Checklist data structures + grading logic.
Pure data + business logic — no UI dependency.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChecklistOption:
    label: str
    score: int
    red_flag: bool = False


@dataclass
class ChecklistItem:
    id: str
    icon: str
    category: str
    question: str
    options: list  # list[ChecklistOption]

    def to_dict(self) -> dict:
        """Serialize to dict for gemini_pricer compatibility."""
        return {
            "id": self.id,
            "icon": self.icon,
            "category": self.category,
            "question": self.question,
            "options": [
                {"label": o.label, "score": o.score, "red_flag": o.red_flag}
                for o in self.options
            ],
        }


@dataclass
class GradeResult:
    grade: str
    score: int
    color: str
    description: str
    red_flags: list = field(default_factory=list)  # list[str]

    @property
    def is_rejected(self) -> bool:
        return self.grade == "REJECT"


# ── Defaults (fallback khi không có checklist.json) ────────────────────────────

_DEFAULT_GRADING = [
    (0,   2,   "A", "#00D4AA", "Máy tốt — Thu mua / bán ra giá cao"),
    (3,   5,   "B", "#4F8EF7", "Máy khá — Giá trung bình"),
    (6,   9,   "C", "#F5A623", "Máy trung bình — Giảm giá"),
    (10, 999,  "D", "#E74C3C", "Máy yếu — Giảm sâu / linh kiện"),
]

_DEFAULT_CHECKLIST_RAW = [
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
            {"label": "Nguyên vẹn",           "score": 0},
            {"label": "Trầy nhẹ",             "score": 1},
            {"label": "Móp / nứt nhẹ",        "score": 3},
            {"label": "Vỡ / biến dạng nặng", "score": 7},
        ],
    },
    {
        "id": "keyboard", "icon": "⌨", "category": "BÀN PHÍM",
        "question": "Tình trạng bàn phím?",
        "options": [
            {"label": "Đầy đủ, hoạt động tốt",             "score": 0},
            {"label": "Mòn phím / bẩn nhẹ",                "score": 1},
            {"label": "Mất hoặc liệt 1-2 phím",            "score": 3},
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
            {"label": "Tất cả hoạt động", "score": 0},
            {"label": "Hỏng 1 cổng phụ",  "score": 1},
            {"label": "Hỏng 2+ cổng",     "score": 3},
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


# ── Loaders ────────────────────────────────────────────────────────────────────

def _parse_raw(raw_list: list) -> list:
    """Convert list of dicts to list[ChecklistItem]."""
    items = []
    for item in raw_list:
        items.append(ChecklistItem(
            id=item["id"],
            icon=item["icon"],
            category=item["category"],
            question=item["question"],
            options=[
                ChecklistOption(
                    label=o["label"],
                    score=o["score"],
                    red_flag=o.get("red_flag", False),
                )
                for o in item["options"]
            ],
        ))
    return items


def load_checklist() -> tuple:
    """
    Load checklist + grading from checklist.json (next to the exe / project root).
    Returns (list[ChecklistItem], list[tuple])
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        # models/ is one level below project root
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    json_path = os.path.join(base, "checklist.json")
    if os.path.isfile(json_path):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            raw_cl = data.get("checklist")
            raw_gr = data.get("grading")
            checklist = _parse_raw(raw_cl) if raw_cl else _parse_raw(_DEFAULT_CHECKLIST_RAW)
            grading = (
                [(g["min"], g["max"], g["grade"], g["color"], g["desc"]) for g in raw_gr]
                if raw_gr else _DEFAULT_GRADING
            )
            return checklist, grading
        except Exception as e:
            print(f"[Warning] checklist.json bị lỗi, dùng default: {e}")
    return _parse_raw(_DEFAULT_CHECKLIST_RAW), _DEFAULT_GRADING


# ── Business logic ─────────────────────────────────────────────────────────────

def calc_grade(answers: dict, checklist: list, grading: list) -> GradeResult:
    """
    answers: {question_id: option_index}
    Returns GradeResult.
    """
    total = 0
    red_flags = []

    for item in checklist:
        idx = answers.get(item.id)
        if idx is None or idx >= len(item.options):
            continue
        opt = item.options[idx]
        if opt.red_flag:
            red_flags.append(f"{item.icon} {item.category}: {opt.label}")
        else:
            total += opt.score

    if red_flags:
        return GradeResult("REJECT", total, "#E74C3C",
                           "Có lỗi nghiêm trọng — Từ chối", red_flags)

    for lo, hi, grade, color, desc in grading:
        if lo <= total <= hi:
            return GradeResult(grade, total, color, desc)

    return GradeResult("D", total, "#E74C3C", "Máy yếu — Giảm sâu / linh kiện")
