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
  6. Verifies any existing calendar event DB records are still live on Google Calendar
     (prunes stale records so deleted events get re-created)
  7. Consolidates matches across all dining commons by (date, period, dish)
     so one event lists every location serving that favorite
  8. Creates/skips Google Calendar events with dedup
  9. Logs everything to console and logs/app.log
"""

import os
import sys
import json
import logging
import datetime
from collections import defaultdict

# Add app/ to path so imports work when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from fetch_menu import fetch_menu_html
from parse_menu import parse_menu
from matcher import load_favorites, match_favorites
from db import (
    init_db, save_menu_items, event_exists, save_calendar_event,
    get_google_event_id, delete_calendar_event_record,
    get_existing_event_for_slot, delete_all_calendar_event_records_for_slot,
)
from calendar_client import (
    get_calendar_service, create_meal_event, load_settings,
    get_or_create_dchd_calendar, verify_event_exists,
)

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

# ---------- Helpers ----------


def _sort_key_for_location(location, preferences):
    """Return an integer rank for a location based on the preferences list."""
    try:
        return preferences.index(location)
    except ValueError:
        return len(preferences)  # Unknown locations go last


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
    location_preferences = settings.get('location_preferences', list(dining_commons.keys()))
    show_all = settings.get('show_all_locations_in_event', True)

    # 3. Load favorites
    favorites_map = load_favorites()
    logger.info(f"Tracking {len(favorites_map)} favorites: {list(favorites_map.values())}")

    # 4. Authenticate with Google Calendar
    service = get_calendar_service()
    if service is None:
        logger.error("Could not authenticate with Google Calendar. Aborting.")
        return

    # 4b. Get or create the shared DCHD calendar
    dchd_cal_id = get_or_create_dchd_calendar(service)
    logger.info(f"Using DCHD calendar: {dchd_cal_id}")

    # Summary counters
    total_items_parsed = 0
    total_items_saved = 0
    total_matches = 0
    total_events_created = 0
    total_duplicates_skipped = 0
    total_stale_pruned = 0
    total_errors = 0

    today = datetime.date.today().isoformat()

    # -----------------------------------------------------------------------
    # Phase A — Scrape, parse, and save ALL dining commons.
    # Collect every upcoming match keyed by (date, period, dish_name) so we
    # can group multiple locations together into a single calendar event.
    # -----------------------------------------------------------------------

    # Structure: { (date, period, dish_name): [ {location, matched_favorite}, … ] }
    cross_dc_matches = defaultdict(list)

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

        # Parse (gets the full week's menu)
        items = parse_menu(html, location_name=dc_name)
        total_items_parsed += len(items)
        logger.info(f"Parsed {len(items)} menu items")

        # Save ALL items to DB (full week — builds historical dataset)
        inserted = save_menu_items(items)
        total_items_saved += inserted
        logger.info(f"Saved {inserted} new items to database ({len(items) - inserted} duplicates skipped)")

        # Match only today and future items for calendar events
        upcoming_items = [item for item in items if item['date'] >= today]
        matches = match_favorites(upcoming_items, favorites_map)
        total_matches += len(matches)

        if not matches:
            logger.info(f"No favorite meals found at {dc_name} for today/upcoming.")
            continue

        logger.info(f"🎉 Found {len(matches)} match(es) at {dc_name}!")

        # Accumulate into cross-DC structure
        for match in matches:
            key = (match['date'], match['meal_period'], match['dish_name'])
            cross_dc_matches[key].append({
                'location': dc_name,
                'matched_favorite': match['matched_favorite'],
            })

    # -----------------------------------------------------------------------
    # Phase B — Create or Update calendar events.
    # Group ALL new matches by (date, period) only — one event per meal slot
    # per day. If an event already exists for that slot, we check if any new
    # dishes/locations were added, and if so, update the Google Event.
    # -----------------------------------------------------------------------

    logger.info("\n--- Creating / Updating Calendar Events ---")

    # { (date, period): [ {dish_name, matched_favorite, locations: [...]}, … ] }
    event_groups = defaultdict(list)

    for (date, period, dish_name), location_entries in cross_dc_matches.items():
        # Sort locations by user preferences
        sorted_locations = sorted(
            location_entries,
            key=lambda e: _sort_key_for_location(e['location'], location_preferences)
        )
        all_locs = [e['location'] for e in sorted_locations]
        matched_fav = sorted_locations[0]['matched_favorite']

        event_groups[(date, period)].append({
            'dish_name': dish_name,
            'matched_favorite': matched_fav,
            'locations': all_locs,
        })

    # Create or Update one event per (date, period)
    for (date, period), dishes in sorted(event_groups.items()):
        # Build a union of all locations across all dishes (for logging)
        all_locs_for_slot = []
        seen = set()
        for d in dishes:
            for loc in d.get('locations', []):
                if loc not in seen:
                    all_locs_for_slot.append(loc)
                    seen.add(loc)

        label = dishes[0]['dish_name'] if len(dishes) == 1 else f"{len(dishes)} favorites"
        logger.info(f"  📍 {label} — {', '.join(all_locs_for_slot)} ({period}, {date})")

        # Check if an event already exists for this slot
        existing_event_id = get_existing_event_for_slot(date, period)

        if existing_event_id:
            # Verify the event is still on the calendar
            live = verify_event_exists(service, dchd_cal_id, existing_event_id)
            if not live:
                logger.info(f"  🔄 Detected deleted master event for {date} {period}. Pruning stale DB records.")
                delete_all_calendar_event_records_for_slot(date, period)
                existing_event_id = None
                total_stale_pruned += 1

        if existing_event_id:
            # Event exists and is live. Does it need an update?
            # It needs an update if any dish+location combo is missing from the DB.
            needs_update = False
            for d in dishes:
                for loc in d.get('locations', []):
                    if not event_exists(date, loc, period, d['dish_name']):
                        needs_update = True
                        break
                if needs_update:
                    break

            if needs_update:
                from calendar_client import update_meal_event
                # Update the event to reflect all current dishes
                updated_id = update_meal_event(
                    service=service,
                    event_id=existing_event_id,
                    dishes=dishes,
                    date_str=date,
                    meal_period=period,
                    settings=settings,
                    calendar_id=dchd_cal_id,
                )
                if updated_id:
                    for d in dishes:
                        for loc in d.get('locations', []):
                            save_calendar_event(existing_event_id, date, loc, period, d['dish_name'])
                    logger.info(f"  ✅ Updated event: {len(dishes)} dish(es) ({period}, {', '.join(all_locs_for_slot)})")
                    # Incrementing total events created just to show progress
                    total_events_created += 1
                else:
                    logger.error(f"  ❌ Failed to update event for {period} on {date}")
                    total_errors += 1
            else:
                logger.info(f"  ⏭️  Skipping (already up-to-date)")
                total_duplicates_skipped += 1

        else:
            # Create a brand new event
            event_id = create_meal_event(
                service=service,
                dishes=dishes,
                date_str=date,
                meal_period=period,
                settings=settings,
                calendar_id=dchd_cal_id,
            )

            if event_id:
                for d in dishes:
                    for loc in d.get('locations', []):
                        save_calendar_event(event_id, date, loc, period, d['dish_name'])
                logger.info(f"  ✅ Created event: {len(dishes)} dish(es) ({period}, {', '.join(all_locs_for_slot)})")
                total_events_created += 1
            else:
                logger.error(f"  ❌ Failed to create event for {period} on {date}")
                total_errors += 1

    # 6. Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("DAILY RUN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Dining commons scraped:    {len(dining_commons)}")
    logger.info(f"  Menu items parsed:         {total_items_parsed}")
    logger.info(f"  New items saved to DB:     {total_items_saved}")
    logger.info(f"  Favorite matches:          {total_matches}")
    logger.info(f"  Calendar events created:   {total_events_created}")
    logger.info(f"  Duplicates skipped:        {total_duplicates_skipped}")
    logger.info(f"  Stale records pruned:      {total_stale_pruned}")
    logger.info(f"  Errors:                    {total_errors}")
    logger.info("=" * 60)
    logger.info("Done!")


if __name__ == "__main__":
    run()
