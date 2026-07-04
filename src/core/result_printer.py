from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.core.runtime_context import ScreenshotManager


@dataclass
class ResultPrinter:
    screenshots: Optional[ScreenshotManager] = None
    failures: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def check(self, title: str, condition: bool, details: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        message = f"{status}: {title}"
        if details:
            message += f" - {details}"

        print(message)
        if condition:
            self.logger.info(message)
            return

        self.failures.append(message)
        self.logger.error(message)
        if self.screenshots is not None:
            self.screenshots.capture(f"failure_{title}")

    def exit_code(self) -> int:
        return 1 if self.failures else 0
