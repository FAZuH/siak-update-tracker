import json
import os
import time

from loguru import logger

from fazuh.warlock.config import Config
from fazuh.warlock.siak.siak import Siak
from fazuh.warlock.siak.path import Path


class WarBot:
    def __init__(self):
        self.conf = Config()
        self.interval = 2

        if not os.path.exists("courses.json"):
            logger.error("courses.json file not found. Please create it with the required courses.")
            raise FileNotFoundError("courses.json file not found.")

        with open("courses.json", "r") as f:
            self.courses = json.load(f)

    def start(self):
        while True:
            self.conf.load()
            try:
                self.siak = Siak(self.conf.username, self.conf.password)
                if not self.siak.authenticate():
                    logger.error("Authentication failed. Is the server down?")
                    continue

                self.run()
            except Exception as e:
                logger.error(f"An error occurred in WarBot: {e}")
            finally:
                self.siak.close()
                logger.info(f"Retrying in {self.interval} seconds...")
                time.sleep(self.interval)

    def run(self):
        self.siak.page.goto(Path.COURSE_PLAN_EDIT)
        if self.siak.page.url != Path.COURSE_PLAN_EDIT:
            logger.error(f"Expected {Path.COURSE_PLAN_EDIT}. Found {self.siak.page.url} instead.")
            return

        rows = self.siak.page.query_selector_all("tr")
        for row in rows:
            course_element = row.query_selector("label")
            prof_element = row.query_selector("td:nth-child(9)")
            if not course_element or not prof_element:
                continue

            course = course_element.inner_text()
            prof = prof_element.inner_text()

            for key, val in self.courses.items():
                if key not in course or val not in prof:
                    continue

                button = row.query_selector('input[type="radio"]')
                if not button:
                    continue

                button.check()
                logger.info(f"Selected course: {course} with prof: {prof}")
                del self.courses[key]
                break

        for key, val in self.courses.items():
            logger.error(f"Course not found: {key} with prof: {val}")

        # Click the save button
        self.siak.page.click("input[type=submit][value='Simpan IRS']")
        logger.success("IRS saved.")
