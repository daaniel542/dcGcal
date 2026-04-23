"""
Google Calendar client for creating meal reminder events.

Events are created on a dedicated "DCHD" calendar that can be shared
via URL so other people can subscribe to it.

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

# Full calendar scope needed to create/manage calendars and set sharing rules.
# If you previously had a token.json with a narrower scope, delete it.
SCOPES = ['https://www.googleapis.com/auth/calendar']

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, 'credentials.json')
TOKEN_PATH = os.path.join(PROJECT_ROOT, 'token.json')
SETTINGS_PATH = os.path.join(PROJECT_ROOT, 'config', 'settings.json')

DCHD_CALENDAR_NAME = "DCHD"


def load_settings():
    with open(SETTINGS_PATH, 'r') as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=4)


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


def get_or_create_dchd_calendar(service):
    """
    Find an existing 'DCHD' calendar or create one.
    Makes the calendar public so anyone with the URL can subscribe.
    Returns the calendar ID.
    """
    settings = load_settings()

    # Check if we already have the calendar ID saved
    saved_id = settings.get('dchd_calendar_id')
    if saved_id:
        # Verify it still exists
        try:
            cal = service.calendars().get(calendarId=saved_id).execute()
            return saved_id
        except Exception:
            pass  # Calendar was deleted — recreate below

    # Search existing calendars for one named DCHD
    calendar_list = service.calendarList().list().execute()
    for cal in calendar_list.get('items', []):
        if cal.get('summary') == DCHD_CALENDAR_NAME:
            cal_id = cal['id']
            settings['dchd_calendar_id'] = cal_id
            save_settings(settings)
            print(f"Found existing DCHD calendar: {cal_id}")
            return cal_id

    # Create a new calendar
    new_cal = service.calendars().insert(body={
        'summary': DCHD_CALENDAR_NAME,
        'description': 'UC Davis Dining Commons — Favorite Meal Alerts',
        'timeZone': settings.get('timezone', 'America/Los_Angeles'),
    }).execute()

    cal_id = new_cal['id']
    print(f"✅ Created new DCHD calendar: {cal_id}")

    # Make the calendar public so anyone can subscribe via URL
    try:
        service.acl().insert(calendarId=cal_id, body={
            'role': 'reader',
            'scope': {'type': 'default'},  # public
        }).execute()
        print("✅ Calendar set to public (anyone can subscribe)")
    except Exception as e:
        print(f"⚠️  Could not make calendar public: {e}")

    # Save the ID for future runs
    settings['dchd_calendar_id'] = cal_id
    save_settings(settings)

    # Print the shareable subscribe URL
    print_share_url(cal_id)

    return cal_id


def print_share_url(calendar_id):
    """Print the public iCal subscription URL for the DCHD calendar."""
    # Google Calendar public iCal feed URL format
    ical_url = f"https://calendar.google.com/calendar/ical/{calendar_id.replace('@', '%40')}/public/basic.ics"
    html_url = f"https://calendar.google.com/calendar/embed?src={calendar_id.replace('@', '%40')}"

    print()
    print("=" * 60)
    print("📅 DCHD Calendar — Share these URLs!")
    print("=" * 60)
    print(f"  Subscribe (iCal): {ical_url}")
    print(f"  View in browser:  {html_url}")
    print("=" * 60)
    print()


def create_meal_event(service, dish_name, date_str, meal_period, location, matched_favorite, settings=None, calendar_id=None):
    """
    Create a Google Calendar event for a matched meal on the DCHD calendar.

    Args:
        service: Google Calendar API service object
        dish_name: the actual dish name from the menu
        date_str: ISO date string (e.g. "2026-04-22")
        meal_period: "Breakfast", "Lunch", or "Dinner"
        location: dining commons name (e.g. "Tercero")
        matched_favorite: the favorite that triggered the match
        settings: loaded settings dict (optional, will load if None)
        calendar_id: the DCHD calendar ID (optional, falls back to settings)

    Returns:
        The created event's ID, or None on failure.
    """
    if settings is None:
        settings = load_settings()

    meal_times = settings.get('meal_times', {})
    timezone = settings.get('timezone', 'America/Los_Angeles')
    reminder_minutes = settings.get('reminder_minutes', 30)

    # Use the DCHD calendar
    if calendar_id is None:
        calendar_id = settings.get('dchd_calendar_id', 'primary')

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

    # Set up the DCHD calendar
    cal_id = get_or_create_dchd_calendar(service)
    print_share_url(cal_id)

    # Create a test event for tomorrow
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    event_id = create_meal_event(
        service=service,
        dish_name="Test Meal — Please Delete",
        date_str=tomorrow,
        meal_period="Lunch",
        location="Tercero",
        matched_favorite="Test Favorite",
        calendar_id=cal_id,
    )

    if event_id:
        print(f"\n✅ Test event created on DCHD calendar with ID: {event_id}")
    else:
        print("\n❌ Test event creation failed.")
