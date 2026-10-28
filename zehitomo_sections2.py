import json

from playwright.sync_api import sync_playwright

SIGN_IN_URL = "https://www.zehitomo.com/sign-in"
ACCOUNT_URL_GLOB = "**/account/client-edit*"
HOME_URL = "https://www.zehitomo.com/"
SERVICE_LIST_LINK = "a[href='/service-list']"
USER_DATA_DIR = "zehitomo-profile"
SECTIONS_FILE = "sections.json"
LOGIN_TIMEOUT_MS = 5 * 60 * 1000
SECTIONS_TIMEOUT_MS = 30 * 1000

CATEGORY_CARD_SEL = "h3[data-cy='category-card']"

EXTRACT_SECTIONS_JS = """
() => {
    const nodes = document.querySelectorAll(
        'h3[data-cy="category-card"], section[class*="section-c2__"], section[class*="section-c3__"]'
    );
    const marks = [];
    for (const el of nodes) {
        let kind;
        if (el.matches('h3[data-cy="category-card"]')) {
            kind = 'category';
        } else if (el.matches('section[class*="section-c2__"]')) {
            kind = 'section';
        } else {
            kind = 'service';
        }
        const link = el.closest('a');
        marks.push({
            kind: kind,
            name: el.textContent.trim(),
            url: link ? link.getAttribute('href') : null,
        });
    }
    return marks;
}
"""


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


def login_with_google(page):
    page.goto(SIGN_IN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    if "sign-in" not in page.url:
        print(f"Already logged in -> {page.url}")
        return
    print("Log in manually with Google in the browser window...")
    page.wait_for_url(ACCOUNT_URL_GLOB, timeout=LOGIN_TIMEOUT_MS)
    print(f"Logged in -> {page.url}")


def open_home(page):
    page.goto(HOME_URL, wait_until="domcontentloaded")


def open_service_list(page):
    page.locator(SERVICE_LIST_LINK).click()
    page.wait_for_load_state("domcontentloaded")


def wait_for_sections(page):
    page.locator(CATEGORY_CARD_SEL).first.wait_for(
        state="visible", timeout=SECTIONS_TIMEOUT_MS
    )


def save_sections(data, path=SECTIONS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scrape_sections(page, path=SECTIONS_FILE):
    marks = page.evaluate(EXTRACT_SECTIONS_JS)

    tree = {}
    category = None
    section = None
    for mark in marks:
        kind = mark["kind"]
        if kind == "category":
            if category is not None:
                save_sections(tree, path)
                print(f"Saved {category}: {len(tree[category]['sections'])} sections")
            category = mark["name"]
            tree[category] = {"url": mark["url"], "sections": []}
            section = None
        elif kind == "section" and category is not None:
            section = {"name": mark["name"], "url": mark["url"], "services": []}
            tree[category]["sections"].append(section)
        elif kind == "service" and section is not None:
            section["services"].append({"name": mark["name"], "url": mark["url"]})

    if category is not None:
        save_sections(tree, path)
        print(f"Saved {category}: {len(tree[category]['sections'])} sections")

    return tree


def main():
    with sync_playwright() as p:
        context = launch_browser(p)
        page = get_page(context)

        login_with_google(page)
        open_home(page)
        open_service_list(page)
        wait_for_sections(page)

        tree = scrape_sections(page)
        total_sections = sum(len(v["sections"]) for v in tree.values())
        total_services = sum(
            len(s["services"]) for v in tree.values() for s in v["sections"]
        )
        print(
            f"Found {len(tree)} categories, {total_sections} sections, "
            f"{total_services} services -> {SECTIONS_FILE}"
        )

        context.close()


if __name__ == "__main__":
    main()
