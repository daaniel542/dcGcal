import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'dining.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create menu_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            meal_period TEXT NOT NULL,
            dish_name TEXT NOT NULL,
            station TEXT,
            UNIQUE(date, location, meal_period, dish_name)
        )
    ''')
    
    # Create favorites table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dish_name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create calendar_events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_event_id TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            meal_period TEXT NOT NULL,
            dish_name TEXT NOT NULL,
            UNIQUE(date, location, meal_period, dish_name)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)


def save_menu_items(menu_items):
    """
    Insert parsed menu items into the database.
    Silently skips duplicates (same date/location/meal_period/dish_name).
    Returns the count of newly inserted rows.
    """
    conn = get_conn()
    cursor = conn.cursor()
    inserted = 0
    for item in menu_items:
        try:
            cursor.execute('''
                INSERT INTO menu_items (date, location, meal_period, dish_name, station)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                item['date'],
                item['location'],
                item['meal_period'],
                item['dish_name'],
                item.get('station')
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # duplicate — skip
    conn.commit()
    conn.close()
    return inserted


def event_exists(date, location, meal_period, dish_name):
    """Check if a calendar event has already been created for this meal."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM calendar_events
        WHERE date = ? AND location = ? AND meal_period = ? AND dish_name = ?
    ''', (date, location, meal_period, dish_name))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def save_calendar_event(google_event_id, date, location, meal_period, dish_name):
    """Record a created calendar event. Skips if duplicate."""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO calendar_events (google_event_id, date, location, meal_period, dish_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (google_event_id, date, location, meal_period, dish_name))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already recorded
    conn.close()


def get_google_event_id(date, location, meal_period, dish_name):
    """
    Return the stored Google Calendar event ID for a given meal, or None if not found.
    Used to verify the event still exists on Google Calendar before skipping it.
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT google_event_id FROM calendar_events
        WHERE date = ? AND location = ? AND meal_period = ? AND dish_name = ?
    ''', (date, location, meal_period, dish_name))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def delete_calendar_event_record(date, location, meal_period, dish_name):
    """
    Remove a stale calendar event record from the DB.
    Called when we detect the event was deleted from Google Calendar.
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM calendar_events
        WHERE date = ? AND location = ? AND meal_period = ? AND dish_name = ?
    ''', (date, location, meal_period, dish_name))
    conn.commit()
    conn.close()


def get_existing_event_for_slot(date, meal_period):
    """
    Return the stored Google Calendar event ID for a given date and meal period,
    regardless of the dish or location. Returns None if no event exists.
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT google_event_id FROM calendar_events
        WHERE date = ? AND meal_period = ? LIMIT 1
    ''', (date, meal_period))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def delete_all_calendar_event_records_for_slot(date, meal_period):
    """
    Remove all stale calendar event records for a specific date and meal period.
    Called when the master event for this slot was deleted from Google Calendar.
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM calendar_events
        WHERE date = ? AND meal_period = ?
    ''', (date, meal_period))
    conn.commit()
    conn.close()


def sync_favorites(favorites_list):
    """
    Sync the favorites JSON list into the favorites table.
    Inserts any new favorites and leaves existing ones alone.
    """
    conn = get_conn()
    cursor = conn.cursor()
    for fav in favorites_list:
        try:
            cursor.execute('INSERT INTO favorites (dish_name) VALUES (?)', (fav,))
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


def get_all_menu_items(date=None):
    """Retrieve menu items, optionally filtered by date."""
    conn = get_conn()
    cursor = conn.cursor()
    if date:
        cursor.execute('SELECT * FROM menu_items WHERE date = ?', (date,))
    else:
        cursor.execute('SELECT * FROM menu_items')
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == '__main__':
    import json

    init_db()
    print(f"Database initialized at {DB_PATH}")

    # --- Test: save menu items ---
    from parse_menu import parse_menu
    html_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_menu.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        items = parse_menu(f.read())

    inserted = save_menu_items(items)
    print(f"Inserted {inserted} menu items (out of {len(items)} parsed).")

    # Run again to prove dedup works
    inserted_again = save_menu_items(items)
    print(f"Second run inserted {inserted_again} (should be 0 — duplicates skipped).")

    # --- Test: sync favorites ---
    fav_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'favorites.json')
    with open(fav_path, 'r') as f:
        favs = json.load(f)
    sync_favorites(favs)
    print(f"Synced {len(favs)} favorites into DB.")

    # --- Test: event_exists (should be False) ---
    print(f"Event exists check (expect False): {event_exists('2026-04-22', 'Tercero', 'Lunch', 'BYO Mongolian BBQ')}")

    # --- Test: save + check calendar event ---
    save_calendar_event('fake_id_123', '2026-04-22', 'Tercero', 'Lunch', 'BYO Mongolian BBQ')
    print(f"Event exists check (expect True):  {event_exists('2026-04-22', 'Tercero', 'Lunch', 'BYO Mongolian BBQ')}")

    # --- Test: query stored items ---
    rows = get_all_menu_items('2026-04-22')
    print(f"Stored menu items for 2026-04-22: {len(rows)}")
