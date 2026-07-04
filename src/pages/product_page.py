from __future__ import annotations

import logging
from typing import Iterable, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select, WebDriverWait

from src.core.text_utils import normalize
from src.models.product import AddedProduct
from src.pages.base_page import BasePage
from src.services.shopify_cart_service import ShopifyCartService


class ProductPage(BasePage):
    """Product page object with dynamic variant/size selection.

    No product name or size value is hardcoded. When a product exposes size options,
    the page object reads the currently available controls and selects the first enabled option.
    """

    TITLE_LOCATORS = [
        (By.CSS_SELECTOR, "main h1"),
        (By.CSS_SELECTOR, "h1"),
        (By.CSS_SELECTOR, "[class*='title']"),
    ]

    ADD_TO_CART_LOCATORS = [
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart') and not(@disabled)]",
        ),
        (By.CSS_SELECTOR, "#main-content form button:not([disabled])"),
        (By.CSS_SELECTOR, "button[name='add']:not([disabled])"),
        (By.CSS_SELECTOR, "form[action*='/cart/add'] button[type='submit']:not([disabled])"),
    ]

    ADD_TO_CART_OR_UNAVAILABLE_LOCATORS = [
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart') "
            "or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sold out') "
            "or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unavailable')]",
        ),
        (By.CSS_SELECTOR, "button[name='add']"),
        (By.CSS_SELECTOR, "form[action*='/cart/add'] button[type='submit']"),
    ]

    SIZE_OPTION_GROUPS = [
        (
            By.XPATH,
            "//fieldset[.//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'size')]]",
        ),
        (
            By.XPATH,
            "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'size')]/ancestor::*[self::div or self::section or self::fieldset][1]",
        ),
        (By.CSS_SELECTOR, "variant-radios fieldset, variant-selects, .product-form__input, .product-page__details-wrapper"),
    ]

    def __init__(self, driver, base_url: str, timeout: int) -> None:
        super().__init__(driver, base_url, timeout)
        self.logger = logging.getLogger(self.__class__.__name__)

    def title(self) -> str:
        return normalize(self.first_visible(self.TITLE_LOCATORS).text)

    def select_available_size(self) -> str | None:
        """Select the first enabled size/variant option visible on the product page."""
        selected = self._select_from_native_size_dropdown()
        if selected:
            return selected

        selected = self._select_from_radio_inputs()
        if selected:
            return selected

        selected = self._select_from_buttons_or_labels()
        if selected:
            return selected

        self.logger.info("No size selector found. Continuing as one-size/no-size product.")
        return None

    def add_to_cart(self, keyword: str, cart_service: ShopifyCartService) -> AddedProduct:
        product_name = self.title()
        selected_size = self.select_available_size()
        before_count = int(cart_service.get_cart_state().get("item_count", 0))

        self._raise_if_product_unavailable(product_name, selected_size)
        try:
            add_button = self.first_visible(self.ADD_TO_CART_LOCATORS, timeout=10)
        except TimeoutException as exc:
            raise AssertionError(
                f"Product is not available or add button did not become enabled: "
                f"{product_name} | size={selected_size or 'N/A'} | url={self.driver.current_url}"
            ) from exc
        button_text = normalize(add_button.text).casefold()
        if "sold" in button_text or "unavailable" in button_text:
            raise AssertionError(
                f"Product is not available: {product_name} | size={selected_size or 'N/A'} | "
                f"button='{normalize(add_button.text)}' | url={self.driver.current_url}"
            )

        self.click(add_button)
        cart_service.wait_until_item_count_greater_than(before_count)

        return AddedProduct(
            keyword=keyword,
            name=product_name,
            size=selected_size,
            product_url=self.driver.current_url,
        )

    def _raise_if_product_unavailable(self, product_name: str, selected_size: str | None) -> None:
        for locator in self.ADD_TO_CART_OR_UNAVAILABLE_LOCATORS:
            for button in self.visible_elements(locator):
                text = normalize(button.text or button.get_attribute("aria-label")).casefold()
                classes = (button.get_attribute("class") or "").casefold()
                disabled = button.get_attribute("disabled") is not None
                aria_disabled = (button.get_attribute("aria-disabled") or "").casefold() == "true"
                unavailable = "sold" in text or "unavailable" in text or "sold" in classes or "unavailable" in classes
                if unavailable or (disabled or aria_disabled) and "add to cart" in text:
                    label = normalize(button.text or button.get_attribute("aria-label"))
                    raise AssertionError(
                        f"Product is sold out/unavailable: {product_name} | size={selected_size or 'N/A'} | "
                        f"button='{label or 'disabled add button'}' | url={self.driver.current_url}"
                    )

    def _select_from_native_size_dropdown(self) -> Optional[str]:
        selects = self.driver.find_elements(
            By.XPATH,
            "//select[not(@disabled) and (contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'size') "
            "or contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'size') "
            "or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'size'))]",
        )
        for select_el in selects:
            if not select_el.is_displayed() or not select_el.is_enabled():
                continue
            select = Select(select_el)
            for option in select.options:
                label = normalize(option.text or option.get_attribute("label") or option.get_attribute("value"))
                if self._is_unavailable_option(option, label):
                    continue
                select.select_by_visible_text(option.text)
                self._wait_until_add_button_is_enabled()
                self.logger.info("Selected size from dropdown: %s", label)
                return label
        return None

    def _select_from_radio_inputs(self) -> Optional[str]:
        groups = self._size_groups()
        radios: list[WebElement] = []
        for group in groups:
            radios.extend(group.find_elements(By.CSS_SELECTOR, "input[type='radio']:not([disabled])"))

        for radio in radios:
            if not radio.is_enabled():
                continue
            label = self._label_for_input(radio) or normalize(radio.get_attribute("value") or radio.get_attribute("aria-label"))
            if not label or self._looks_unavailable(label):
                continue
            clickable = self._clickable_label_for_input(radio) or radio
            self.click(clickable)
            self._wait_until_add_button_is_enabled()
            self.logger.info("Selected size from radio option: %s", label)
            return label
        return None

    def _select_from_buttons_or_labels(self) -> Optional[str]:
        for group in self._size_groups():
            candidates = self._option_candidates(group)
            for candidate in candidates:
                label = normalize(candidate.text or candidate.get_attribute("aria-label") or candidate.get_attribute("value"))
                if not self._is_available_click_target(candidate, label):
                    continue
                self.click(candidate)
                self._wait_until_add_button_is_enabled()
                self.logger.info("Selected size from visible option: %s", label)
                return label
        return None

    def _size_groups(self) -> list[WebElement]:
        groups: list[WebElement] = []
        seen: set[str] = set()
        for locator in self.SIZE_OPTION_GROUPS:
            for group in self.visible_elements(locator):
                key = group.id
                group_text = normalize(group.text).casefold()
                if key in seen:
                    continue
                # Prefer groups that are actually about sizes; keep the broad wrapper as fallback.
                if "size" in group_text or group.tag_name.lower() in {"variant-radios", "variant-selects"} or "product-page" in (group.get_attribute("class") or ""):
                    groups.append(group)
                    seen.add(key)
        return groups

    @staticmethod
    def _option_candidates(group: WebElement) -> list[WebElement]:
        return group.find_elements(
            By.XPATH,
            ".//*[self::button or self::label or @role='button'][normalize-space(.)!='']",
        )

    def _is_available_click_target(self, element: WebElement, label: str) -> bool:
        if not label:
            return False
        lower_label = label.casefold()
        blocked_words = [
            "add to cart",
            "buy",
            "checkout",
            "quantity",
            "size guide",
            "sold out",
            "unavailable",
            "notify",
            "share",
        ]
        if any(word in lower_label for word in blocked_words):
            return False
        if not element.is_displayed() or not element.is_enabled():
            return False
        classes = (element.get_attribute("class") or "").casefold()
        aria_disabled = (element.get_attribute("aria-disabled") or "").casefold() == "true"
        disabled = element.get_attribute("disabled") is not None
        if disabled or aria_disabled or any(word in classes for word in ["disabled", "sold", "unavailable"]):
            return False
        input_id = element.get_attribute("for")
        if input_id:
            try:
                linked = element.parent.find_element(By.CSS_SELECTOR, f"input#{input_id}")
                if linked.get_attribute("disabled") is not None:
                    return False
            except NoSuchElementException:
                pass
        return True

    @staticmethod
    def _is_unavailable_option(option: WebElement, label: str) -> bool:
        return not label or option.get_attribute("disabled") is not None or "sold" in label.casefold() or "unavailable" in label.casefold()

    @staticmethod
    def _looks_unavailable(label: str) -> bool:
        value = label.casefold()
        return "sold" in value or "unavailable" in value or "disabled" in value

    def _clickable_label_for_input(self, radio: WebElement) -> Optional[WebElement]:
        radio_id = radio.get_attribute("id")
        if not radio_id:
            return None
        labels = self.driver.find_elements(By.CSS_SELECTOR, f"label[for='{radio_id}']")
        for label in labels:
            if label.is_displayed() and label.is_enabled():
                return label
        return None

    def _label_for_input(self, radio: WebElement) -> str:
        label = self._clickable_label_for_input(radio)
        if label is not None:
            return normalize(label.text)
        return normalize(radio.get_attribute("value") or radio.get_attribute("aria-label"))

    def _wait_until_add_button_is_enabled(self) -> None:
        WebDriverWait(self.driver, self.timeout).until(
            lambda _: any(self._add_button_enabled(button) for button in self.driver.find_elements(By.CSS_SELECTOR, "button"))
        )

    @staticmethod
    def _add_button_enabled(button: WebElement) -> bool:
        text = normalize(button.text).casefold()
        return "add to cart" in text and button.is_displayed() and button.is_enabled() and button.get_attribute("disabled") is None
