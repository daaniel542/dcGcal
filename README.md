# Aggie Meal Notifier 🍽️

Automatically detect when your favorite meals appear on a UC Davis dining commons menu and create Google Calendar events with reminders at the correct meal time.

Events are posted to a shared **DCHD** calendar that anyone can subscribe to via URL.

---

## Features

- Fetches UC Davis dining commons menus daily
- Parses meal periods (Breakfast, Lunch, Dinner) with station/zone info
- Matches against your personal favorites list using substring matching
- Creates Google Calendar events on a dedicated shareable calendar
- Deduplication — safe to re-run without creating duplicate events
- Stores historical menu data in SQLite
- Logs everything to `logs/app.log`
- Scheduled to run automatically via macOS launchd

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/daaniel542/dcGcal.git
cd dcGcal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Search for and **enable** the **Google Calendar API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Desktop application** as the type
6. Download the JSON file and save it as `credentials.json` in the project root

### 3. Configure your favorites

Edit `config/favorites.json` with the meals you want to track:

```json
[
    "Tri Tip",
    "Build Your Own Burger",
    "Mongolian BBQ",
    "Orange Chicken"
]
```

Matching is case-insensitive and uses substring matching, so `"Mongolian BBQ"` will match `"BYO Mongolian BBQ"`.

### 4. Configure dining commons and times

Edit `config/settings.json` to set:
- Which dining commons to check
- Meal period time windows
- Timezone
- Reminder time (minutes before)

### 5. First run

```bash
python app/main.py
```

On first run, a browser window will open for Google OAuth. After authorizing, a `token.json` is saved so you won't need to re-auth.

The script will:
- Create a **DCHD** calendar on your Google account
- Make it public (shareable via URL)
- Print the subscribe/share URLs
- Fetch menus, match favorites, and create events

### 6. Schedule daily runs (optional)

```bash
cp com.aggiemeal.notifier.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aggiemeal.notifier.plist
```

This runs the notifier daily at 6:00 AM. See `app/scheduler_notes.md` for more options.

---

## Project Structure

```
aggie-meal-notifier/
├── app/
│   ├── main.py              # End-to-end pipeline
│   ├── fetch_menu.py         # Fetch dining menu HTML (with retries)
│   ├── parse_menu.py         # Parse HTML into structured items
│   ├── normalize.py          # Text normalization for matching
│   ├── matcher.py            # Match menu items against favorites
│   ├── calendar_client.py    # Google Calendar API integration
│   ├── db.py                 # SQLite database operations
│   └── scheduler_notes.md    # Scheduling documentation
├── config/
│   ├── favorites.json        # Your favorite meals
│   └── settings.json         # App configuration
├── data/
│   └── dining.db             # Historical menu database (auto-created)
├── logs/
│   └── app.log               # Application logs (auto-created)
├── com.aggiemeal.notifier.plist  # macOS launchd schedule
├── run_daily.sh              # Shell wrapper for scheduled runs
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Debugging

```bash
# Check logs
cat logs/app.log

# Check launchd status
launchctl list | grep aggiemeal

# Check launchd output
cat logs/launchd_stdout.log
cat logs/launchd_stderr.log

# Run manually
python app/main.py

# Test individual components
python app/fetch_menu.py      # Test fetching
python app/parse_menu.py      # Test parsing
python app/matcher.py         # Test matching
python app/calendar_client.py # Test calendar
python app/db.py              # Test database
```

---

## Sharing the Calendar

After the first run, the DCHD calendar URLs are printed and saved. Share them so others can subscribe:

- **iCal URL** — paste into Google Calendar / Apple Calendar / Outlook → "Add by URL"
- **Browser URL** — view the calendar in any web browser

---

## Tech Stack

- **Python 3**
- `requests` + `beautifulsoup4` — fetching and parsing
- `google-api-python-client` — Google Calendar API
- `sqlite3` — local historical storage
- macOS `launchd` — scheduling
