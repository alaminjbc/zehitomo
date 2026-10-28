from playwright.sync_api import sync_playwright

import zehitomo_link3 as z

MAX_STEPS = 20
TARGET_LIMIT = 1


def first_path(root, page):
    for _ in range(MAX_STEPS):
        if z.is_email_step(root):
            return

        options = z.get_page_options(root)
        if options:
            option = options[0]
            kind = z.choose_option(root, option)
            if kind is None:
                return
            if kind != "button" and not z.advance_form(root, page):
                return
            continue

        if z.is_address_step(root):
            z.fill_address(root, page, z.POSTAL_CODES[0])
            return

        if not z.advance_form(root, page):
            return


def main():
    targets = z.load_targets()[:TARGET_LIMIT]
    print(f"Loaded {len(targets)} service(s) from {z.SECTIONS_FILE}")

    with sync_playwright() as p:
        context = z.launch_browser(p)
        page = z.get_page(context)

        for index, (name, url) in enumerate(targets, start=1):
            print(f"[{index}/{len(targets)}] first combination: {name} ({url})")
            root = z.open_form(page, url)
            first_path(root, page)

        try:
            input("Done. Press Enter to close the browser...")
        except EOFError:
            pass
        context.close()


if __name__ == "__main__":
    main()
