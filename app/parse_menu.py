"""
Parse the UC Davis dining commons menu page HTML.

Extracts structured menu items from the page for the ENTIRE WEEK:
  - date, location, meal period, station/zone, dish name

HTML structure:
  div.tab-pane#monday, #tuesday, etc. -> Day containers
    h2.stickyMealHeader -> Meal Period (Breakfast / Lunch / Dinner)
    h3                  -> Station / Zone name
    h4.panel-title      -> Dish name
"""

from bs4 import BeautifulSoup
import json
import os
import datetime
import logging

logger = logging.getLogger(__name__)

# Map day tab IDs to weekday names
DAY_TAB_IDS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


def _get_week_dates():
    """
    Return a dict mapping day names to ISO date strings for the current week.
    The UC Davis menu page shows a Sunday–Saturday week.
    """
    today = datetime.date.today()
    # Find this week's Monday
    monday = today - datetime.timedelta(days=today.weekday())
    # Sunday of this week (day before Monday)
    sunday = monday - datetime.timedelta(days=1)

    dates = {}
    dates['sunday'] = sunday.isoformat()
    for i, day_name in enumerate(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):
        dates[day_name] = (monday + datetime.timedelta(days=i)).isoformat()

    return dates


def parse_menu(html_content, location_name="Tercero", date_override=None):
    """
    Parse the dining commons menu HTML and return structured items.

    If date_override is provided, all items get that date (legacy behavior).
    Otherwise, items are assigned the correct date based on their day tab.

    Args:
        html_content: Raw HTML string from the menu page.
        location_name: Name of the dining commons (e.g. "Tercero").
        date_override: Optional ISO date string. If set, all items get this date.

    Returns:
        List of dicts with keys: date, location, meal_period, station, dish_name.
        Returns empty list if parsing fails or no items found.
    """
    if not html_content:
        logger.warning("Empty HTML content received — nothing to parse.")
        return []

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        logger.error(f"Failed to parse HTML: {e}")
        return []

    week_dates = _get_week_dates()
    items = []

    # Parse each day tab separately
    for day_id in DAY_TAB_IDS:
        day_tab = soup.find('div', id=day_id, class_='tab-pane')
        if not day_tab:
            continue

        date_str = date_override or week_dates.get(day_id, datetime.date.today().isoformat())

        current_meal_period = None
        current_station = None

        for tag in day_tab.find_all(['h2', 'h3', 'h4']):
            classes = tag.get('class', [])

            if tag.name == 'h2' and 'stickyMealHeader' in classes:
                current_meal_period = tag.get_text(strip=True)
                current_station = None

            elif tag.name == 'h3' and current_meal_period:
                current_station = tag.get_text(strip=True)

            elif tag.name == 'h4' and 'panel-title' in classes and current_meal_period:
                dish_name = tag.get_text(strip=True)
                if dish_name:
                    items.append({
                        "date": date_str,
                        "location": location_name,
                        "meal_period": current_meal_period,
                        "station": current_station,
                        "dish_name": dish_name,
                    })

    if not items:
        logger.warning(
            f"No menu items found for {location_name}. "
            "The HTML structure may have changed — inspect the page manually."
        )
    else:
        # Count unique dates
        unique_dates = sorted(set(item['date'] for item in items))
        logger.info(f"Parsed {len(items)} items for {location_name} across {len(unique_dates)} days ({unique_dates[0]} to {unique_dates[-1]})")

    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_menu.html")
    with open(path, "r", encoding="utf-8") as f:
        parsed = parse_menu(f.read())

    # Show breakdown by date
    from collections import Counter
    date_counts = Counter(item['date'] for item in parsed)
    print(f"\nTotal items parsed: {len(parsed)}")
    print(f"\nBreakdown by date:")
    for date, count in sorted(date_counts.items()):
        weekday = datetime.date.fromisoformat(date).strftime('%A')
        print(f"  {date} ({weekday}): {count} items")
