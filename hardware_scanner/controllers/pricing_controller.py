"""
Controller: AI pricing via Gemini.
Calls gemini_pricer in a background thread, caches results.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

import gemini_pricer
from models.hardware import HardwareData
from models.checklist import GradeResult
from models.pricing import PricingResult


class PricingController:
    def __init__(self):
        self._cache: dict = {}   # cache_key → PricingResult
        self._running = False
        self._on_start: Optional[Callable] = None
        self._on_result: Optional[Callable] = None   # (PricingResult) → None

    def set_callbacks(
        self,
        on_start: Optional[Callable] = None,
        on_result: Optional[Callable] = None,
    ):
        self._on_start = on_start
        self._on_result = on_result

    def reset(self):
        self._running = False
        self._cache.clear()

    def request(
        self,
        hw: HardwareData,
        answers: dict,
        checklist: list,
        grade: GradeResult,
    ):
        if self._running:
            return
        key = self._cache_key(answers, grade)
        if key in self._cache:
            if self._on_result:
                self._on_result(self._cache[key])
            return

        self._running = True
        if self._on_start:
            self._on_start()
        threading.Thread(
            target=self._worker,
            args=(hw, answers, checklist, grade, key),
            daemon=True,
        ).start()

    def retry(
        self,
        hw: HardwareData,
        answers: dict,
        checklist: list,
        grade: GradeResult,
    ):
        key = self._cache_key(answers, grade)
        self._cache.pop(key, None)
        self._running = False
        self.request(hw, answers, checklist, grade)

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(answers: dict, grade: GradeResult) -> str:
        return f"{sorted(answers.items())}|{grade.grade}|{grade.score}"

    def _worker(
        self,
        hw: HardwareData,
        answers: dict,
        checklist: list,
        grade: GradeResult,
        key: str,
    ):
        try:
            raw = gemini_pricer.get_price_estimate(
                hw.to_raw(),
                answers,
                [item.to_dict() for item in checklist],
                grade.grade,
                grade.score,
            )
            data = gemini_pricer.parse_result(raw)
            result = PricingResult.from_parsed(data, raw)
        except Exception as e:
            result = PricingResult.from_error(str(e))
        finally:
            self._cache[key] = result
            self._running = False
            if self._on_result:
                self._on_result(result)
