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

if __name__ == '__main__':
    init_db()
    print(f"Database initialized at {DB_PATH}")
