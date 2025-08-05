import asyncio
import base64

from loguru import logger
from playwright.async_api import async_playwright
from playwright.async_api import Browser
from playwright.async_api import Page
import requests

from fazuh.warlock.config import Config
from fazuh.warlock.siak.path import Path


class Siak:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.config = Config()

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.config.headless)
        self.page = await self.browser.new_page()

    async def authenticate(self) -> bool:
        try:
            if await self.is_logged_in():
                return True  # Already logged in, no need to authenticate

            await self.page.goto(Path.AUTHENTICATION)
            # self.page.wait_for_load_state("networkidle")

            # Handle pre-login CAPTCHA page
            if await self.handle_captcha():
                return await self.authenticate()

            await self.page.wait_for_selector("input[name=u]", state="visible")
            # Proceed with standard login
            await self.page.fill("input[name=u]", self.username)
            await self.page.fill("input[name=p]", self.password)
            await self.page.click("input[type=submit]")
            await self.page.wait_for_load_state("networkidle")

            # Handle post-login CAPTCHA page (possible)
            if await self.handle_captcha():
                return await self.authenticate()

        except Exception as e:
            logger.error(f"An unexpected error occurred during authentication: {e}")
            return False

        if await self.is_rejected_page():
            logger.error("Authentication failed. The requested URL was rejected.")
            return False

        if not await self.is_cookie_exists():
            logger.error(
                "Initial authentication failed. Please check your credentials or CAPTCHA solution."
            )
            return False
        else:
            logger.success(f"Successful login. Obtained cookie: {await self.get_cookie()}")

        if await self.is_high_load_page():
            logger.error("Server is under high load.")
            return False

        if await self.is_inaccessible_page():
            logger.error("The page is currently inaccessible.")
            return False

        logger.info("Authentication successful.")
        return True

    async def handle_captcha(self) -> bool:
        """Extracts CAPTCHA, notifies admin, and gets solution from CLI."""
        if not await self.is_captcha_page():
            return False

        try:
            image_element = await self.page.query_selector('img[src*="data:image/png;base64,"]')
            if not image_element:
                raise ValueError("CAPTCHA image element not found.")

            image_src = await image_element.get_attribute("src")
            if not image_src or "base64," not in image_src:
                raise ValueError("Could not extract CAPTCHA image source.")

            base64_data = image_src.split(",", 1)[1]
            image_data = base64.b64decode(base64_data)

            if self.config.auth_discord_webhook_url:
                await self._notify_admin_for_captcha(image_data)

            captcha_solution = await asyncio.to_thread(
                input, "Please enter the CAPTCHA code from the image: "
            )

            await self.page.fill("input[name=answer]", captcha_solution)
            await self.page.click("button#jar")

            await self.page.wait_for_load_state("networkidle")

        except Exception as e:
            logger.error(f"Failed to handle CAPTCHA: {e}")
            raise

        return True

    async def _notify_admin_for_captcha(self, image_data: bytes):
        """Sends the CAPTCHA image to the admin webhook."""
        if not self.config.auth_discord_webhook_url:
            return

        message = "CAPTCHA detected. Please provide the solution."
        if self.config.user_id:
            message = f"<@{self.config.user_id}> {message}"

        try:
            files = {"file": ("captcha.png", image_data, "image/png")}
            data = {"username": "Warlock Auth", "content": message}
            response = await asyncio.to_thread(
                requests.post,
                self.config.auth_discord_webhook_url,
                data=data,
                files=files,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Admin notified about CAPTCHA and image sent.")
        except requests.RequestException as e:
            logger.error(f"Failed to notify admin via webhook: {e}")

    async def is_cookie_exists(self) -> bool:
        """Check if the user is logged in by looking for the session cookie."""
        cookies = await self.page.context.cookies()
        return "siakng_cc" in [cookie["name"] for cookie in cookies]

    async def get_cookie(self) -> str:
        cookies = await self.page.context.cookies()
        for cookie in cookies:
            if cookie["name"] == "siakng_cc":
                return cookie["value"]
        return ""

    async def is_logged_in(self) -> bool:
        """Check if the user is logged in by visiting a known page."""
        await self.page.goto(Path.WELCOME)
        # If we are on the CAPTCHA or Login page, we are not logged in.
        if await self.is_captcha_page():
            return False
        if self.page.url == Path.AUTHENTICATION:
            return False
        return True

    async def is_captcha_page(self) -> bool:
        """Check if the current page is a CAPTCHA page."""
        content = await self.page.content()
        return "This question is for testing whether you are a human visitor" in content

    async def is_rejected_page(self) -> bool:
        """Check if the current page is a rejected URL page."""
        content = await self.page.content()
        return "The requested URL was rejected" in content

    async def is_high_load_page(self) -> bool:
        """Check if the current page indicates high server load."""
        # Maaf, server SIAKNG sedang mengalami load tinggi dan belum dapat melayani request Anda saat ini.
        # Silahkan mencoba beberapa saat lagi.
        content = await self.page.content()
        return "Silahkan mencoba beberapa saat lagi." in content

    async def is_inaccessible_page(self) -> bool:
        """Check if the current page is inaccessible."""
        content = await self.page.content()
        return "Silakan mencoba beberapa saat lagi." in content

    async def close(self):
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
