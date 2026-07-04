from __future__ import annotations

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from src.core.money import cents_to_amount, lkr_label
from src.core.result_printer import ResultPrinter
from src.core.text_utils import normalize, normalize_key, xpath_literal
from src.models.product import AddedProduct
from src.pages.base_page import BasePage
from src.services.shopify_cart_service import ShopifyCartService


class CartPage(BasePage):
    CHECKOUT_BUTTONS = [
        (By.CSS_SELECTOR, "button[name='checkout']"),
        (By.CSS_SELECTOR, "a[href*='/checkout']"),
        (
            By.XPATH,
            "//*[self::a or self::button][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'check out') or contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'checkout')]",
        ),
    ]

    def open_cart(self) -> None:
        self.open_path("cart")

    def verify_cart(self, added_products: list[AddedProduct], expected_item_count: int, printer: ResultPrinter) -> None:
        self.open_cart()
        cart_service = ShopifyCartService(self.driver, self.timeout)
        cart_state = cart_service.get_cart_state()
        cart_items = cart_state.get("items", [])
        cart_text = self.page_text()

        expected_names = [product.name for product in added_products]
        cart_names = [normalize(item.get("product_title") or item.get("title") or "") for item in cart_items]
        item_count = int(cart_state.get("item_count", 0))

        printer.check(
            "Cart contains exactly 2 items",
            item_count == expected_item_count,
            f"expected={expected_item_count}, actual={item_count}",
        )

        missing_names = [
            name for name in expected_names if not any(name.casefold() in cart_name.casefold() for cart_name in cart_names)
        ]
        printer.check(
            "Product names in cart match products added",
            not missing_names,
            f"expected={expected_names}; actual={cart_names}",
        )

        for product_name in expected_names:
            printer.check(
                f"Cart page visibly shows product: {product_name}",
                self._is_text_visible(product_name),
            )

        prices = [cents_to_amount(item.get("final_line_price", 0)) for item in cart_items]
        printer.check(
            "Can read each item's price",
            len(prices) == expected_item_count and all(price > 0 for price in prices),
            f"prices={[lkr_label(price) for price in prices]}",
        )

        subtotal = cents_to_amount(cart_state.get("total_price", 0))
        calculated_sum = round(sum(prices), 2)
        printer.check(
            "Cart subtotal equals the sum of individual item prices",
            subtotal == calculated_sum,
            f"subtotal={lkr_label(subtotal)}, sum={lkr_label(calculated_sum)}",
        )

        for price in prices:
            visible = self._money_value_visible(cart_text, price)
            printer.check(f"Cart page visibly shows price {lkr_label(price)}", visible)

        subtotal_visible = self._money_value_visible(cart_text, subtotal)
        printer.check("Cart page visibly shows subtotal/total", subtotal_visible)

    def proceed_to_checkout(self) -> None:
        self.open_cart()
        checkout_button = self.first_visible(self.CHECKOUT_BUTTONS)
        self.click(checkout_button)

    def _is_text_visible(self, text: str) -> bool:
        try:
            literal = xpath_literal(normalize_key(text))
            self.driver.find_element(
                By.XPATH,
                "//*[contains("
                "translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                f"{literal})]",
            )
            return True
        except NoSuchElementException:
            return normalize_key(text) in normalize_key(self.page_text())

    @staticmethod
    def _money_value_visible(page_text: str, amount: float) -> bool:
        amount_as_int = str(int(amount))
        compact_text = page_text.replace(",", "").replace(".00", "")
        return (
            lkr_label(amount) in page_text
            or amount_as_int in compact_text
            or f"{amount:,.2f}" in page_text
            or f"{amount:.2f}" in page_text.replace(",", "")
        )
