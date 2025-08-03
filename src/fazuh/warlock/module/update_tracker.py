from datetime import datetime
import difflib
import io
from pathlib import Path
import time

from bs4 import BeautifulSoup
import requests

from fazuh.warlock.config import Config
from fazuh.warlock.siak.auth import Auth


class UpdateTracker:
    def __init__(self):
        self.conf = Config()
        self.tracked_page = "https://academic.ui.ac.id/main/Schedule/Index?period=2025-1&search="

        data_folder = Path("data")
        if not data_folder.exists():
            data_folder.mkdir(parents=True)

        self.cache_file = data_folder.joinpath("latest_courses.txt")
        if not self.cache_file.exists():
            self.cache_file.touch()

        self.prev_content = self.cache_file.read_text() if self.cache_file.exists() else ""

        self.session = requests.Session()
        self.auth = Auth(self.session, self.conf.username, self.conf.password)

    def start(self):
        while True:
            if self.auth.authenticate():
                self.run()
            print(f"Waiting for the next check in {self.conf.interval} seconds...")
            time.sleep(self.conf.interval)

    def run(self):
        # 1. GET tracked page
        resp = self.session.get(self.tracked_page)
        if resp.url != self.tracked_page:
            print(f"Error: Expected {self.tracked_page}. Found {resp.url} instead.")
            return

        # 2. Parse response
        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.find_all(class_=["sub", "border2", "pad2"])  # Mata kuliah
        courses: list[str] = []
        for e in elements:
            content = "".join(str(e) for e in e.contents)  # type: ignore
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
        self._to_webhook(self.conf.webhook_url, diff)

        self.prev_content = curr
        self.cache_file.write_text(curr)

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
            "username": "warlock",
            "avatar_url": "https://academic.ui.ac.id/favicon.ico",
        }

        files = {"file": (filename, diff_file, "text/plain")}

        try:
            resp = requests.post(webhook_url, data=data, files=files)
            resp.raise_for_status()
            print("Content sent to webhook successfully.")
        except requests.exceptions.RequestException as e:
            print(f"Error sending content to webhook: {e}")
        finally:
            diff_file.close()

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
