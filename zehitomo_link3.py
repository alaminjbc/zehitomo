import csv
import json
import os
import time

from playwright.sync_api import sync_playwright

BASE_URL = "https://www.zehitomo.com"
USER_DATA_DIR = "zehitomo-profile"
SECTIONS_FILE = "sections.json"
OPTIONS_FILE = "options.json"
SCRAPE_URLS_FILE = "scrape_urls.json"

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
WAIT_AFTER_ADDRESS_MS = 6* 1000

APPLY_LIST_SEL = "ul[data-test-id='apply-list'] li"
PRO_NAME_SEL = "[class*='header-pro-name']"
NAME_GROUP_SEL = "[class*='avatar-icon-name-group']"
LOCATION_SEL = "p[class*='ProProfileHeader-module__location']"
CSV_FILE = "contractors.csv"


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


def load_urls(path=SCRAPE_URLS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_urls(urls, path=SCRAPE_URLS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)


def save_url(page, path=SCRAPE_URLS_FILE): # url ta save korbo ekta json file e 
    urls = load_urls(path)
    if page.url not in urls:
        urls.append(page.url)
    save_urls(urls, path)
    print(f"Saved scraping url: {page.url}")


def ensure_files():
    if not os.path.exists(OPTIONS_FILE):
        save_options({})
    if not os.path.exists(SCRAPE_URLS_FILE):
        save_urls([])


def get_text(page, selector):
    locator = page.locator(selector).first
    if locator.count():
        return locator.inner_text().strip()
    return ""


def scrape_contractors(page):
    url = page.url
    try:
        page.wait_for_selector(APPLY_LIST_SEL, timeout=60000)
    except Exception:
        print(f"  no contractor list on {url}")
        return []
    page.wait_for_timeout(1500)

    total = page.locator(APPLY_LIST_SEL).count()
    print(f"  {total} contractors on {url}")
    rows = []

    for index in range(total):
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(APPLY_LIST_SEL, timeout=60000)
        page.wait_for_timeout(1500)

        item = page.locator(APPLY_LIST_SEL).nth(index)
        item.scroll_into_view_if_needed()
        item.click()

        try:
            page.wait_for_selector(PRO_NAME_SEL, timeout=12000)
        except Exception:
            print(f"    {index + 1}/{total}: no profile, skipped")
            continue

        name = get_text(page, PRO_NAME_SEL)

        group = page.locator(NAME_GROUP_SEL).first
        if group.count():
            group.click()
            try:
                page.wait_for_selector(LOCATION_SEL, timeout=10000)
            except Exception:
                pass

        location = get_text(page, LOCATION_SEL)
        rows.append((name, location))
        print(f"    {index + 1}/{total}: {name} | {location}")

    page.goto(url, wait_until="domcontentloaded")
    return rows


def append_csv(rows, path=CSV_FILE):
    if not rows:
        return
    if os.path.exists(path):
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    else:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "location"])
            writer.writerows(rows)


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
    page.go_back()
    page.wait_for_timeout(2000)
    return True


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
    existing = wait_for_existing_request(page, WAIT_AFTER_ADDRESS_MS) # exsting button cole ashle oikhane click kore jabo
    if existing is not None:
        existing.click()
    
    page.wait_for_timeout(WAIT_AFTER_ADDRESS_MS) # 1 min wait korlam
    save_url(page)
    append_csv(scrape_contractors(page)) # Scraping page e gelam
    return True


def save_combination(data, name, trail):
    save_options(data)
    save_urls(load_urls())
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
    ensure_files()
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
