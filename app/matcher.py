import json
import os
from normalize import normalize

FAVORITES_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'favorites.json')

def load_favorites(path=FAVORITES_PATH):
    """Load favorite meals from the JSON config file and return them normalized."""
    with open(path, 'r') as f:
        raw = json.load(f)
    return {normalize(fav): fav for fav in raw}  # normalized -> original name


def match_favorites(menu_items, favorites_map):
    """
    Compare parsed menu items against the favorites list.

    Args:
        menu_items: list of dicts from parse_menu (each has 'dish_name', etc.)
        favorites_map: dict of {normalized_name: original_name} from load_favorites

    Returns:
        list of matched menu item dicts, each enriched with 'matched_favorite' key
    """
    matches = []
    for item in menu_items:
        norm_dish = normalize(item['dish_name'])
        # Check if the normalized dish name contains any favorite as a substring,
        # or if any favorite is contained in the dish name
        for norm_fav, orig_fav in favorites_map.items():
            if norm_fav == norm_dish or norm_fav in norm_dish or norm_dish in norm_fav:
                matched = dict(item)
                matched['matched_favorite'] = orig_fav
                matches.append(matched)
                break  # one match per dish is enough
    return matches


if __name__ == "__main__":
    from parse_menu import parse_menu

    # Load the saved sample HTML
    html_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_menu.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    menu_items = parse_menu(html)
    favorites_map = load_favorites()

    print(f"Parsed {len(menu_items)} menu items.")
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
