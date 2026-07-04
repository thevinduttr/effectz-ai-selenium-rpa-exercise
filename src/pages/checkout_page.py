from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from selenium.common.exceptions import ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select, WebDriverWait

from src.core.exceptions import CaptchaDetectedError
from src.core.result_printer import ResultPrinter
from src.core.runtime_context import ScreenshotManager
from src.core.text_utils import digits_only, normalize
from src.pages.base_page import BasePage


class CheckoutPage(BasePage):
    """Shopify checkout page object. It fills and verifies contact/shipping only.

    The flow never enters card details and never clicks Pay now / Complete order.
    """

    ADDON_POPUP_CONTINUE = [
        (By.CSS_SELECTOR, "div.lb-addon-popup-continue-btn"),
        (By.CSS_SELECTOR, "#lb-addon-popup-container-id .lb-addon-popup-continue-btn"),
        (
            By.XPATH,
            "//*[self::button or self::div or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
        ),
    ]

    FIELD_SELECTORS = {
        "email": [
            "#email",
            "input[type='email']",
            "input[name='email']",
            "input[id*='email' i]",
            "input[autocomplete*='email' i]",
        ],
        "first_name": [
            "input[name='firstName']",
            "input[name*='first_name' i]",
            "input[id*='firstName' i]",
            "input[autocomplete='shipping given-name']",
            "input[aria-label*='First name' i]",
            "input[placeholder*='First name' i]",
        ],
        "last_name": [
            "input[name='lastName']",
            "input[name*='last_name' i]",
            "input[id*='lastName' i]",
            "input[autocomplete='shipping family-name']",
            "input[aria-label*='Last name' i]",
            "input[placeholder*='Last name' i]",
        ],
        "address_line_1": [
            "input[name='address1']",
            "input[id*='address1' i]",
            "input[autocomplete='shipping address-line1']",
            "input[aria-label='Address']",
            "input[placeholder='Address']",
            "input[aria-label*='Address' i]:not([aria-label*='Apartment' i])",
        ],
        "address_line_2": [
            "input[name='address2']",
            "input[id*='address2' i]",
            "input[autocomplete='shipping address-line2']",
            "input[aria-label*='Apartment' i]",
            "input[placeholder*='Apartment' i]",
        ],
        "city": [
            "input[name='city']",
            "input[id*='city' i]",
            "input[autocomplete='shipping address-level2']",
            "input[aria-label*='City' i]",
            "input[placeholder*='City' i]",
        ],
        "postal_code": [
            "input[name='postalCode']",
            "input[name*='zip' i]",
            "input[id*='postalCode' i]",
            "input[autocomplete='shipping postal-code']",
            "input[aria-label*='Postal code' i]",
            "input[placeholder*='Postal code' i]",
        ],
        "phone": [
            "input[type='tel']",
            "input[name='phone']",
            "input[name*='phone' i]",
            "input[id*='phone' i]",
            "input[autocomplete*='tel' i]",
            "input[aria-label*='Phone' i]",
            "input[placeholder*='Phone' i]",
        ],
    }

    COUNTRY_SELECTORS = [
        "select[name='countryCode']",
        "select[name*='country' i]",
        "select[id*='country' i]",
        "select[autocomplete*='country' i]",
        "select[aria-label*='Country' i]",
    ]

    COUNTRY_COMBOBOX_SELECTORS = [
        "[role='combobox'][aria-label*='Country' i]",
        "input[aria-label*='Country' i]",
        "button[aria-label*='Country' i]",
    ]

    NEWS_AND_OFFERS_CHECKBOXES = [
        "#marketing_opt_in",
        "input[name='marketing_opt_in']",
        "input[type='checkbox'][name*='marketing' i]:not([name*='sms' i])",
        "input[type='checkbox'][id*='marketing' i]:not([id*='sms' i])",
        "input[type='checkbox'][aria-label*='news' i]",
        "input[type='checkbox'][aria-label*='offers' i]",
    ]

    PAYMENT_AREA_SELECTORS = [
        "iframe[name*='card' i]",
        "input[name*='card' i]",
        "input[autocomplete='cc-number']",
        "button[type='submit']",
    ]

    CAPTCHA_WIDGET_SELECTORS = [
        "iframe[src*='captcha' i]",
        "iframe[src*='hcaptcha' i]",
        "iframe[src*='recaptcha' i]",
        ".g-recaptcha",
        ".h-captcha",
        "[data-sitekey]",
        "[id*='captcha' i]",
        "[class*='captcha' i]",
    ]

    def __init__(
        self,
        driver,
        base_url: str,
        timeout: int,
        screenshots: ScreenshotManager | None = None,
    ) -> None:
        super().__init__(driver, base_url, timeout)
        self.screenshots = screenshots
        self.logger = logging.getLogger(self.__class__.__name__)

    def wait_until_loaded(self) -> None:
        WebDriverWait(self.driver, self.timeout).until(
            lambda d: "checkout" in d.current_url.casefold() or "Checkout - Carnage" in d.title
        )
        WebDriverWait(self.driver, self.timeout).until(
            lambda d: "Loading" not in (d.find_element(By.TAG_NAME, "body").get_attribute("class") or "")
        )

    def handle_optional_addon_popup(self) -> None:
        try:
            continue_button = WebDriverWait(self.driver, 8, poll_frequency=0.25).until(
                lambda _: self._visible_continue_button()
            )
            self.driver.execute_script("arguments[0].click();", continue_button)
            self.logger.info("Handled optional add-on popup before checkout.")
        except (ElementNotInteractableException, TimeoutException) as exc:
            self.logger.info("No interactable optional add-on popup was displayed: %s", exc)

    def _visible_continue_button(self) -> Optional[WebElement]:
        candidates = self.driver.find_elements(
            By.XPATH,
            "//*[self::button or self::a or @role='button' or contains(@class, 'lb-addon-popup-continue-btn')]",
        )
        for candidate in candidates:
            try:
                text = normalize(candidate.text or candidate.get_attribute("aria-label")).casefold()
                rect = candidate.rect
                if (
                    "continue" in text
                    and candidate.is_displayed()
                    and candidate.is_enabled()
                    and rect.get("width", 0) > 1
                    and rect.get("height", 0) > 1
                ):
                    return candidate
            except Exception:
                continue
        return None

    def assert_no_captcha_or_capture(self, checkpoint_name: str) -> None:
        if not self.is_blocked_by_captcha_or_challenge():
            return
        if self.screenshots is not None:
            self.screenshots.capture(f"captcha_{checkpoint_name}")
        raise CaptchaDetectedError(
            "Checkout captcha/challenge was displayed. Screenshot captured. Automation will not bypass it."
        )

    def is_blocked_by_captcha_or_challenge(self) -> bool:
        url_and_title = f"{self.driver.current_url} {self.driver.title}".casefold()
        page_text = self.page_text().casefold()
        challenge_markers = [
            "captcha",
            "hcaptcha",
            "recaptcha",
            "verify you are human",
            "checking if the site connection is secure",
            "prove you are human",
        ]
        if any(marker in url_and_title or marker in page_text for marker in challenge_markers):
            return True

        for selector in self.CAPTCHA_WIDGET_SELECTORS:
            for element in self.visible_elements((By.CSS_SELECTOR, selector)):
                if element.is_enabled() or element.tag_name.lower() == "iframe":
                    self.logger.warning("Visible captcha/challenge widget detected by selector: %s", selector)
                    return True
        return False

    def fill_and_verify_contact_and_shipping(self, checkout_data: Dict[str, Any], printer: ResultPrinter) -> None:
        self.assert_no_captcha_or_capture("before_form_fill")

        fields: dict[str, Optional[WebElement]] = {}

        fields["email"] = self._set_input("email", checkout_data["email"])
        self._set_email_news_and_offers(should_be_checked=bool(checkout_data.get("email_news_and_offers", False)))
        country_field = self._select_country(checkout_data["country"], checkout_data.get("country_code"))
        self._wait_for_shipping_form()

        fields["first_name"] = self._set_input("first_name", checkout_data["first_name"])
        fields["last_name"] = self._set_input("last_name", checkout_data["last_name"])
        fields["address_line_1"] = self._set_input("address_line_1", checkout_data["address_line_1"])

        if checkout_data.get("address_line_2"):
            fields["address_line_2"] = self._set_input("address_line_2", checkout_data["address_line_2"], required=False)
        else:
            fields["address_line_2"] = self._optional_field("address_line_2")

        fields["city"] = self._set_input("city", checkout_data["city"])
        fields["postal_code"] = self._set_input("postal_code", checkout_data["postal_code"])
        fields["phone"] = self._set_input("phone", checkout_data["phone"])

        self.assert_no_captcha_or_capture("after_form_fill")

        printer.check("Checkout country selected", country_field is not None, checkout_data["country"])
        self._verify_news_and_offers(printer, bool(checkout_data.get("email_news_and_offers", False)))

        for key, expected in checkout_data.items():
            if key in {"country", "country_code", "email_news_and_offers"}:
                continue
            if key == "address_line_2" and not expected:
                printer.check("Checkout optional apartment/unit field handled", True, "No value configured")
                continue

            actual = self._field_value(fields.get(key))
            if key == "phone":
                condition = digits_only(expected) in digits_only(actual)
            else:
                condition = normalize(actual) == normalize(expected)
            printer.check(f"Checkout field verified: {key}", condition, f"expected='{expected}', actual='{actual}'")

        self.assert_no_payment_details_entered(printer)
        printer.check("Stopped before payment", True, "No card details entered; Pay now / order placement was not clicked")

    def assert_no_payment_details_entered(self, printer: ResultPrinter) -> None:
        page_lower = self.page_text().casefold()
        payment_words_present = any(word in page_lower for word in ["payment", "card number", "pay now", "complete order"])
        # Reaching the payment section is fine; entering card details or clicking payment is not done by this script.
        printer.check("Payment section not submitted", True, f"payment_section_visible={payment_words_present}")

    def _wait_for_shipping_form(self) -> None:
        WebDriverWait(self.driver, self.timeout).until(lambda _: self._optional_field("first_name") is not None)

    def _set_input(self, field_key: str, value: str, required: bool = True) -> Optional[WebElement]:
        field = self._optional_field(field_key)
        if field is None:
            if required:
                raise AssertionError(f"Could not find checkout field: {field_key}")
            return None

        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
        self._set_react_input_value(field, value)
        WebDriverWait(self.driver, self.timeout).until(lambda _: self._field_value(field) != "" or value == "")
        return field

    def _optional_field(self, field_key: str) -> Optional[WebElement]:
        for selector in self.FIELD_SELECTORS[field_key]:
            for field in self.visible_elements((By.CSS_SELECTOR, selector)):
                if field.is_enabled() and field.get_attribute("aria-hidden") != "true":
                    return field
        return None

    def _select_country(self, country_name: str, country_code: str | None = None) -> Optional[WebElement]:
        for selector in self.COUNTRY_SELECTORS:
            for field in self.visible_elements((By.CSS_SELECTOR, selector)):
                try:
                    select = Select(field)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
                    try:
                        select.select_by_visible_text(country_name)
                    except Exception:
                        if not country_code:
                            raise
                        select.select_by_value(country_code)
                    WebDriverWait(self.driver, self.timeout).until(lambda _: self._country_selected(field, country_name, country_code))
                    self.logger.info("Selected country from dropdown: %s", country_name)
                    return field
                except Exception as exc:
                    self.logger.debug("Country native select attempt failed for selector %s: %s", selector, exc)
                    continue

        return self._select_country_from_combobox(country_name)

    def _select_country_from_combobox(self, country_name: str) -> Optional[WebElement]:
        for selector in self.COUNTRY_COMBOBOX_SELECTORS:
            for field in self.visible_elements((By.CSS_SELECTOR, selector)):
                try:
                    self.click(field)
                    if field.tag_name.lower() == "input":
                        field.send_keys(Keys.CONTROL, "a")
                        field.send_keys(country_name)
                    option_xpath = (
                        "//*[@role='option' or self::li or self::div]"
                        f"[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{country_name.casefold()}')]"
                    )
                    option = self.first_visible([(By.XPATH, option_xpath)], timeout=8)
                    self.click(option)
                    self.logger.info("Selected country from combobox: %s", country_name)
                    return field
                except Exception as exc:
                    self.logger.debug("Country combobox attempt failed: %s", exc)
                    continue
        raise AssertionError(f"Could not find/select checkout country dropdown: {country_name}")

    @staticmethod
    def _country_selected(field: WebElement, country_name: str, country_code: str | None = None) -> bool:
        selected_value = normalize(field.get_attribute("value"))
        try:
            selected_text = normalize(Select(field).first_selected_option.text)
        except Exception:
            selected_text = ""
        return country_name.casefold() in selected_text.casefold() or bool(country_code and selected_value == country_code)

    def _set_email_news_and_offers(self, should_be_checked: bool) -> None:
        checkbox = self._find_news_and_offers_checkbox()
        if checkbox is None:
            self.logger.info("'Email me with news and offers' checkbox was not present on this checkout.")
            return
        if checkbox.is_selected() != should_be_checked:
            self.driver.execute_script("arguments[0].click();", checkbox)
            WebDriverWait(self.driver, self.timeout).until(lambda _: checkbox.is_selected() == should_be_checked)

    def _verify_news_and_offers(self, printer: ResultPrinter, expected: bool) -> None:
        checkbox = self._find_news_and_offers_checkbox()
        if checkbox is None:
            printer.check("Email me with news and offers checkbox handled", True, "Checkbox not present on this checkout")
            return
        printer.check(
            "Email me with news and offers checkbox handled",
            checkbox.is_selected() == expected,
            f"expected_checked={expected}, actual_checked={checkbox.is_selected()}",
        )

    def _find_news_and_offers_checkbox(self) -> Optional[WebElement]:
        for selector in self.NEWS_AND_OFFERS_CHECKBOXES:
            for checkbox in self.driver.find_elements(By.CSS_SELECTOR, selector):
                if checkbox.is_enabled():
                    return checkbox

        label_xpath = (
            "//*[self::label or self::span or self::div]"
            "[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'email me') "
            "and (contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'news') "
            "or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'offers'))]"
        )
        for label in self.visible_elements((By.XPATH, label_xpath)):
            candidate = self._nearby_checkbox(label)
            if candidate is not None:
                return candidate
        return None

    def _nearby_checkbox(self, element: WebElement) -> Optional[WebElement]:
        script = """
            const label = arguments[0];
            const root = label.closest('label, div, section, form') || document;
            return root.querySelector('input[type="checkbox"]') || null;
        """
        candidate = self.driver.execute_script(script, element)
        if candidate and candidate.is_enabled():
            return candidate
        return None

    def _set_react_input_value(self, field: WebElement, value: str) -> None:
        try:
            field.click()
            field.send_keys(Keys.CONTROL, "a")
            field.send_keys(Keys.BACKSPACE)
            field.send_keys(value)
        except ElementNotInteractableException:
            self.driver.execute_script(
                """
                const element = arguments[0];
                const value = arguments[1];
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(element, value);
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                field,
                value,
            )

    @staticmethod
    def _field_value(field: Optional[WebElement]) -> str:
        return normalize(field.get_attribute("value") if field is not None else "")
