"""
Offline dry-run test — uses the saved sample_menu.html (no network needed).

Tests:
  1. Loads the local sample HTML (Tercero) as a stand-in for all 3 DCs
  2. Parses and matches against favorites
  3. Runs the cross-DC grouping logic (simulates all 3 DCs finding matches)
  4. Prints what calendar events WOULD be created
  5. Tests the stale-event DB helpers
"""

import os
import sys
import datetime
from collections import defaultdict
import json

sys.path.insert(0, os.path.dirname(__file__))

from parse_menu import parse_menu
from matcher import load_favorites, match_favorites
from db import (
    init_db, save_menu_items, event_exists,
    get_google_event_id, delete_calendar_event_record, save_calendar_event,
)

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
with open(SETTINGS_PATH) as f:
    settings = json.load(f)

dining_commons       = settings.get('dining_commons', {})
location_preferences = settings.get('location_preferences', list(dining_commons.keys()))
show_all             = settings.get('show_all_locations_in_event', True)

def sort_key(location):
    try:
        return location_preferences.index(location)
    except ValueError:
        return len(location_preferences)

# ── 1. Init DB ───────────────────────────────────────────────────────────────
init_db()
print("✅ DB initialised")

# ── 2. Load favorites ────────────────────────────────────────────────────────
favorites_map = load_favorites()
print(f"✅ Loaded {len(favorites_map)} favorites: {list(favorites_map.values())}\n")

# ── 3. Load sample HTML & simulate all 3 DCs ─────────────────────────────────
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_menu.html')
with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

print(f"✅ Loaded sample HTML ({len(html):,} bytes)\n")

today = datetime.date.today().isoformat()
cross_dc_matches = defaultdict(list)

# Simulate parsing the same HTML for each DC (real run would fetch each DC's own page)
for dc_name in dining_commons.keys():
    print(f"─── {dc_name} (simulated) ───")
    items = parse_menu(html, location_name=dc_name)
    print(f"  Parsed {len(items)} menu items")

    inserted = save_menu_items(items)
    print(f"  Saved {inserted} new items to DB ({len(items)-inserted} already existed)")

    upcoming = [i for i in items if i['date'] >= today]
    matches  = match_favorites(upcoming, favorites_map)
    print(f"  Upcoming matches: {len(matches)}")
    for m in matches:
        print(f"    🎉 {m['dish_name']} ({m['meal_period']}, {m['date']}) → '{m['matched_favorite']}'")
        key = (m['date'], m['meal_period'], m['dish_name'])
        cross_dc_matches[key].append({
            'location': dc_name,
            'matched_favorite': m['matched_favorite'],
        })
    print()

# ── 4. Cross-DC grouping ─────────────────────────────────────────────────────
print("=" * 60)
print("CROSS-DC EVENT GROUPING (what would be created on Calendar)")
print("=" * 60)

if not cross_dc_matches:
    print("😔 No matches across any dining commons today/upcoming.")
    print("   (The sample_menu.html may be from a past week — this is expected.)")
else:
    # Group by (date, period) — same logic as main.py Phase B
    event_groups = defaultdict(list)  # (date, period) → [dish_entries]

    for (date, period, dish_name), entries in cross_dc_matches.items():
        sorted_entries  = sorted(entries, key=lambda e: sort_key(e['location']))
        all_locs        = [e['location'] for e in sorted_entries]
        matched_fav     = sorted_entries[0]['matched_favorite']
        already_exists  = any(event_exists(date, loc, period, dish_name) for loc in all_locs)

        event_groups[(date, period)].append({
            'dish_name':        dish_name,
            'matched_favorite':  matched_fav,
            'locations':         all_locs,
            'already_exists':    already_exists,
        })

    for (date, period), dishes in sorted(event_groups.items()):
        # Collect union of all locations for this slot
        all_locs_for_slot = []
        seen = set()
        for d in dishes:
            for loc in d['locations']:
                if loc not in seen:
                    all_locs_for_slot.append(loc)
                    seen.add(loc)

        # Build title exactly as create_meal_event would
        if len(dishes) == 1:
            d = dishes[0]
            locs_str = " & ".join(d['locations'])
            summary = f"🍽️ {d['dish_name']} @ {locs_str}"
        else:
            summary = f"🍽️ {len(dishes)} Favorites — {period}!"

        # Build description exactly as create_meal_event would
        description_lines = ["Your favorite meals are being served!", ""]
        for d in dishes:
            loc_str = ", ".join(d['locations'])
            description_lines.append(f"  • {d['dish_name']} — {loc_str}")
        description_lines.append(f"\n  Meal period: {period}")

        any_new = any(not d['already_exists'] for d in dishes)
        status  = "✅ WOULD CREATE" if any_new else "⏭️  SKIP (already in DB)"

        print(f"\n{status}")
        print(f"  Title       : {summary}")
        print(f"  Date        : {date}  |  Period: {period}")
        print(f"  All DCs     : {', '.join(all_locs_for_slot)}")
        print(f"  Description :")
        for line in description_lines:
            print(f"    {line}")


# ── 5. Stale-event DB helpers ─────────────────────────────────────────────────
print()
print("=" * 60)
print("STALE EVENT DETECTION DB HELPERS TEST")
print("=" * 60)

FAKE_DATE     = "2099-01-01"
FAKE_LOCATION = "Tercero"
FAKE_PERIOD   = "Lunch"
FAKE_DISH     = "__test_dry_run_dish__"
FAKE_GID      = "fake_google_event_id_xyz"

save_calendar_event(FAKE_GID, FAKE_DATE, FAKE_LOCATION, FAKE_PERIOD, FAKE_DISH)
print(f"  Seeded fake DB record  →  google_event_id='{FAKE_GID}'")

retrieved = get_google_event_id(FAKE_DATE, FAKE_LOCATION, FAKE_PERIOD, FAKE_DISH)
match_ok  = retrieved == FAKE_GID
print(f"  get_google_event_id()  →  '{retrieved}'  {'✅' if match_ok else '❌'}")

delete_calendar_event_record(FAKE_DATE, FAKE_LOCATION, FAKE_PERIOD, FAKE_DISH)
after = get_google_event_id(FAKE_DATE, FAKE_LOCATION, FAKE_PERIOD, FAKE_DISH)
print(f"  After delete_calendar_event_record(), result: {after}  {'✅ correctly None' if after is None else '❌ should be None'}")

print()
print("=" * 60)
print("Offline dry-run complete. No calendar events were created or modified.")
print("=" * 60)
