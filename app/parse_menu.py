from bs4 import BeautifulSoup
import json
import os
import datetime

def parse_menu(html_content, location_name="Tercero"):
    soup = BeautifulSoup(html_content, 'html.parser')
    items = []
    
    # We will assume today's date if not reliably parsed
    date_str = datetime.date.today().isoformat()
    
    # Menus are usually contained within a tab pane, but we can iterate through the flat structure
    # Or find the current day's tab content.
    # Looking at the flat structure:
    # h2.stickyMealHeader -> Meal Period
    # h3 -> Station / Zone
    # h4.panel-title -> Dish
    
    current_meal_period = None
    current_station = None
    
    # We find all relevant tags in order
    for tag in soup.find_all(['h2', 'h3', 'h4']):
        classes = tag.get('class', [])
        if tag.name == 'h2' and 'stickyMealHeader' in classes:
            current_meal_period = tag.get_text(strip=True)
            current_station = None # Reset station on new meal period
        elif tag.name == 'h3' and current_meal_period:
            current_station = tag.get_text(strip=True)
        elif tag.name == 'h4' and 'panel-title' in classes and current_meal_period:
            dish_name = tag.get_text(strip=True)
            items.append({
                "date": date_str,
                "location": location_name,
                "meal_period": current_meal_period,
                "station": current_station,
                "dish_name": dish_name
            })
            
    return items

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_menu.html")
    with open(path, "r", encoding="utf-8") as f:
        parsed = parse_menu(f.read())
        print(json.dumps(parsed[:5], indent=2))
        print(f"Total items parsed: {len(parsed)}")
