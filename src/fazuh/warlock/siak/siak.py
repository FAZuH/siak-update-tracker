import asyncio
import base64

from loguru import logger
from playwright.async_api import async_playwright
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

        match self.config.browser:
            case "chromium":
                browser = self.playwright.chromium
            case "firefox":
                browser = self.playwright.firefox
            case "webkit":
                browser = self.playwright.webkit
            case _:
                logger.error(f"Unsupported browser: {self.config.browser}. Defaulting to Chromium.")
                browser = self.playwright.chromium

        self.browser = await browser.launch(headless=self.config.headless)
        self.page = await self.browser.new_page()

    async def authenticate(self) -> bool:
        if not self.is_logged_in(await self.content):
            try:
                if self.page.url != Path.AUTHENTICATION:
                    await self.page.goto(Path.AUTHENTICATION)

                # Handle pre-login CAPTCHA page
                if await self.handle_captcha(await self.content):
                    return await self.authenticate()

                await self.page.wait_for_selector("input[name=u]", state="visible")
                # Proceed with standard login
                await self.page.fill("input[name=u]", self.username)
                await self.page.fill("input[name=p]", self.password)
                await self.page.click("input[type=submit]")
                await self.page.wait_for_load_state()

                # Handle post-login CAPTCHA page (sometimes appears after login)
                if await self.handle_captcha(await self.content):
                    return await self.authenticate()

            except Exception as e:
                logger.error(f"An unexpected error occurred during authentication: {e}")
                return False

        # When auth is too fast, the browser might not have the chance to change role
        await self.page.wait_for_load_state("networkidle")
        if not self.is_role_selected(await self.content):
            logger.info("No role selected. Navigating to change role page.")
            await self.page.goto(Path.CHANGE_ROLE)

        logger.success("Authentication successful.")
        return True

    async def handle_captcha(self, content: str) -> bool:
        """Extracts CAPTCHA, notifies admin, and gets solution from CLI."""
        if not self.is_captcha_page(content):
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
            await self.page.wait_for_load_state()

        except Exception as e:
            logger.error(f"Failed to handle CAPTCHA: {e}")
            raise

        return True

    def is_logged_in(self, content: str) -> bool:
        """Check if the user is logged in."""
        return "Logout Counter" in content

    def is_role_selected(self, content: str) -> bool:
        """Check if a role is selected."""
        return "No role selected" not in content

    def is_captcha_page(self, content: str) -> bool:
        """Check if the current page is a CAPTCHA page."""
        keywords = [
            "This question is for testing whether you are a human visitor",
            "What code is in the image?",
            "You have entered an invalid answer",
        ]
        return any(keyword in content for keyword in keywords)

    async def close(self):
        if hasattr(self, "browser"):
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()

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

    @property
    async def content(self) -> str:
        """Get the current page content."""
        return await self.page.content()
