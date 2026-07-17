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


def verify_event_exists(service, calendar_id, event_id):
    """
    Check whether a Google Calendar event still exists.

    Args:
        service: Google Calendar API service object.
        calendar_id: The calendar ID the event belongs to.
        event_id: The Google Calendar event ID to verify.

    Returns:
        True if the event exists, False if it was deleted or not found.
    """
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        # Events that were cancelled/deleted have status 'cancelled'
        return event.get('status') != 'cancelled'
    except Exception:
        return False

def _build_event_body(dishes, date_str, meal_period, settings):
    """Internal helper to construct the event payload body."""
    meal_times = settings.get('meal_times', {})
    timezone = settings.get('timezone', 'America/Los_Angeles')
    reminder_minutes = settings.get('reminder_minutes', 30)

    time_info = meal_times.get(meal_period, {'start': '12:00', 'end': '13:00'})
    start_time = f"{date_str}T{time_info['start']}:00"
    end_time   = f"{date_str}T{time_info['end']}:00"

    # ---- Build title ----
    # Collect the unique ordered set of all locations across all dishes
    all_locs_ordered = []
    seen_locs = set()
    for d in dishes:
        for loc in d.get('locations', []):
            if loc not in seen_locs:
                all_locs_ordered.append(loc)
                seen_locs.add(loc)

    if len(dishes) == 1:
        d = dishes[0]
        locs_str = " & ".join(d.get('locations', all_locs_ordered))
        summary = f"🍽️ {d['dish_name']} @ {locs_str}"
    else:
        summary = f"🍽️ {len(dishes)} Favorites — {meal_period}!"

    # ---- Build description ----
    description = "Your favorite meals are being served!\n\n"
    for d in dishes:
        locs = d.get('locations', [])
        loc_str = ", ".join(locs) if locs else "Unknown DC"
        description += f"• {d['dish_name']} — {loc_str}\n"
    description += f"\nMeal period: {meal_period}"

    # ---- Google Calendar location field ----
    location_field = ", ".join(all_locs_ordered) + " Dining Commons, UC Davis"

    return {
        'summary': summary,
        'location': location_field,
        'description': description,
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

def create_meal_event(service, dishes, date_str, meal_period, settings=None, calendar_id=None):
    """
    Create a Google Calendar event for matched meals on the DCHD calendar.

    Args:
        service: Google Calendar API service object.
        dishes: list of dicts, each with 'dish_name', 'matched_favorite', 'locations'
        date_str: ISO date string (e.g. "2026-04-22").
        meal_period: "Breakfast", "Lunch", or "Dinner".
        settings: loaded settings dict (optional, loads from file if None).
        calendar_id: DCHD calendar ID (optional, falls back to settings).

    Returns:
        The created event's ID, or None on failure.
    """
    if not dishes:
        return None

    if settings is None:
        settings = load_settings()
    if calendar_id is None:
        calendar_id = settings.get('dchd_calendar_id', 'primary')

    event_body = _build_event_body(dishes, date_str, meal_period, settings)

    try:
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        print(f"  📅 Created event: {event.get('htmlLink')}")
        return event.get('id')
    except Exception as e:
        print(f"  ❌ Failed to create event: {e}")
        return None

def update_meal_event(service, event_id, dishes, date_str, meal_period, settings=None, calendar_id=None):
    """
    Update an existing Google Calendar event with a new list of matched meals.
    Used when a user adds a new favorite that falls in an already-created meal slot.
    """
    if not dishes:
        return None

    if settings is None:
        settings = load_settings()
    if calendar_id is None:
        calendar_id = settings.get('dchd_calendar_id', 'primary')

    event_body = _build_event_body(dishes, date_str, meal_period, settings)

    try:
        event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
        print(f"  🔄 Updated event: {event.get('htmlLink')}")
        return event.get('id')
    except Exception as e:
        print(f"  ❌ Failed to update event {event_id}: {e}")
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
        dishes=[{'dish_name': 'Test Meal — Please Delete', 'matched_favorite': 'Test Favorite'}],
        date_str=tomorrow,
        meal_period="Lunch",
        location="Tercero",
        calendar_id=cal_id,
    )

    if event_id:
        print(f"\n✅ Test event created on DCHD calendar with ID: {event_id}")
    else:
        print("\n❌ Test event creation failed.")
