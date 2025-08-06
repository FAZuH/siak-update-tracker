
https://github.com/user-attachments/assets/31b86a47-ba8f-466b-8d71-48ab0384e73e

https://github.com/user-attachments/assets/e1f077d2-494c-43de-b5be-4a1bfbb87a3d

> [!warning]
> This script may not work as expected. Use at your own risk.

## Features

- Automatic authentication to university portal
- Handle CAPTCHA challenges by notifying and asking the user to solve them
- Send notifications via Discord webhook

**Modules**:
- **war**: Bot to search and enroll for courses by course and professor names.
- **track**: Track changes in course offerings, including professor, schedule, location, and more.

## Installation

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Download/clone this repository

In root of the repository,

3. Run `uv sync`. (This will install all the required project dependencies and set up the project environment)
4. Run `uv run playwright install-deps && uv run playwright install`. (This will install the necessary dependencies for Playwright, which is used for web scraping and automation)
5. Copy `.env-example` file to `.env` and fill in the required environment variables. Each variable is documented in the `.env-example` file.

## Usage

### War bot

Copy `courses-example.json` file to `courses.json` and fill in the required fields.

You can run using `uv run warlock war`.

The War bot does **case-insensitive** searches and does **not require exact matches** for course and professor names. For example, you can use "cs 101": "john" to select course "CS 101: Introduction to Computer Scienc" with professor name "John Doe".

### Schedule update tracker

In root of the repository, run `uv run warlock track`.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
