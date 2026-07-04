from __future__ import annotations

from urllib.parse import quote_plus

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from src.pages.base_page import BasePage


class HomePage(BasePage):
    SEARCH_OPENERS = [
        (By.CSS_SELECTOR, "#search-toggle"),
        (By.CSS_SELECTOR, "summary[aria-label*='Search' i]"),
        (By.CSS_SELECTOR, "button[aria-label*='Search' i]"),
        (By.CSS_SELECTOR, "a[href*='/search']"),
        (By.CSS_SELECTOR, ".header__icon--search"),
        (By.CSS_SELECTOR, "[data-search-open]"),
    ]

    SEARCH_INPUTS = [
        (By.CSS_SELECTOR, "#search-input"),
        (By.CSS_SELECTOR, "input[type='search']"),
        (By.CSS_SELECTOR, "input[name='q']"),
        (By.CSS_SELECTOR, "input[placeholder*='Search' i]"),
    ]

    def open_home(self) -> None:
        self.open_path("")

    def search(self, keyword: str) -> None:
        """Search through the site UI; fallback to Shopify's /search route if the icon is hidden."""
        self.open_home()
        try:
            opener = self.first_visible(self.SEARCH_OPENERS, timeout=6)
            self.click(opener)
            search_input = self.first_visible(self.SEARCH_INPUTS, timeout=8)
            search_input.clear()
            search_input.send_keys(keyword)
            search_input.send_keys(Keys.ENTER)
        except TimeoutException:
            self.driver.get(f"{self.base_url}/search?q={quote_plus(keyword)}")

        WebDriverWait(self.driver, self.timeout).until(lambda d: self._search_page_loaded(d, keyword))

    @staticmethod
    def _search_page_loaded(driver, keyword: str) -> bool:
        current_url = driver.current_url or ""
        page_source = driver.page_source or ""
        return "/search" in current_url or keyword.casefold() in page_source.casefold()
