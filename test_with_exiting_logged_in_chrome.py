"""
Zehitomo contractor scraper using Browser Use + Google Gemini.

Requirements:
    Python 3.11+
    pip install -U browser-use playwright python-dotenv
    playwright install chromium --with-deps --no-shell

Create a .env file:
    GOOGLE_API_KEY=your_google_gemini_api_key

Run:
    python zehitomo_scraper.py
"""

import asyncio
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from browser_use import Agent, Browser, ChatGoogle, Tools, ActionResult

load_dotenv()

CHROME_PROFILE_DIRECTORY = os.getenv("CHROME_PROFILE_DIRECTORY", "Default")

START_URL = "https://www.zehitomo.com/"
SERVICE_URL = "https://www.zehitomo.com/service-list"
AIRCON_URL = (
    "https://www.zehitomo.com/home/cleaning/"
    "electronics-cleaning/air-conditioner-cleaner"
)

POSTAL_CODE = "182-0004"
SERVICE_NAME = "エアコンクリーニング"
OUTPUT_FILE = "zehitomo_contractors.json"

MAX_STEPS = 250


class Contractor(BaseModel):
    contractor_name: str = Field(
        description=(
            "Contractor or company name shown at the top of the chat box."
        )
    )
    location: str = Field(
        description=(
            "Location name shown in the contractor details/map area."
        )
    )
    phone_number: str = Field(
        default="",
        description=(
            "Phone number found in the chat messages. "
            "Use an empty string if not present."
        ),
    )
    email: str = Field(
        default="",
        description=(
            "Email address found in the chat messages. "
            "Use an empty string if not present."
        ),
    )


class ScrapingResult(BaseModel):
    postal_code: str = Field(description="Postal code used for the search.")
    service: str = Field(description="Zehitomo service name.")
    contractors: list[Contractor] = Field(
        description="All contractors found for the selected postal code."
    )


tools = Tools()


@tools.action(
    "Wait for the user to manually complete login on Zehitomo, then continue."
)
async def wait_for_manual_login() -> ActionResult:
    input(
        "\n" + "=" * 70 + "\n"
        "A Chrome window has opened.\n"
        "1. Click 「ログイン」 in Zehitomo.\n"
        "2. Complete the login manually.\n"
        "3. After you are logged in, return here and press ENTER.\n"
        "=" * 70 + "\n"
    )
    return ActionResult(extracted_content="Manual login completed.")


@tools.action(
    "Wait for 60 seconds before scraping the contractor list."
)
async def wait_one_minute() -> ActionResult:
    print("Waiting 60 seconds for the contractor page to load...")
    await asyncio.sleep(60)
    return ActionResult(extracted_content="Finished waiting 60 seconds.")


@tools.action(
    "Extract phone number and email from the currently open Zehitomo chat page. "
    "The agent should identify contractor name and location from the visible UI."
)
async def extract_current_contractor(browser_session) -> ActionResult:
    page = await browser_session.get_current_page()
    text = await page.inner_text("body")

    email = ""
    phone = ""

    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )
    if email_match:
        email = email_match.group(0)

    phone_match = re.search(
        r"(?<!\d)(?:0\d{1,4}[-−]\d{1,4}[-−]\d{3,4}|0\d{9,10})(?!\d)",
        text,
    )
    if phone_match:
        phone = phone_match.group(0).replace("−", "-")

    return ActionResult(
        extracted_content=json.dumps(
            {
                "phone_number": phone,
                "email": email,
                "page_text_preview": text[:3000],
            },
            ensure_ascii=False,
        )
    )


TASK = f"""
You are automating Zehitomo using a real visible Chrome browser.

Follow these steps exactly:

1. Go to {START_URL}.

2. Call the tool `wait_for_manual_login`.
   - The user will manually click 「ログイン」 and complete login.
   - Do NOT attempt to enter credentials.
   - Continue only after the user confirms login.

3. After login, reload {START_URL}.

4. In the navbar, click 「サービス一覧」 and go to {SERVICE_URL}.

5. On the service list, find and click 「{SERVICE_NAME}」.
   It should lead to:
   {AIRCON_URL}

6. On that page, click 「戸建タイプ」.

7. A modal will appear with radio-button questions, a progress bar,
   「次へ」, and 「戻る」.

   Repeat the following until a 「スキップ」 button appears:
   - Select the FIRST visible radio-button option.
   - Click 「次へ」.

8. Once 「スキップ」 appears, always click 「スキップ」.

9. In the next modal:
   - Enter `{POSTAL_CODE}` into the postal-code search field.
   - Click 「プロを見る」.

10. After clicking:
    - If both 「前回の依頼を確認する」 and 「新しく依頼を出す」 appear,
      click 「前回の依頼を確認する」.
    - Otherwise, continue with the page redirect.
    - Then call the tool `wait_one_minute`.

11. On the contractor results page, find the floating scrollable list
    on the left side containing contractor/company names.

12. For EVERY contractor in that list:
    - Click the contractor name once.
    - A chat box should open on the right.
    - The contractor/company name is at the top of the chat box.
    - Click that contractor name at the top of the chat box to open
      the details panel.
    - Extract the location name shown in the details/map area.
    - Return to the chat messages and extract any phone number and
      email address.
    - If a value is not present, use an empty string.
    - Call `extract_current_contractor` to help capture phone/email
      from the page text.
    - Close or navigate back from the details/chat view if needed.
    - Select the next contractor in the left-side list.

13. Do not invent data. Only extract values visibly shown in the UI.

14. When finished, return a structured result containing every contractor
    found for postal code `{POSTAL_CODE}` and service 「{SERVICE_NAME}」.
"""


async def run_scraper() -> None:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Add it to your .env file or environment."
        )

    llm = ChatGoogle(
        model="gemini-3.6-flash",
        api_key=api_key,
        temperature=0,
    )

    browser = Browser.from_system_chrome(
        profile_directory=CHROME_PROFILE_DIRECTORY,
        headless=False,
        keep_alive=True,
        window_size={"width": 1440, "height": 900},
    )

    agent = Agent(
        task=TASK,
        llm=llm,
        browser=browser,
        tools=tools,
        output_model_schema=ScrapingResult,
        max_actions_per_step=5,
        use_vision=True,
    )

    try:
        print("Starting Browser Use agent...")
        history = await agent.run(max_steps=MAX_STEPS)

        result = history.structured_output

        if result is None:
            final_result = history.final_result()

            if not final_result:
                raise RuntimeError(
                    "Gemini did not return a structured result. "
                    "Check whether the contractor list page was reached."
                )

            result = ScrapingResult.model_validate_json(final_result)

        data = result.model_dump(mode="json", exclude_none=True)

        output_path = Path(OUTPUT_FILE)
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("\n" + "=" * 70)
        print(f"Scraping completed.")
        print(f"Saved {len(data['contractors'])} contractors to: {output_path.resolve()}")
        print("=" * 70)
        print(json.dumps(data, ensure_ascii=False, indent=2))

    except Exception as e:
        print("\nScraping failed:")
        print(type(e).__name__, e)
        raise

    finally:
        print("\nClosing browser...")
        await browser.kill()


if __name__ == "__main__":
    asyncio.run(run_scraper())