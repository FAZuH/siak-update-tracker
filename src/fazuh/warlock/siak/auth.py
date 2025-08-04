import time

from loguru import logger
import requests

from .path import Path


class Auth:
    def __init__(self, session: requests.Session, username: str, password: str):
        self.session = session
        self.username = username
        self.password = password

    def authenticate(self) -> bool:
        try:
            resp = self.session.post(
                Path.AUTHENTICATION, data={"u": self.username, "p": self.password}
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during authentication: {e}")
            return False

        time.sleep(1)
        if self.is_logged_in() is False:
            logger.error("Error: Authentication failed. Please check your credentials.")
            return False

        time.sleep(1)
        if self.change_role() is False:
            logger.error(
                "Error: Authentication succeeded but role change failed. Is the website down?"
            )
            return False

        logger.info("Authentication successful.")
        return True

    def change_role(self) -> bool:
        try:
            resp = self.session.get(Path.CHANGE_ROLE)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error changing role: {e}")
            return False

        if resp.status_code == 200 and resp.url == Path.WELCOME:
            logger.info("Role changed successfully.")
            return True
        else:
            logger.error("Error: Role change failed.")
            return False

    def is_logged_in(self) -> bool:
        return "siakng_cc" in self.session.cookies
