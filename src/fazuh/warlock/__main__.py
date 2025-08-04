from loguru import logger


def main():
    logger.add("log/{time}.log", rotation="1 day")

    from fazuh.warlock.module.schedule_update_tracker import ScheculeUpdateTracker
    ScheculeUpdateTracker().start()


if __name__ == "__main__":
    main()
