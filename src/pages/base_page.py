from __future__ import annotations

from typing import Iterable

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from src.core.wait_utils import Locator, first_visible, safe_click, wait_for_document_ready, visible_elements
from src.core.text_utils import normalize


class BasePage:
    def __init__(self, driver: WebDriver, base_url: str, timeout: int) -> None:
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def open_path(self, path: str) -> None:
        self.driver.get(f"{self.base_url}/{path.lstrip('/')}")
        wait_for_document_ready(self.driver, self.timeout)

    def click(self, element: WebElement) -> None:
        safe_click(self.driver, element, self.timeout)

    def first_visible(self, locators: Iterable[Locator], timeout: int | None = None) -> WebElement:
        return first_visible(self.driver, locators, timeout or self.timeout)

    def visible_elements(self, locator: Locator) -> list[WebElement]:
        return visible_elements(self.driver, locator)

    def page_text(self) -> str:
        return normalize(self.driver.find_element("tag name", "body").text)
