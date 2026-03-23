"""
Controller: Checklist state management.
Tracks answers, computes grade, fires on_change callback.
"""
from __future__ import annotations

from typing import Callable, Optional

from models.checklist import ChecklistItem, GradeResult, load_checklist, calc_grade


class ChecklistController:
    def __init__(self):
        self._checklist, self._grading = load_checklist()
        self._answers: dict = {}  # {question_id: option_index}
        self._on_change: Optional[Callable] = None

    def set_on_change(self, callback: Callable):
        """callback(answers: dict, grade: Optional[GradeResult])"""
        self._on_change = callback

    # ── Read-only properties ───────────────────────────────────────────────────

    @property
    def checklist(self) -> list:
        return self._checklist

    @property
    def answers(self) -> dict:
        return dict(self._answers)

    @property
    def answered_count(self) -> int:
        return len(self._answers)

    @property
    def total_count(self) -> int:
        return len(self._checklist)

    @property
    def is_complete(self) -> bool:
        return self.answered_count == self.total_count

    # ── Mutations ──────────────────────────────────────────────────────────────

    def answer(self, question_id: str, option_index: int):
        self._answers[question_id] = option_index
        self._notify()

    def sync_from_visual(self, visual: dict):
        """
        Nhận dict {qid: idx} từ visual state của tất cả RadioGroups.
        Ghi đè answers và notify một lần — tránh mất on_change.
        """
        self._answers = {k: v for k, v in visual.items()}
        self._notify()

    def reset(self):
        self._answers = {}
        self._notify()

    # ── Queries ───────────────────────────────────────────────────────────────

    def current_grade(self) -> Optional[GradeResult]:
        if not self._answers:
            return None
        return calc_grade(self._answers, self._checklist, self._grading)

    def answers_as_labels(self) -> dict:
        """Return {question_id: option_label} for QR payload."""
        cl_map = {item.id: item for item in self._checklist}
        return {
            qid: cl_map[qid].options[idx].label
            for qid, idx in self._answers.items()
            if qid in cl_map
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _notify(self):
        if self._on_change:
            self._on_change(self._answers, self.current_grade())
