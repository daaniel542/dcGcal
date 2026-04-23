# Aggie Meal Notifier

Automatically detect when specific favorite meals appear on a UC Davis dining commons menu and create Google Calendar events with reminders at the correct meal time.

## Goal
* Fetch the UC Davis dining menu page daily
* Parse today's menu to find specific preferred meals
* Create Google Calendar events for matched meals

## Setup
1. Clone the repo
2. Create and activate virtual environment: `python3 -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `config/settings.json` file for Google Calendar integration if required (optional initially)
5. Set up Google Calendar OAuth by following Google Calendar API Python Quickstart and saving `credentials.json` at the project root.
6. Populate `config/favorites.json` with meals you want to track.

## Run
`python app/main.py`
