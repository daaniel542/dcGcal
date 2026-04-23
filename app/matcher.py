"""
Favorite meal matcher.

Loads favorite meals from config/favorites.json, normalizes them,
and compares against parsed menu items using substring matching.
"""

import json
import os
import logging

from normalize import normalize

logger = logging.getLogger(__name__)

FAVORITES_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'favorites.json')


def load_favorites(path=FAVORITES_PATH):
    """
    Load favorite meals from the JSON config file.

    Returns:
        Dict mapping normalized_name -> original_name.
        Returns empty dict on error.
    """
    try:
        with open(path, 'r') as f:
            raw = json.load(f)

        if not isinstance(raw, list) or not raw:
            logger.warning(f"Favorites file is empty or not a list: {path}")
            return {}

        favorites = {normalize(fav): fav for fav in raw if fav}
        logger.info(f"Loaded {len(favorites)} favorites from {os.path.basename(path)}")
        return favorites

    except FileNotFoundError:
        logger.error(f"Favorites file not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in favorites file: {e}")
        return {}


def match_favorites(menu_items, favorites_map):
    """
    Compare parsed menu items against the favorites list.

    Uses substring matching: a favorite like "Mongolian BBQ" will match
    dishes like "BYO Mongolian BBQ" or "BYO Veggie Mongolian BBQ".

    Args:
        menu_items: List of dicts from parse_menu.
        favorites_map: Dict of {normalized_name: original_name}.

    Returns:
        List of matched menu item dicts, each with 'matched_favorite' key.
    """
    if not menu_items:
        return []
    if not favorites_map:
        logger.warning("No favorites loaded — nothing to match against.")
        return []

    matches = []
    for item in menu_items:
        norm_dish = normalize(item.get('dish_name', ''))
        if not norm_dish:
            continue

        for norm_fav, orig_fav in favorites_map.items():
            if norm_fav == norm_dish or norm_fav in norm_dish or norm_dish in norm_fav:
                matched = dict(item)
                matched['matched_favorite'] = orig_fav
                matches.append(matched)
                break  # one match per dish is enough

    return matches


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    from parse_menu import parse_menu

    html_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_menu.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    menu_items = parse_menu(html)
    favorites_map = load_favorites()

    print(f"\nParsed {len(menu_items)} menu items.")
    print(f"Tracking {len(favorites_map)} favorites: {list(favorites_map.values())}")
    print()

    matches = match_favorites(menu_items, favorites_map)

    if matches:
        print(f"🎉 Found {len(matches)} match(es)!")
        for m in matches:
            print(f"  ✅ {m['dish_name']} ({m['meal_period']}, {m['station']})")
            print(f"     Matched favorite: {m['matched_favorite']}")
    else:
        print("😔 No favorite meals on today's menu.")
