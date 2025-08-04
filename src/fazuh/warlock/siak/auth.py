import base64

from loguru import logger
from playwright.sync_api import Browser
from playwright.sync_api import Page
from playwright.sync_api import sync_playwright
import requests

from fazuh.warlock.config import Config
from fazuh.warlock.siak.path import Path


class Auth:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.playwright = sync_playwright().start()
        self.browser: Browser = self.playwright.firefox.launch(headless=False)
        self.page: Page = self.browser.new_page()
        self.config = Config()

    def authenticate(self) -> bool:
        try:
            self.page.goto(Path.AUTHENTICATION)
            self.page.wait_for_load_state("networkidle")

            # Handle pre-login CAPTCHA page
            if self.handle_captcha():
                return self.authenticate()

            self.page.wait_for_selector("input[name=u]", state="visible")
            # Proceed with standard login
            self.page.fill("input[name=u]", self.username)
            self.page.fill("input[name=p]", self.password)
            self.page.click("input[type=submit]")
            self.page.wait_for_load_state("networkidle")

            if self.handle_captcha():
                return self.authenticate()

        except Exception as e:
            logger.error(f"An unexpected error occurred during authentication: {e}")
            return False

        if self.is_rejected_page():
            logger.error("Authentication failed. The requested URL was rejected.")
            return False

        if not self.is_initial_logged_in():
            logger.error(
                "Initial authentication failed. Please check your credentials or CAPTCHA solution."
            )
            return False

        logger.info("Authentication successful.")
        return True

    def handle_captcha(self) -> bool:
        """Extracts CAPTCHA, notifies admin, and gets solution from CLI."""
        if not self.is_captcha_page():
            return False

        try:
            image_element = self.page.query_selector('img[src*="data:image/png;base64,"]')
            if not image_element:
                raise ValueError("CAPTCHA image element not found.")

            image_src = image_element.get_attribute("src")
            if not image_src or "base64," not in image_src:
                raise ValueError("Could not extract CAPTCHA image source.")

            base64_data = image_src.split(",", 1)[1]
            image_data = base64.b64decode(base64_data)

            if self.config.admin_webhook_url:
                self._notify_admin_for_captcha(image_data)

            captcha_solution = input("Please enter the CAPTCHA code from the image: ")

            self.page.fill("input[name=answer]", captcha_solution)
            self.page.click("button#jar")

            self.page.wait_for_load_state("networkidle")

        except Exception as e:
            logger.error(f"Failed to handle CAPTCHA: {e}")
            raise

        return True

    def _notify_admin_for_captcha(self, image_data: bytes):
        """Sends the CAPTCHA image to the admin webhook."""
        if not self.config.admin_webhook_url:
            return

        message = "CAPTCHA detected. Please provide the solution."
        if self.config.admin_user_id:
            message = f"<@{self.config.admin_user_id}> {message}"

        try:
            files = {"file": ("captcha.png", image_data, "image/png")}
            data = {"content": message}
            response = requests.post(
                self.config.admin_webhook_url, data=data, files=files, timeout=10
            )
            response.raise_for_status()
            logger.info("Admin notified about CAPTCHA and image sent.")
        except requests.RequestException as e:
            logger.error(f"Failed to notify admin via webhook: {e}")

    def is_initial_logged_in(self) -> bool:
        """Check if the user is logged in by looking for the session cookie."""
        return "siakng_cc" in [cookie["name"] for cookie in self.page.context.cookies()]

    def is_logged_in(self) -> bool:
        """Check if the user is logged in by visiting a known page."""
        self.page.goto(Path.WELCOME)
        # If we are on the CAPTCHA or Login page, we are not logged in.
        if self.is_captcha_page():
            return False
        if self.page.url == Path.AUTHENTICATION:
            return False
        return True

    def is_captcha_page(self) -> bool:
        """Check if the current page is a CAPTCHA page."""
        return "This question is for testing whether you are a human visitor" in self.page.content()

    def is_rejected_page(self) -> bool:
        """Check if the current page is a rejected URL page."""
        return "The requested URL was rejected" in self.page.content()

    def close(self):
        self.browser.close()
        self.playwright.stop()
