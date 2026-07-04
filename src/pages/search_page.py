from __future__ import annotations

from collections import OrderedDict

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from src.core.wait_utils import wait_for
from src.core.text_utils import normalize
from src.pages.base_page import BasePage


class SearchResultsPage(BasePage):
    PRODUCT_LINKS = (By.CSS_SELECTOR, "a[href*='/products/']")

    def wait_for_results(self) -> None:
        wait_for(self.driver, self.timeout).until(lambda _: len(self.product_links()) > 0)

    def product_links(self) -> list[WebElement]:
        """Return unique visible product links from search results."""
        links = self.visible_elements(self.PRODUCT_LINKS)
        unique: OrderedDict[str, WebElement] = OrderedDict()

        for link in links:
            try:
                href = (link.get_attribute("href") or "").split("?")[0]
                text = normalize(link.text or link.get_attribute("aria-label"))
            except StaleElementReferenceException:
                continue
            if href and "/products/" in href:
                unique[href] = link

        return list(unique.values())
