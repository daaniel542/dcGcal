"""
Aggie Meal Notifier — Main Pipeline

Usage:
    python app/main.py

This script:
  1. Loads settings and favorites
  2. Fetches the menu page for each dining commons
  3. Parses the menu items
  4. Saves the menu snapshot to SQLite
  5. Matches parsed items against favorites
  6. Creates Google Calendar events for matches (with dedup)
  7. Logs everything to console and logs/app.log
"""

import os
import sys
import json
import logging
import datetime

# Add app/ to path so imports work when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from fetch_menu import fetch_menu_html
from parse_menu import parse_menu
from matcher import load_favorites, match_favorites
from db import init_db, save_menu_items, event_exists, save_calendar_event
from calendar_client import get_calendar_service, create_meal_event, load_settings

# ---------- Logging setup ----------

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ---------- Main pipeline ----------

def run():
    logger.info("=" * 60)
    logger.info("Aggie Meal Notifier — starting daily run")
    logger.info("=" * 60)

    # 1. Init DB
    init_db()

    # 2. Load settings
    settings = load_settings()
    dining_commons = settings.get('dining_commons', {})

    # 3. Load favorites
    favorites_map = load_favorites()
    logger.info(f"Tracking {len(favorites_map)} favorites: {list(favorites_map.values())}")

    # 4. Authenticate with Google Calendar
    service = get_calendar_service()
    if service is None:
        logger.error("Could not authenticate with Google Calendar. Aborting.")
        return

    # Summary counters
    total_items_parsed = 0
    total_items_saved = 0
    total_matches = 0
    total_events_created = 0
    total_duplicates_skipped = 0
    total_errors = 0

    # 5. Loop through each dining commons
    for dc_name, dc_url in dining_commons.items():
        logger.info(f"\n--- {dc_name} Dining Commons ---")

        # Fetch
        logger.info(f"Fetching menu from {dc_url}")
        html = fetch_menu_html(dc_url)
        if html is None:
            logger.error(f"Failed to fetch menu for {dc_name}. Skipping.")
            total_errors += 1
            continue
        logger.info(f"Fetch successful ({len(html)} bytes)")

        # Parse
        items = parse_menu(html, location_name=dc_name)
        total_items_parsed += len(items)
        logger.info(f"Parsed {len(items)} menu items")

        # Save to DB
        inserted = save_menu_items(items)
        total_items_saved += inserted
        logger.info(f"Saved {inserted} new items to database ({len(items) - inserted} duplicates skipped)")

        # Match
        matches = match_favorites(items, favorites_map)
        total_matches += len(matches)

        if not matches:
            logger.info(f"No favorite meals found at {dc_name} today.")
            continue

        logger.info(f"🎉 Found {len(matches)} match(es) at {dc_name}!")

        # Create calendar events
        for match in matches:
            dish = match['dish_name']
            date = match['date']
            period = match['meal_period']
            location = match['location']
            fav = match['matched_favorite']

            # Dedup check
            if event_exists(date, location, period, dish):
                logger.info(f"  ⏭️  Skipping (already created): {dish} ({period})")
                total_duplicates_skipped += 1
                continue

            # Create event
            event_id = create_meal_event(
                service=service,
                dish_name=dish,
                date_str=date,
                meal_period=period,
                location=location,
                matched_favorite=fav,
                settings=settings,
            )

            if event_id:
                save_calendar_event(event_id, date, location, period, dish)
                logger.info(f"  ✅ Created event: {dish} ({period}, {location})")
                total_events_created += 1
            else:
                logger.error(f"  ❌ Failed to create event: {dish}")
                total_errors += 1

    # 6. Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("DAILY RUN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Menu items parsed:     {total_items_parsed}")
    logger.info(f"  New items saved to DB: {total_items_saved}")
    logger.info(f"  Favorite matches:      {total_matches}")
    logger.info(f"  Calendar events created: {total_events_created}")
    logger.info(f"  Duplicates skipped:    {total_duplicates_skipped}")
    logger.info(f"  Errors:                {total_errors}")
    logger.info("=" * 60)
    logger.info("Done!")


if __name__ == "__main__":
    run()
