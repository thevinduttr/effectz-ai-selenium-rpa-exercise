from __future__ import annotations

import logging
from typing import Callable, Optional, TypeVar

from selenium.common.exceptions import TimeoutException

from src.core.runtime_context import ScreenshotManager

T = TypeVar("T")


class RetryRunner:
    """Retries a high-level process when Selenium times out.

    The exercise asks for correct waits instead of fixed sleeps. This class does not replace
    explicit waits; it only re-runs a business step if a live Shopify page times out.
    """

    def __init__(self, max_attempts: int, screenshots: Optional[ScreenshotManager] = None) -> None:
        if max_attempts < 1:
            raise ValueError("retry.max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self.screenshots = screenshots
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, process_name: str, action: Callable[[], T]) -> T:
        last_error: TimeoutException | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                self.logger.info("Starting process '%s' attempt %s/%s", process_name, attempt, self.max_attempts)
                result = action()
                self.logger.info("Completed process '%s' attempt %s/%s", process_name, attempt, self.max_attempts)
                return result
            except TimeoutException as exc:
                last_error = exc
                self.logger.warning("Timeout in process '%s' attempt %s/%s: %s", process_name, attempt, self.max_attempts, exc)
                if self.screenshots is not None:
                    self.screenshots.capture(f"timeout_{process_name}_attempt_{attempt}")
                if attempt == self.max_attempts:
                    break

        raise last_error or TimeoutException(f"Process timed out: {process_name}")
