"""
Parse the UC Davis dining commons menu page HTML.

Extracts structured menu items from the page:
  - date, location, meal period, station/zone, dish name

HTML structure expected:
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


def parse_menu(html_content, location_name="Tercero", date_override=None):
    """
    Parse the dining commons menu HTML and return structured items.

    Args:
        html_content: Raw HTML string from the menu page.
        location_name: Name of the dining commons (e.g. "Tercero").
        date_override: Optional ISO date string. Defaults to today.

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

    date_str = date_override or datetime.date.today().isoformat()
    items = []

    current_meal_period = None
    current_station = None

    for tag in soup.find_all(['h2', 'h3', 'h4']):
        classes = tag.get('class', [])

        if tag.name == 'h2' and 'stickyMealHeader' in classes:
            current_meal_period = tag.get_text(strip=True)
            current_station = None  # Reset station on new meal period

        elif tag.name == 'h3' and current_meal_period:
            current_station = tag.get_text(strip=True)

        elif tag.name == 'h4' and 'panel-title' in classes and current_meal_period:
            dish_name = tag.get_text(strip=True)
            if dish_name:  # Skip empty dish names
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
        logger.info(f"Parsed {len(items)} items for {location_name} on {date_str}")

    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_menu.html")
    with open(path, "r", encoding="utf-8") as f:
        parsed = parse_menu(f.read())
        print(json.dumps(parsed[:5], indent=2))
        print(f"Total items parsed: {len(parsed)}")
