from playwright.sync_api import sync_playwright
import time

def take_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        # Wait until the page has loaded completely
        page.goto("http://localhost:8501", wait_until="networkidle")
        # Streamlit pages might load content dynamically, so we wait extra
        time.sleep(5)
        # We can also wait for a specific element that shows the title or data
        page.screenshot(path="assets/dashboard.png")
        browser.close()

if __name__ == "__main__":
    take_screenshot()
