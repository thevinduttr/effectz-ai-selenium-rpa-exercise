from __future__ import annotations

import logging
from typing import Any, Dict

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.exceptions import CaptchaDetectedError
from src.core.result_printer import ResultPrinter
from src.core.retry import RetryRunner
from src.core.runtime_context import ScreenshotManager
from src.pages.cart_page import CartPage
from src.pages.checkout_page import CheckoutPage


class CheckoutFlow:
    """Task B: fill checkout contact/shipping details and stop before payment."""

    def __init__(
        self,
        driver: WebDriver,
        app_config: Dict[str, Any],
        test_data: Dict[str, Any],
        screenshots: ScreenshotManager | None = None,
    ) -> None:
        self.driver = driver
        self.app_config = app_config
        self.test_data = test_data
        self.base_url = app_config["base_url"].rstrip("/")
        self.timeout = int(app_config.get("timeout_seconds", 20))
        self.screenshots = screenshots
        self.retry = RetryRunner(int(app_config.get("retry", {}).get("max_attempts", 3)), screenshots)
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, printer: ResultPrinter) -> None:
        cart_page = CartPage(self.driver, self.base_url, self.timeout)
        checkout_page = CheckoutPage(self.driver, self.base_url, self.timeout, screenshots=self.screenshots)

        self.retry.run("proceed_to_checkout", cart_page.proceed_to_checkout)
        checkout_page.handle_optional_addon_popup()
        self.retry.run("wait_for_checkout_page", checkout_page.wait_until_loaded)

        try:
            self.retry.run(
                "fill_and_verify_checkout_form",
                lambda: checkout_page.fill_and_verify_contact_and_shipping(self.test_data["checkout"], printer),
            )
        except CaptchaDetectedError as exc:
            # Captcha should be documented/captured, not bypassed.
            printer.check("Checkout captcha/challenge not shown", False, str(exc))
            self.logger.warning("Stopping Task B because captcha/challenge is present: %s", exc)
