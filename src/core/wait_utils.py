from __future__ import annotations

import time
from typing import Iterable, Optional, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

Locator = Tuple[str, str]


def wait_for(driver: WebDriver, timeout: int) -> WebDriverWait:
    return WebDriverWait(
        driver,
        timeout,
        poll_frequency=0.25,
        ignored_exceptions=(StaleElementReferenceException,),
    )


def wait_for_document_ready(driver: WebDriver, timeout: int) -> None:
    wait_for(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")


def visible_elements(driver: WebDriver, locator: Locator) -> list[WebElement]:
    elements: list[WebElement] = []
    for element in driver.find_elements(*locator):
        try:
            if element.is_displayed():
                elements.append(element)
        except StaleElementReferenceException:
            continue
    return elements


def first_visible(driver: WebDriver, locators: Iterable[Locator], timeout: int) -> WebElement:
    end_time = time.time() + timeout
    locators = list(locators)
    last_error: Optional[Exception] = None

    while time.time() < end_time:
        for locator in locators:
            try:
                elements = visible_elements(driver, locator)
                if elements:
                    return elements[0]
            except Exception as exc:  # DOM can re-render while testing live Shopify pages.
                last_error = exc
        time.sleep(0.25)

    raise TimeoutException(f"No visible element found. Locators={locators}; last_error={last_error}")


def safe_click(driver: WebDriver, element: WebElement, timeout: int) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
    try:
        wait_for(driver, timeout).until(lambda _: element.is_displayed() and element.is_enabled())
        element.click()
    except (ElementClickInterceptedException, TimeoutException, StaleElementReferenceException):
        driver.execute_script("arguments[0].click();", element)
