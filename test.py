import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on('pageerror', lambda err: print('ERROR:', err))
        await page.goto('file:///C:/Users/james/Documents/Projects/change-ringing/docs/invention.html')
        await page.wait_for_timeout(1000)
        
        count = await page.evaluate('document.querySelectorAll(".comp-card").length')
        print(f'Rendered {count} composition cards')
        
        await browser.close()

asyncio.run(run())
