# Carnage Selenium Practical Exercise

Selenium automation solution for the RPA Developer practical exercise on `https://incarnage.com`.

It covers:

- Task A: shopping flow, dynamic product selection, size selection, add to cart, and cart verification
- Task B: checkout contact/shipping form filling, value verification, and stopping before payment

The project uses Python, Selenium, Page Object Model classes, explicit waits, retry handling, logging, screenshots, and clear PASS/FAIL output.

## Project Structure

```text
incarnage-selenium-exercise/
|-- config/
|   |-- app_config.json
|   `-- test_data.json
|-- src/
|   |-- core/
|   |-- flows/
|   |-- models/
|   |-- pages/
|   `-- services/
|-- logs/
|-- screenshots/
|-- run.py
|-- requirements.txt
`-- README.md
```

## Setup

Python 3.10+ is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Selenium Manager is used, so a separate ChromeDriver download is normally not needed when Chrome is installed.

## Simple Botrunner

Run:

```bash
run.bat
```

If setup is not available, botrunner will do this automatically:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The botrunner will ask what to run:

- `1` or `A` runs Task A only
- `2` or `BOTH` runs Task A and Task B

If Chrome is closed or an unexpected browser/session error happens during the run, the botrunner closes that browser and starts Chrome again. The retry count is controlled by `execution.browser_restart_attempts` in `config/app_config.json`.

## How To Run

Run Task A only:

```bash
python run.py --task A
```

Run Task A and Task B:

```bash
python run.py --task BOTH
```

Optional headless mode:

```bash
python run.py --task BOTH --headless
```

Task B starts by running Task A because checkout needs cart items.

## Configuration

`config/app_config.json` controls the base URL, browser settings, timeout, retry count, and artifact directories.

`config/test_data.json` keeps all test data outside the code:

```json
{
  "shopping": {
    "search_keywords": ["tee", "tank"]
  },
  "checkout": {
    "email": "thevindu.rpa.test+incarnage@example.com",
    "email_news_and_offers": true,
    "country": "Sri Lanka",
    "country_code": "LK",
    "first_name": "Thevindu",
    "last_name": "Rathnaweera",
    "address_line_1": "60 A , Sunandha Road",
    "address_line_2": "",
    "city": "Matara",
    "postal_code": "81000",
    "phone": "0714337912"
  }
}
```

Product names and size values are never hardcoded. The script uses whatever available products the live search results return.

## Locator Choices

The locators avoid copied absolute XPath. They use stable CSS selectors, semantic attributes, form attributes, autocomplete attributes, button text, and short relative XPath only where text matching is useful.

Examples:

- `input[name='email']`
- `input[autocomplete='shipping given-name']`
- `select[name='countryCode']`
- `form[action*='/cart/add'] button[type='submit']`
- relative XPath for visible button text such as Add to cart, Checkout, and Continue

Search result links are selected from product URLs (`a[href*='/products/']`) so the script still works if product card text or images change.

## Waiting Strategy

The code uses `WebDriverWait` and custom wait helpers instead of fixed sleeps. It waits for:

- document readiness
- search results
- product title
- enabled Add to cart button
- Shopify `/cart.js` item count changes
- checkout page loading
- checkout fields after country selection

High-level actions are retried on timeouts to handle normal live Shopify delays without hiding real assertion failures.

## Size Selection

The product page object reads available variant controls and selects the first enabled option. It supports:

- native dropdowns
- radio inputs
- visible buttons or labels

If a product has no size selector, the script continues as a one-size/no-size product.

## Verification

Task A prints PASS/FAIL for:

- cart contains exactly 2 items
- product names in the cart match the products added
- each product is visible on the cart page
- each item's price can be read
- cart subtotal equals the sum of the item prices
- subtotal/total is visible on the cart page

Task B prints PASS/FAIL for:

- selected country
- optional email/news/offers checkbox when present
- every configured checkout field value
- payment section not submitted
- stopped before payment

The script does not enter card details and does not click Pay now or complete an order.

## Logs And Screenshots

Each run creates a log file:

```text
logs/run_YYYYMMDD_HHMMSS.log
```

Screenshots are saved under:

```text
screenshots/YYYYMMDD_HHMMSS/
```

Screenshots are captured for assertion failures, timeout retries, fatal errors, and checkout captcha/challenge detection.

## Captcha Handling

The script does not bypass captcha or human verification. If a checkout captcha/challenge appears, it captures a screenshot, prints a clear FAIL message, logs the event, and stops Task B safely.

## Unexpected Behavior

Because this is a live Shopify store, product availability, product sizes, checkout layout, prices, and popups can change. The code avoids hardcoded product names and size values for that reason.

During checkout the site can show an add-on popup with a Continue button before the Shopify checkout page. The script handles that popup by waiting for a genuinely visible and clickable Continue control.
