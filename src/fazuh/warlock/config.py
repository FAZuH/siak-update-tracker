import os
from typing import Self

from dotenv import load_dotenv
from loguru import logger
import requests


class Config:
    _instance: Self | None = None

    def load(self):
        """Load environment variables

        The priority is .env file > environment variables
        See .env-example for the required variables
        """
        load_dotenv()
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")
        if username is None or password is None:
            logger.error("Error: USERNAME and PASSWORD environment variables are not set.")
            return

        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url is None or not self._is_webhook_valid(webhook_url):
            logger.error("Error: invalid WEBHOOK_URL.")
            return

        self.username = username
        self.password = password
        self.interval = int(os.getenv("INTERVAL", 60))
        self.webhook_url = webhook_url

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    @staticmethod
    def _is_webhook_valid(url: str) -> bool:
        try:
            resp = requests.head(url, timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False
