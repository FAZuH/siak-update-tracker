from loguru import logger


def main():
    logger.add("log/{time}.log", rotation="1 day")
    from fazuh.warlock.module.update_tracker import UpdateTracker

    UpdateTracker().start()


if __name__ == "__main__":
    main()
