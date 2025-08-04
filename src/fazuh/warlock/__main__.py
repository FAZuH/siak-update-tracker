import argparse

from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Warlock Bot")
    parser.add_argument(
        "module",
        choices=["tracker", "war"],
        help="Module to run (tracker or war).",
    )
    args = parser.parse_args()

    logger.add("log/{time}.log", rotation="1 day")

    if args.module == "tracker":
        from fazuh.warlock.module.schedule_update_tracker import ScheculeUpdateTracker

        ScheculeUpdateTracker().start()

    elif args.module == "war":
        from fazuh.warlock.module.war_bot import WarBot

        WarBot().start()


if __name__ == "__main__":
    main()
