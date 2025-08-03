from datetime import datetime
import difflib
import io
import os
from pathlib import Path
import time

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests


class Main:

    def __init__(self):
        self.login_url = "https://academic.ui.ac.id/main/Authentication/"
        self.change_role_url = "https://academic.ui.ac.id/main/Authentication/ChangeRole"
        self.tracked_page = "https://academic.ui.ac.id/main/Schedule/Index?period=2025-1&search="

        self.cache_file = Path("latest_courses.txt")
        self.prev_content = self.cache_file.read_text() if self.cache_file.exists() else ""

        self.session = requests.Session()

    def main(self):
        while True:
            self.load_env()
            if self.authenticate():
                self.run()
            print(f"Waiting for the next check in {self.interval} seconds...")
            time.sleep(self.interval)

    def load_env(self):
        """Load environment variables

        The priority is .env file > environment variables
        See .env-example for the required variables
        """
        load_dotenv()
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")
        self.interval = int(os.getenv("INTERVAL", 60))
        webhook_url = os.getenv("WEBHOOK_URL")

        if self.username is None or self.password is None:
            print("Error: USERNAME and PASSWORD environment variables are not set.")
            return

        if webhook_url is None or not self._is_webhook_valid(webhook_url):
            print("Error: invalid WEBHOOK_URL.")
            return

        self.webhook_url = webhook_url

    def authenticate(self) -> bool:
        try:
            resp = self.session.post(self.login_url, data={"u": self.username, "p": self.password})
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error during authentication: {e}")
            return False

        time.sleep(1)
        if self.is_logged_in() is False:
            print("Error: Authentication failed. Please check your credentials.")
            return False

        time.sleep(1)
        if self.change_role() is False:
            print("Error: Authentication succeeded but role change failed. Is the website down?")
            return False

        print("Authentication successful.")
        return True

    def change_role(self) -> bool:
        try:
            resp = self.session.get(self.change_role_url)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error changing role: {e}")
            return False

        if resp.status_code == 200 and resp.url == "https://academic.ui.ac.id/main/Welcome/":
            print("Role changed successfully.")
            return True
        else:
            print("Error: Role change failed.")
            return False

    def run(self):
        # 1. GET tracked page
        resp = self.session.get(self.tracked_page)
        if self._is_logged_in_url(resp) is False:
            print("Session expired or not logged in.")
            return

        # 2. Parse response
        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.find_all(class_=["sub", "border2", "pad2"])  # Mata kuliah
        courses: list[str] = []
        for e in elements:
            content = "".join(str(e) for e in e.contents)
            course = content.replace("<strong>", "").replace("</strong>", "").strip()
            courses.append(course)

        curr = "\n".join(courses)

        # 3. Compare with previous content
        if self.prev_content == curr:
            print("No updates detected.")
            return
        print("Update detected!")

        # compare using set
        old_courses = set(self.prev_content.splitlines()) if self.prev_content else set()
        new_courses = set(courses)
        added_courses = new_courses - old_courses
        removed_courses = old_courses - new_courses

        changes = []
        for course in added_courses:
            changes.append(f"Added: {course}")
        for course in removed_courses:
            changes.append(f"Removed: {course}")

        if not changes:
            print("No meaningful changes detected (only order changed).")
            return

        # 4. Create diff and send to webhook
        diff = "\n".join(changes)
        print(diff)
        self._to_webhook(self.webhook_url, diff)

        self.prev_content = curr
        self.cache_file.write_text(curr)

    def is_logged_in(self) -> bool:
        try:
            response = self.session.get(self.tracked_page)
            return response.status_code == 200 and self._is_logged_in_url(response)
        except requests.RequestException:
            return False

    def _is_logged_in_url(self, resp: requests.Response) -> bool:
        return resp.url != "https://academic.ui.ac.id/main/Authentication/"

    @staticmethod
    def _to_webhook(webhook_url: str, diff: str):
        message = "**Jadwal SIAK UI Berubah!**"

        # Create a file-like object from the diff string
        diff_file = io.BytesIO(diff.encode("utf-8"))

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"siak_schedule_diff_{timestamp}.txt"

        data = {
            "content": message,
            "username": "siak-update-tracker",
            "avatar_url": "https://academic.ui.ac.id/favicon.ico",
        }

        files = {"file": (filename, diff_file, "text/plain")}

        try:
            response = requests.post(webhook_url, data=data, files=files)
            response.raise_for_status()
            print("Content sent to webhook successfully.")
        except requests.exceptions.RequestException as e:
            print(f"Error sending content to webhook: {e}")
        finally:
            diff_file.close()

    @staticmethod
    def _is_webhook_valid(url: str) -> bool:
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    @staticmethod
    def _get_diff(old: str, new: str) -> str:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
        return "".join(diff)


def main():
    Main().main()


if __name__ == "__main__":
    main()
