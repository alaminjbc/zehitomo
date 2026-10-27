import json
import time

from playwright.sync_api import sync_playwright

BASE_URL = "https://www.zehitomo.com"
USER_DATA_DIR = "zehitomo-profile"
SECTIONS_FILE = "sections.json"
OPTIONS_FILE = "options.json"

POSTAL_CODES = ["182-0004"]

CTA_SEL = "button[class*='RequestFormCTA_button']"
MODAL_SEL = "[data-test-id='request-form-modal']"
ENTRY_TITLE_SEL = "[class*='RequestFormEntry_title']"
ENTRY_BUTTON_TEXT_SEL = "[class*='form-entry-button-text']"
ADDRESS_INPUT_SEL = "#map-search-box-search-input"
SUBMIT_SEL = "button[data-test-id='request-submit']"
NEXT_SEL = "button[data-test-id^='request-next']"
BACK_SEL = "button:has-text('戻る')"
EXISTING_REQUEST_SEL = "button[data-test-id='go-to-existing-request']"
WAIT_AFTER_ADDRESS_MS = 60 * 1000


def launch_browser(playwright):
    return playwright.chromium.launch_persistent_context(
        USER_DATA_DIR,
        channel="chrome",
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )


def get_page(context):
    return context.pages[0] if context.pages else context.new_page()


def load_targets(path=SECTIONS_FILE):
    with open(path, encoding="utf-8") as f:
        sections = json.load(f)

    targets = []
    for category in sections.values():
        for section in category.get("sections", []):
            for service in section.get("services", []):
                targets.append((service["name"], service["url"]))
    return targets


def load_options(path=OPTIONS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_options(data, path=OPTIONS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def open_form(page, url):
    page.goto(f"{BASE_URL}{url}", wait_until="domcontentloaded")

    modal = page.locator(MODAL_SEL)
    if not modal.count():
        cta = page.locator(CTA_SEL)
        cta.first.scroll_into_view_if_needed()
        cta.first.click()

    page.wait_for_selector(MODAL_SEL, timeout=20000)
    page.wait_for_timeout(1000)
    return page.locator(MODAL_SEL)


def get_heading(root):
    for selector in (ENTRY_TITLE_SEL, "h2"):
        locator = root.locator(selector)
        if locator.count():
            text = locator.first.inner_text().strip()
            if text:
                return text
    return ""


def get_radio_options(root):
    options = []
    for radio in root.locator("input[type='radio']").all():
        options.append(radio.locator("xpath=ancestor::label").inner_text().strip())
    return options


def get_checkbox_options(root):
    options = []
    for checkbox in root.locator("input[type='checkbox']").all():
        options.append(checkbox.locator("xpath=parent::*//label").inner_text().strip())
    return options


def get_entry_button_options(root):
    options = []
    for text in root.locator(ENTRY_BUTTON_TEXT_SEL).all():
        options.append(text.inner_text().strip())
    return options


def get_page_options(root):
    return (
        get_radio_options(root)
        + get_checkbox_options(root)
        + get_entry_button_options(root)
    )


def get_next_button(root):
    buttons = root.locator(NEXT_SEL)
    if buttons.count():
        return buttons.last
    return None


def choose_option(root, option):
    for selector, label_selector in (
        ("input[type='radio']", "xpath=ancestor::label"),
        ("input[type='checkbox']", "xpath=parent::*//label"),
    ):
        for control in root.locator(selector).all():
            label = control.locator(label_selector)
            if label.inner_text().strip() == option:
                label.click()
                return "option"

    for text in root.locator(ENTRY_BUTTON_TEXT_SEL).all():
        if text.inner_text().strip() == option:
            text.locator("xpath=ancestor::button").first.click()
            return "button"

    return None


def is_email_step(root):
    return root.locator("button[data-test-id='request-email-step']").count() > 0


def is_address_step(root):
    field = root.locator(ADDRESS_INPUT_SEL)
    return field.count() > 0 and field.first.is_visible()


def advance_form(root, page):
    next_button = get_next_button(root)
    if next_button is not None and not next_button.is_disabled():
        next_button.click()
        page.wait_for_timeout(900)
        return True
    return False


def back(root, page):
    button = root.locator(BACK_SEL).last
    if button.count():
        button.click()
        page.wait_for_timeout(900)
        return True
    return False


def wait_for_existing_request(page, timeout_ms):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        button = page.locator(EXISTING_REQUEST_SEL)
        if button.count():
            return button.first
        page.wait_for_timeout(1000)
    return None


def fill_address(root, page, postal_code):
    field = root.locator(ADDRESS_INPUT_SEL)
    field.click()
    field.press_sequentially(postal_code, delay=60)
    page.wait_for_timeout(2000)

    submit = root.locator(SUBMIT_SEL)
    if not (submit.count() and not submit.first.is_disabled()):
        return False

    submit.first.click()
    existing = wait_for_existing_request(page, WAIT_AFTER_ADDRESS_MS)
    if existing is not None:
        existing.click()
    page.wait_for_timeout(WAIT_AFTER_ADDRESS_MS)
    return True


def save_combination(data, name, trail):
    save_options(data)
    print(f"Saved combination: {name} > {trail or '(root)'}")


def walk(root, page, data, node, name, trail, depth=0):
    if depth > 20 or is_email_step(root):
        return

    options = get_page_options(root)

    if options:
        heading = get_heading(root)
        heading_data = node.setdefault(heading, {})
        for option in options:
            child = heading_data.setdefault(option, {})
            kind = choose_option(root, option)
            if kind is None:
                continue
            if kind != "button" and not advance_form(root, page):
                continue
            next_trail = f"{trail} > {option}" if trail else option
            walk(root, page, data, child, name, next_trail, depth + 1)
            back(root, page)
        save_combination(data, name, trail)
        return

    if is_address_step(root):
        heading = get_heading(root)
        heading_data = node.setdefault(heading, {})
        for code in POSTAL_CODES:
            heading_data.setdefault(code, {})
            if not fill_address(root, page, code):
                break
            back(root, page)
        address_trail = f"{trail} > {heading}" if trail else heading
        save_combination(data, name, address_trail)
        return

    if advance_form(root, page):
        walk(root, page, data, node, name, trail, depth + 1)
        back(root, page)
    else:
        save_combination(data, name, trail)


def explore_target(page, name, url, data):
    root = open_form(page, url)
    tree = data.setdefault(name, {})
    walk(root, page, data, tree, name, "", 0)


def main():
    targets = load_targets()
    print(f"Loaded {len(targets)} services from {SECTIONS_FILE}")

    with sync_playwright() as p:
        context = launch_browser(p)
        page = get_page(context)

        data = load_options()
        for index, (name, url) in enumerate(targets, start=1):
            print(f"Exploring {index}/{len(targets)}: {name} ({url})")
            explore_target(page, name, url, data)
            save_options(data)
        print(f"Saved option trees -> {OPTIONS_FILE}")

        context.close()


if __name__ == "__main__":
    main()
