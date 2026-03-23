"""
Model: AI pricing result.
Pure data — no UI dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PricingResult:
    buy_min: Optional[int] = None
    buy_max: Optional[int] = None
    sell_min: Optional[int] = None
    sell_max: Optional[int] = None
    summary: str = ""
    strengths: list = field(default_factory=list)   # list[str]
    weaknesses: list = field(default_factory=list)  # list[str]
    reasoning: str = ""
    raw: str = ""
    error: str = ""

    @classmethod
    def from_parsed(cls, data: dict, raw: str) -> "PricingResult":
        """Tạo PricingResult từ dict đã parse (do controller gọi parse_result trước)."""
        if set(data.keys()) == {"_raw"}:
            return cls(raw=raw)
        return cls(
            buy_min=data.get("buy_min"),
            buy_max=data.get("buy_max"),
            sell_min=data.get("sell_min"),
            sell_max=data.get("sell_max"),
            summary=data.get("summary", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            reasoning=data.get("reasoning", ""),
            raw=raw,
        )

    @classmethod
    def from_error(cls, error: str) -> "PricingResult":
        return cls(error=error)

    @property
    def has_prices(self) -> bool:
        return self.buy_min is not None

    @property
    def copy_text(self) -> str:
        if self.has_prices:
            buy_lo = f"{self.buy_min:,.0f}".replace(",", ".")
            buy_hi = f"{self.buy_max:,.0f}".replace(",", ".")
            sell_lo = f"{self.sell_min:,.0f}".replace(",", ".")
            sell_hi = f"{self.sell_max:,.0f}".replace(",", ".")
            return (
                f"{self.summary}\n"
                f"Thu mua: {buy_lo} – {buy_hi} đ\n"
                f"Bán ra:  {sell_lo} – {sell_hi} đ"
            )
        return self.raw
