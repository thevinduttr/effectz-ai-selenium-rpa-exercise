from __future__ import annotations

import logging
from typing import Any, Dict

from selenium.webdriver.remote.webdriver import WebDriver

from src.core.result_printer import ResultPrinter
from src.core.retry import RetryRunner
from src.core.runtime_context import ScreenshotManager
from src.core.text_utils import normalize_key
from src.models.product import AddedProduct
from src.pages.cart_page import CartPage
from src.pages.home_page import HomePage
from src.pages.product_page import ProductPage
from src.pages.search_page import SearchResultsPage
from src.services.shopify_cart_service import ShopifyCartService


class ShoppingFlow:
    """Task A: search, dynamically choose available sizes, add 2 products, and verify cart."""

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
        self.cart_service = ShopifyCartService(driver, self.timeout)
        self.retry = RetryRunner(int(app_config.get("retry", {}).get("max_attempts", 3)), screenshots)
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, printer: ResultPrinter) -> list[AddedProduct]:
        shopping_data = self.test_data["shopping"]
        keywords = shopping_data["search_keywords"]
        expected_item_count = int(self.app_config.get("cart", {}).get("expected_item_count", 2))

        if len(keywords) < expected_item_count:
            raise AssertionError("At least two search keywords are required in config/test_data.json")

        if self.app_config.get("cart", {}).get("clear_before_run", True):
            self.retry.run("clear_cart", lambda: self.cart_service.clear_cart(self.base_url))

        added_products: list[AddedProduct] = []
        for keyword in keywords[:expected_item_count]:
            product = self.retry.run(
                f"search_and_add_product_{keyword}",
                lambda keyword=keyword: self._search_and_add_available_product(keyword, added_products),
            )
            added_products.append(product)
            self.logger.info("Added product: %s | size: %s | keyword: %s", product.name, product.size or "N/A", keyword)
            print(f"Added product: {product.name} | size: {product.size or 'N/A'} | keyword: {keyword}")

        self.retry.run(
            "verify_cart",
            lambda: CartPage(self.driver, self.base_url, self.timeout).verify_cart(
                added_products,
                expected_item_count=expected_item_count,
                printer=printer,
            ),
        )
        return added_products

    def _search_and_add_available_product(self, keyword: str, already_added: list[AddedProduct]) -> AddedProduct:
        home = HomePage(self.driver, self.base_url, self.timeout)
        search_results = SearchResultsPage(self.driver, self.base_url, self.timeout)
        product_page = ProductPage(self.driver, self.base_url, self.timeout)

        already_added_names = {normalize_key(product.name) for product in already_added}
        tried_urls: set[str] = set()
        max_candidates = int(self.app_config.get("execution", {}).get("retry_product_candidates_per_keyword", 12))

        home.search(keyword)
        search_results.wait_for_results()

        for _ in range(max_candidates):
            product_link = self._next_untried_product_link(search_results, tried_urls)
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", product_link)
            self.driver.execute_script("arguments[0].click();", product_link)

            try:
                current_product_name = product_page.title()
                if normalize_key(current_product_name) in already_added_names:
                    self.logger.info("Skipping duplicate product: %s", current_product_name)
                    self.driver.back()
                    search_results.wait_for_results()
                    continue

                return product_page.add_to_cart(keyword=keyword, cart_service=self.cart_service)
            except Exception as exc:
                self.logger.warning("Skipping product for keyword '%s' because it could not be added: %s", keyword, exc)
                print(f"Skipping product for keyword '{keyword}' because it could not be added: {exc}")
                self.driver.back()
                search_results.wait_for_results()

        raise AssertionError(f"Could not add an available product for keyword '{keyword}'.")

    @staticmethod
    def _next_untried_product_link(search_results: SearchResultsPage, tried_urls: set[str]):
        for link in search_results.product_links():
            href = (link.get_attribute("href") or "").split("?")[0]
            if href and href not in tried_urls:
                tried_urls.add(href)
                return link
        raise AssertionError("No more untried product links were available in the search results.")
