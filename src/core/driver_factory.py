from __future__ import annotations

from typing import Any, Dict

from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.remote.webdriver import WebDriver


def create_driver(app_config: Dict[str, Any], headless_override: bool | None = None) -> WebDriver:
    """Create a Chrome WebDriver using Selenium Manager."""
    browser_config = app_config.get("browser", {})
    headless = browser_config.get("headless", False) if headless_override is None else headless_override

    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        width = browser_config.get("window_width", 1440)
        height = browser_config.get("window_height", 1200)
        options.add_argument("--headless=new")
        options.add_argument(f"--window-size={width},{height}")

    return webdriver.Chrome(options=options)
