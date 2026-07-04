from __future__ import annotations


def cents_to_amount(cents: int | float | str | None) -> float:
    try:
        return round(int(cents or 0) / 100.0, 2)
    except (TypeError, ValueError):
        return 0.0


def lkr_label(amount: float) -> str:
    return f"LKR {amount:,.2f}"
