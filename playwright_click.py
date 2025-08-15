# Optional helper: click the "Скачать учебный план" button rendered by JS.
import asyncio, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent
PLANS = BASE_DIR / "plans"
PLANS.mkdir(exist_ok=True, parents=True)

TARGETS = [
    ("ai","https://abit.itmo.ru/program/master/ai"),
    ("ai_product","https://abit.itmo.ru/program/master/ai_product"),
]

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(accept_downloads=True)
        page = await ctx.new_page()
        for slug, url in TARGETS:
            await page.goto(url, wait_until="domcontentloaded")
            # Look for a link or button containing "Учебный план"
            btn = await page.get_by_text("Скачать учебный план").first
            if await btn.is_visible():
                with page.expect_download() as dl_info:
                    await btn.click()
                dl = await dl_info.value
                fname = PLANS / f"{slug}_{dl.suggested_filename}"
                await dl.save_as(str(fname))
                print("Downloaded:", fname)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
