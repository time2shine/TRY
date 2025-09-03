import asyncio
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright
import time

URL = "https://www.distro.tv/live/shemaroo-bollywood/"
LOG_FILE = "m3u8_changes.log"

previous_link_file = "previous_link.txt"

async def get_m3u8():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        m3u8_links = set()

        def handle_request(request):
            url = request.url
            if ".m3u8" in url:
                if "f=" in url:
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    if "f" in params:
                        decoded = urllib.parse.unquote(params["f"][0])
                        if ".m3u8" in decoded:
                            m3u8_links.add(decoded)
                else:
                    m3u8_links.add(url)

        context.on("request", handle_request)
        await page.goto(URL)
        await page.wait_for_timeout(15000)
        await browser.close()

        if m3u8_links:
            link = list(m3u8_links)[0]
            clean_url = link.split(".m3u8")[0] + ".m3u8"
            return clean_url
        return None

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

async def monitor_once():
    # Load previous link from file
    try:
        with open(previous_link_file, "r") as f:
            previous_link = f.read().strip()
    except FileNotFoundError:
        previous_link = None

    current_link = await get_m3u8()
    if current_link:
        if previous_link is None:
            log_message(f"Initial link: {current_link}")
        elif current_link != previous_link:
            log_message(f"Link changed! New link: {current_link}")
        else:
            log_message("No change in link.")

        # Save current link for next run
        with open(previous_link_file, "w") as f:
            f.write(current_link)
    else:
        log_message("No link found this cycle.")

asyncio.run(monitor_once())
