"""
Google Calendar client for creating meal reminder events.

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project (or use an existing one)
  3. Enable the Google Calendar API
  4. Create OAuth 2.0 credentials (Desktop app type)
  5. Download the JSON and save it as `credentials.json` at the project root
  6. On first run, a browser window will open for you to authorize. 
     After that, a `token.json` file is saved so you don't need to re-auth.
"""

import os
import json
import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying scopes, delete token.json so a new one is generated.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, 'credentials.json')
TOKEN_PATH = os.path.join(PROJECT_ROOT, 'token.json')
SETTINGS_PATH = os.path.join(PROJECT_ROOT, 'config', 'settings.json')


def load_settings():
    with open(SETTINGS_PATH, 'r') as f:
        return json.load(f)


def get_calendar_service():
    """Authenticate and return a Google Calendar API service object."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print("ERROR: credentials.json not found at project root.")
                print("Follow the setup instructions in README.md to create it.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def create_meal_event(service, dish_name, date_str, meal_period, location, matched_favorite, settings=None):
    """
    Create a Google Calendar event for a matched meal.

    Args:
        service: Google Calendar API service object
        dish_name: the actual dish name from the menu
        date_str: ISO date string (e.g. "2026-04-22")
        meal_period: "Breakfast", "Lunch", or "Dinner"
        location: dining commons name (e.g. "Tercero")
        matched_favorite: the favorite that triggered the match
        settings: loaded settings dict (optional, will load if None)

    Returns:
        The created event's ID, or None on failure.
    """
    if settings is None:
        settings = load_settings()

    meal_times = settings.get('meal_times', {})
    timezone = settings.get('timezone', 'America/Los_Angeles')
    calendar_id = settings.get('calendar_id', 'primary')
    reminder_minutes = settings.get('reminder_minutes', 30)

    time_info = meal_times.get(meal_period, {'start': '12:00', 'end': '13:00'})
    start_time = f"{date_str}T{time_info['start']}:00"
    end_time = f"{date_str}T{time_info['end']}:00"

    event_body = {
        'summary': f"🍽️ {dish_name} — {location} DC",
        'location': f"{location} Dining Commons, UC Davis",
        'description': (
            f"Your favorite meal is being served!\n\n"
            f"Dish: {dish_name}\n"
            f"Matched favorite: {matched_favorite}\n"
            f"Meal period: {meal_period}\n"
            f"Location: {location} Dining Commons"
        ),
        'start': {
            'dateTime': start_time,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': timezone,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': reminder_minutes},
            ],
        },
    }

    try:
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        print(f"  📅 Created event: {event.get('htmlLink')}")
        return event.get('id')
    except Exception as e:
        print(f"  ❌ Failed to create event: {e}")
        return None


if __name__ == "__main__":
    print("--- Google Calendar Client Test ---")
    print()

    service = get_calendar_service()
    if service is None:
        print("Could not authenticate. Ensure credentials.json is in the project root.")
        exit(1)

    print("✅ Successfully authenticated with Google Calendar API!")
    print()

    # Create a test event for tomorrow so it doesn't clutter today
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    event_id = create_meal_event(
        service=service,
        dish_name="Test Meal — Please Delete",
        date_str=tomorrow,
        meal_period="Lunch",
        location="Tercero",
        matched_favorite="Test Favorite"
    )

    if event_id:
        print(f"\n✅ Test event created with ID: {event_id}")
        print("Check your Google Calendar to confirm it appeared!")
    else:
        print("\n❌ Test event creation failed.")
