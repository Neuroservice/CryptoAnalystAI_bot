import logging

from playwright.async_api import async_playwright

browser = None
context = None


async def init_browser():
    """
    Инициализирует браузер Playwright один раз.
    """
    global browser, context
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--blink-settings=imagesEnabled=false",
        ]
    )
    context = await browser.new_context()
    logging.info("✅ Браузер Playwright инициализирован.")


async def close_browser():
    """
    Закрывает браузер при завершении работы бота.
    """
    global browser
    if browser:
        await browser.close()
        logging.info("🛑 Браузер Playwright закрыт.")