from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.config_loader import PROJECT_ROOT


@dataclass(frozen=True)
class RuntimeContext:
    run_id: str
    log_file: Path
    screenshot_dir: Path


def create_runtime_context(app_config: Dict[str, Any]) -> RuntimeContext:
    """Create a unique artifact location for one script execution."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_config = app_config.get("artifacts", {})

    logs_dir = PROJECT_ROOT / artifact_config.get("logs_dir", "logs")
    screenshots_root = PROJECT_ROOT / artifact_config.get("screenshots_dir", "screenshots")
    screenshot_dir = screenshots_root / run_id

    logs_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    return RuntimeContext(
        run_id=run_id,
        log_file=logs_dir / f"run_{run_id}.log",
        screenshot_dir=screenshot_dir,
    )


def configure_logging(context: RuntimeContext) -> None:
    """Write every run to its own log file and also show concise logs in the console."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(context.log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


class ScreenshotManager:
    def __init__(self, driver: WebDriver, context: RuntimeContext) -> None:
        self.driver = driver
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

    def capture(self, name: str) -> Path:
        safe_name = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in name).strip("_")
        path = self.context.screenshot_dir / f"{safe_name}.png"
        self.driver.save_screenshot(str(path))
        self.logger.info("Screenshot captured: %s", path)
        return path
