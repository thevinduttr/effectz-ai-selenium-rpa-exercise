from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AddedProduct:
    keyword: str
    name: str
    size: str | None
    product_url: str
