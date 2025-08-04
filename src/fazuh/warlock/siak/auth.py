from loguru import logger
from playwright.sync_api import Browser
from playwright.sync_api import Page
from playwright.sync_api import sync_playwright
import requests

from fazuh.warlock.config import Config
from fazuh.warlock.siak.path import Path


class Auth:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.playwright = sync_playwright().start()
        self.browser: Browser = self.playwright.firefox.launch(headless=False)
        self.page: Page = self.browser.new_page()
        self.config = Config()

    def authenticate(self) -> bool:
        try:
            self.page.goto(Path.AUTHENTICATION)
            self.page.wait_for_selector("input[name=u]", state="visible")
            self.page.fill("input[name=u]", self.username)
            self.page.fill("input[name=p]", self.password)
            self.page.click("input[type=submit]")
            self.page.wait_for_load_state("networkidle")
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            # Check for CAPTCHA
            if "What code is in the image?" in self.page.content():
                logger.warning(
                    "JavaScript CAPTCHA detected. Please solve it in the browser window."
                )
                if self.config.admin_webhook_url:
                    self._notify_admin_for_captcha()
                logger.info("The script will resume automatically after you log in.")
                try:
                    # Wait for successful login, which should set the session cookie.
                    self.page.wait_for_function(
                        "() => document.cookie.includes('siakng_cc')", timeout=300_000
                    )  # 5 minutes timeout
                except Exception:
                    logger.error("CAPTCHA was not solved in time. Authentication failed.")
                    return False
            else:
                logger.error(f"An unexpected error occurred during authentication: {e}")
                return False

        if not self.is_logged_in():
            logger.error("Error: Authentication failed. Please check your credentials.")
            return False

        if not self.change_role():
            logger.error(
                "Error: Authentication succeeded but role change failed. Is the website down?"
            )
            return False

        logger.info("Authentication successful.")
        return True

    def _notify_admin_for_captcha(self):
        if not self.config.admin_webhook_url:
            return

        message = "JavaScript CAPTCHA detected. Please solve it in the browser window."
        if self.config.admin_user_id:
            message = f"<@{self.config.admin_user_id}> {message}"

        try:
            requests.post(
                self.config.admin_webhook_url,
                json={"content": message},
                timeout=5,
            )
            logger.info("Admin notified about CAPTCHA.")
        except requests.RequestException as e:
            logger.error(f"Failed to notify admin: {e}")

    def change_role(self) -> bool:
        try:
            self.page.goto(Path.CHANGE_ROLE)
            self.page.wait_for_url(Path.WELCOME)
        except Exception as e:
            logger.error(f"Error changing role: {e}")
            return False

        if self.page.url == Path.WELCOME:
            logger.info("Role changed successfully.")
            return True
        else:
            logger.error("Error: Role change failed.")
            return False

    def is_logged_in(self) -> bool:
        return "siakng_cc" in [cookie["name"] for cookie in self.page.context.cookies()]

    def close(self):
        self.browser.close()
        self.playwright.stop()
