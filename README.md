## Features

- Automatic authentication to university portal
- Handle CAPTCHA challenges by notifying and asking the user to solve them
- Send notifications via Discord webhook
- **war**: Bot to search and enroll for courses by course and professor names.
- **track**: Track changes in course offerings, including professor, schedule, location, and more.

## Installation

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Download/clone this repository

In root of the repository,

3. Run `uv playwright install`
4. Copy `.env.example` to `.env` and fill in the required environment variables. Each variable is documented in the `.env-example` file.

## Usage

### War bot

In root of the repository, run `uv run warlock war`.

For `war` mode, copy `courses-example.json` to `courses.json` and fill in the required fields. `war` searches for courses and professors by checking keywords that **contains** the course name and professor name. 

War bot will not check for exact matches, for example, you can use "CS 101": "John" to find courses that contains "CS 101" e.g., "CS 101: Introduction to Computer Scienc" with professor name that contains "John", e.g., "John Doe".

### Schedule update tracker

In root of the repository, run `uv run warlock track`.
