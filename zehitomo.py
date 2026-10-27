import json

from playwright.sync_api import sync_playwright

HOME_URL = "https://www.zehitomo.com/"
JOB_TYPES_API = "https://api.zehitomo.com/api/job-types"
USER_DATA_DIR = "zehitomo-profile"
CATEGORY_FILE = "category.json"
OPTIONS_FILE = "options.json"

INPUT_SEL = "input#homeBannerJobTypeSearch"
OPTION_SEL = "ul#homeBannerJobTypeSearch-list li[role='option']"
SUBMIT_SEL = "button[data-test-id='start-new-request']"
MODAL_SEL = "[data-test-id='request-form-modal']"


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


def open_home(page):
    page.goto(HOME_URL, wait_until="domcontentloaded")


def fetch_categories(page):
    response = page.request.get(JOB_TYPES_API)
    if not response.ok:
        raise RuntimeError(f"Request failed: {response.status} {response.status_text}")

    names = []
    seen = set()
    for item in response.json():
        title = item.get("title") or {}
        name = title.get("ja") or title.get("en")
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def save_categories(names, path=CATEGORY_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=2)


def select_category(page, category):
    search = page.locator(INPUT_SEL)
    search.wait_for(state="visible")
    search.click()
    with page.expect_response(lambda r: "/job-types/search" in r.url):
        search.press_sequentially(category, delay=50)
    page.wait_for_timeout(500)
    page.locator(OPTION_SEL).first.click()


def open_request_form(page):
    page.locator(SUBMIT_SEL).click()
    modal = page.locator(MODAL_SEL)
    modal.wait_for(state="visible", timeout=15000)
    return modal


def get_heading(modal):
    return modal.locator("h2").first.inner_text().strip()


def get_radio_options(modal):
    options = []
    for radio in modal.locator("input[type='radio']").all():
        options.append(radio.locator("xpath=ancestor::label").inner_text().strip())
    return options


def get_checkbox_options(modal):
    options = []
    for checkbox in modal.locator("input[type='checkbox']").all():
        options.append(
            checkbox.locator("xpath=parent::*//label").inner_text().strip()
        )
    return options


def get_page_options(modal):
    return get_radio_options(modal) + get_checkbox_options(modal)


def extract_page(modal):
    return get_heading(modal), get_page_options(modal)


def get_next_button(modal):
    buttons = modal.locator("button[data-test-id^='request-next']")
    if buttons.count():
        return buttons.last
    return None


def choose_option(modal, option):
    for selector, label_selector in (
        ("input[type='radio']", "xpath=ancestor::label"),
        ("input[type='checkbox']", "xpath=parent::*//label"),
    ):
        for control in modal.locator(selector).all():
            label = control.locator(label_selector)
            if label.inner_text().strip() == option:
                label.click()
                return True
    return False


def fill_address(modal, page, postal_code="1500001"):
    field = modal.locator("input[type='text']").first
    field.click()
    field.press_sequentially(postal_code, delay=50)
    page.wait_for_timeout(1500)
    modal.locator("button[data-test-id='request-address-step']").click()


def wait_for_email_step(modal):
    modal.locator("button[data-test-id='request-email-step']").wait_for(
        state="visible", timeout=60000
    )


def is_email_step(modal):
    return modal.locator("button[data-test-id='request-email-step']").count() > 0


def save_options(data, path=OPTIONS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def advance_form(modal, page):
    next_button = get_next_button(modal)
    if next_button is not None and not next_button.is_disabled():
        next_button.click()
        page.wait_for_timeout(800)
        return True

    address_button = modal.locator("button[data-test-id='request-address-step']")
    if address_button.count():
        fill_address(modal, page)
        page.wait_for_timeout(1200)
        return True

    return False


def explore_category(page, category, data):
    pending_paths = [[]]
    while pending_paths:
        path = pending_paths.pop()
        open_home(page)
        select_category(page, category)
        modal = open_request_form(page)
        tree = data.setdefault(category, {})
        node = tree

        for previous_heading, selected_option in path:
            heading = get_heading(modal)
            options = get_page_options(modal)
            if heading != previous_heading or selected_option not in options:
                raise RuntimeError(
                    f"Form changed while exploring {category!r}: "
                    f"expected {previous_heading!r} / {selected_option!r}"
                )
            node = node.setdefault(heading, {}).setdefault(selected_option, {})
            if not choose_option(modal, selected_option):
                raise RuntimeError(
                    f"Could not select {selected_option!r} for {category!r}"
                )
            if not advance_form(modal, page):
                if not is_email_step(modal):
                    wait_for_email_step(modal)
                break

        if is_email_step(modal):
            continue

        heading = get_heading(modal)
        options = get_page_options(modal)
        if not options:
            continue

        heading_data = node.setdefault(heading, {})
        for option in options:
            heading_data.setdefault(option, {})

        print(f"{category}: {heading} ({len(options)} options)")
        for option in reversed(options):
            pending_paths.append(path + [(heading, option)])


def main():
    with sync_playwright() as p:
        context = launch_browser(p)
        page = get_page(context)

        open_home(page)
        categories = fetch_categories(page)
        print(f"Found {len(categories)} categories:")
        for name in categories:
            print(" -", name)
        save_categories(categories)
        print(f"Saved -> {CATEGORY_FILE}")

        data = {}
        for index, category in enumerate(categories, start=1):
            print(f"Exploring category {index}/{len(categories)}: {category}")
            explore_category(page, category, data)
            save_options(data)
        print(f"Saved category option trees -> {OPTIONS_FILE}")

        context.close()


if __name__ == "__main__":
    main()