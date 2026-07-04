from __future__ import annotations

from typing import Any, Dict

from selenium.common.exceptions import JavascriptException, TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

from src.core.wait_utils import wait_for


class ShopifyCartService:
    """Reads Shopify cart data through /cart.js for reliable arithmetic assertions."""

    def __init__(self, driver: WebDriver, timeout: int) -> None:
        self.driver = driver
        self.timeout = timeout

    def get_cart_state(self) -> Dict[str, Any]:
        script = """
            const done = arguments[0];
            fetch('/cart.js', {credentials: 'same-origin'})
              .then(response => response.json())
              .then(data => done({ok: true, data}))
              .catch(error => done({ok: false, error: String(error)}));
        """
        try:
            result = self.driver.execute_async_script(script)
            if result and result.get("ok"):
                return result.get("data", {})
        except JavascriptException:
            pass
        return {}

    def wait_until_item_count_is(self, expected_count: int) -> None:
        wait_for(self.driver, self.timeout).until(
            lambda _: int(self.get_cart_state().get("item_count", 0)) == expected_count
        )

    def wait_until_item_count_greater_than(self, previous_count: int) -> None:
        wait_for(self.driver, self.timeout).until(
            lambda _: int(self.get_cart_state().get("item_count", 0)) > previous_count
        )

    def clear_cart(self, base_url: str) -> None:
        self.driver.get(f"{base_url}/cart/clear")
        try:
            self.wait_until_item_count_is(0)
        except TimeoutException:
            # Some themes redirect after /cart/clear. Continue; the next read will validate state.
            pass
