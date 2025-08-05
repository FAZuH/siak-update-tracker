import asyncio
import json
import os

from loguru import logger

from fazuh.warlock.config import Config
from fazuh.warlock.siak.path import Path
from fazuh.warlock.siak.siak import Siak


class WarBot:
    def __init__(self):
        self.conf = Config()
        self.interval = 2

        if not os.path.exists("courses.json"):
            logger.error("courses.json file not found. Please create it with the required courses.")
            raise FileNotFoundError("courses.json file not found.")

        with open("courses.json", "r") as f:
            self.courses = json.load(f)

    async def start(self):
        self.siak = Siak(self.conf.username, self.conf.password)
        await self.siak.start()
        while True:
            self.conf.load()
            try:
                self.siak = Siak(self.conf.username, self.conf.password)
                await self.siak.start()
                if not await self.siak.authenticate():
                    logger.error("Authentication failed. Is the server down?")
                    continue

                await self.run()
            except Exception as e:
                logger.error(f"An error occurred: {e}")
            finally:
                await self.siak.close()
                logger.info(f"Retrying in {self.interval} seconds...")
                await asyncio.sleep(self.interval)

    async def run(self):
        await self.siak.page.goto(Path.COURSE_PLAN_EDIT)
        if self.siak.page.url != Path.COURSE_PLAN_EDIT:
            logger.error(f"Expected {Path.COURSE_PLAN_EDIT}. Found {self.siak.page.url} instead.")
            return

        rows = await self.siak.page.query_selector_all("tr")
        for row in rows:
            course_element = await row.query_selector("label")
            prof_element = await row.query_selector("td:nth-child(9)")
            if not course_element or not prof_element:
                continue

            course = await course_element.inner_text()
            prof = await prof_element.inner_text()

            for key, val in self.courses.items():
                if key.lower() not in course.lower() or val.lower() not in prof.lower():
                    continue

                button = await row.query_selector('input[type="radio"]')
                if not button:
                    continue

                await button.check()
                logger.info(f"Selected course: {course} with prof: {prof}")
                del self.courses[key]
                break

        for key, val in self.courses.items():
            logger.error(f"Course not found: {key} with prof: {val}")

        # Click the save button
        await self.siak.page.click("input[type=submit][value='Simpan IRS']")
        logger.success("IRS saved.")
