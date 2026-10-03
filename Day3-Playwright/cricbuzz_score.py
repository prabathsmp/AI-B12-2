from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
SCORE_SELECTOR = 'a[href^="/live-cricket-scores/"] span[class~="font-medium"][class~="truncate"]'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    # Increase the viewport size to ensure the score is visible
    page = browser.new_page()
#     page = browser.new_page(
#     viewport={"width": 1280, "height": 720}
# )
    try:
        page.goto(
            "https://www.cricbuzz.com/"
            )
        #page.wait_for_load_state("networkidle")
        # page.wait_for_selector(SCORE_SELECTOR, timeout=15000)
        scores = page.locator(SCORE_SELECTOR)
        scores.first.wait_for(
            state="visible",
            timeout=15000
        )
        # score_element = scores.first
        # score_element.wait_for(
        #     state="visible",
        #     timeout=30000
        # )
        score = scores.first.inner_text().strip()
        if score:
            print("Score:")
            print(score)
        else:
            print("No live score available.")
    except PlaywrightTimeoutError:
        print("No live match/score found.")
        page.screenshot(
        path="debug.png",
        full_page=True
    )

        print("Current URL:", page.url)

        print("Page title:", page.title())

        print("Number of matching elements:", scores.count())

    except Exception as e:
        print(f"Error while retrieving score: {e}")
    finally:
        # Always take the screenshot
        page.screenshot(
            path="score.png",
            full_page=True
        )
    browser.close()