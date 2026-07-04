from __future__ import annotations

import argparse
import logging
import sys

from selenium.common.exceptions import WebDriverException

from src.core.config_loader import load_json_config
from src.core.driver_factory import create_driver
from src.core.result_printer import ResultPrinter
from src.core.runtime_context import ScreenshotManager, configure_logging, create_runtime_context
from src.flows.checkout_flow import CheckoutFlow
from src.flows.shopping_flow import ShoppingFlow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carnage Selenium practical exercise runner")
    parser.add_argument(
        "--task",
        choices=["A", "B", "BOTH", "task-a", "task-b", "all"],
        default="A",
        help="A/task-a = shopping only, BOTH/all = shopping + checkout. B/task-b also runs Task A first because checkout needs cart items.",
    )
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    return parser.parse_args()


def normalize_task(task: str) -> str:
    normalized_task = task.upper().replace("TASK-", "")
    if normalized_task == "ALL":
        return "BOTH"
    return normalized_task


def is_browser_closed_error(exc: Exception) -> bool:
    if not isinstance(exc, WebDriverException):
        return False

    message = str(exc).lower()
    closed_messages = (
        "invalid session id",
        "no such window",
        "target window already closed",
        "disconnected",
        "chrome not reachable",
        "web view not found",
    )
    return any(text in message for text in closed_messages)


def run_selected_task(task: str, app_config: dict, test_data: dict, context) -> int:
    logger = logging.getLogger("runner")
    driver = create_driver(app_config)
    screenshots = ScreenshotManager(driver, context)
    printer = ResultPrinter(screenshots=screenshots)

    try:
        ShoppingFlow(driver, app_config, test_data, screenshots=screenshots).run(printer)

        if task in {"B", "BOTH"}:
            CheckoutFlow(driver, app_config, test_data, screenshots=screenshots).run(printer)

        exit_code = printer.exit_code()
        logger.info("Run completed with exit_code=%s", exit_code)
        return exit_code
    finally:
        try:
            driver.quit()
        except WebDriverException:
            logger.info("Chrome was already closed.")


def main() -> int:
    args = parse_args()
    task = normalize_task(args.task)
    app_config = load_json_config("app_config.json")
    test_data = load_json_config("test_data.json")
    context = create_runtime_context(app_config)
    configure_logging(context)
    logger = logging.getLogger("runner")

    logger.info("Run ID: %s", context.run_id)
    logger.info("Log file: %s", context.log_file)
    logger.info("Screenshots directory: %s", context.screenshot_dir)
    logger.info("Selected task: %s", task)

    if args.headless:
        app_config.setdefault("browser", {})["headless"] = True

    restart_attempts = app_config.get("execution", {}).get("browser_restart_attempts", 1)
    for attempt in range(restart_attempts + 1):
        try:
            if attempt:
                logger.info("Restarting Chrome and running selected task again. Attempt %s of %s.", attempt + 1, restart_attempts + 1)

            exit_code = run_selected_task(task, app_config, test_data, context)
            logger.info("Log file available at: %s", context.log_file)
            logger.info("Screenshots available at: %s", context.screenshot_dir)
            return exit_code
        except Exception as exc:
            if is_browser_closed_error(exc) and attempt < restart_attempts:
                logger.warning("Chrome was closed or disconnected. Starting again...")
                continue

            logger.exception("Run failed with unexpected error: %s", exc)
            raise

    return 1


if __name__ == "__main__":
    sys.exit(main())
