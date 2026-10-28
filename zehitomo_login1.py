from playwright.sync_api import sync_playwright

SIGN_IN_URL = "https://www.zehitomo.com/sign-in"
ACCOUNT_URL_GLOB = "**/account/client-edit*"
HOME_URL = "https://www.zehitomo.com/"
SERVICE_LIST_LINK = "a[href='/service-list']"
USER_DATA_DIR = "zehitomo-profile"
LOGIN_TIMEOUT_MS = 5 * 60 * 1000
WAIT_AFTER_CLICK_MS = 60 * 10000


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
    print("Log in manually with Google in the browser window...")
    page.wait_for_url(ACCOUNT_URL_GLOB, timeout=LOGIN_TIMEOUT_MS)
    print(f"Logged in -> {page.url}")


def open_home(page):
    page.goto(HOME_URL, wait_until="domcontentloaded")


def open_service_list(page):
    page.locator(SERVICE_LIST_LINK).click()
    page.wait_for_load_state("domcontentloaded")


def wait_one_minute(page):
    print("Waited, holding for 1 minute...")
    page.wait_for_timeout(WAIT_AFTER_CLICK_MS)


def main():
    with sync_playwright() as p:
        context = launch_browser(p)
        page = get_page(context)

        login_with_google(page)
        open_home(page)
        open_service_list(page)
        wait_one_minute(page)

        context.close()


if __name__ == "__main__":
    main()
