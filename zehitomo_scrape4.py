import csv
import json

from playwright.sync_api import sync_playwright

import zehitomo_link3 as z

APPLY_LIST_SEL = "ul[data-test-id='apply-list'] li"
PRO_NAME_SEL = "[class*='header-pro-name']"
NAME_GROUP_SEL = "[class*='avatar-icon-name-group']"
LOCATION_SEL = "p[class*='ProProfileHeader-module__location']"
CSV_FILE = "contractors.csv"


def load_request_urls(path=z.SCRAPE_URLS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            urls = json.load(f)
    except FileNotFoundError:
        return []
    return [u for u in urls if "/request/" in u and "/apply/" not in u]


def get_text(page, selector):
    locator = page.locator(selector).first
    if locator.count():
        return locator.inner_text().strip()
    return ""


def scrape_contractors(page, url):
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_selector(APPLY_LIST_SEL, timeout=20000)
    page.wait_for_timeout(2000)

    total = page.locator(APPLY_LIST_SEL).count()
    print(f"  {total} contractors on {url}")
    rows = []

    for index in range(total):
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(APPLY_LIST_SEL, timeout=20000)
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

    return rows


def write_csv(rows, path=CSV_FILE):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "location"])
        writer.writerows(rows)


def main():
    urls = load_request_urls()
    print(f"Loaded {len(urls)} request url(s) from {z.SCRAPE_URLS_FILE}")

    with sync_playwright() as p:
        context = z.launch_browser(p)
        page = z.get_page(context)

        rows = []
        for url in urls:
            rows.extend(scrape_contractors(page, url))

        write_csv(rows)
        print(f"Saved {len(rows)} contractors -> {CSV_FILE}")

        context.close()


if __name__ == "__main__":
    main()
