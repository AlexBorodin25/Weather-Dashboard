import sqlite3

DB_PATH = os.path.join(BASE_DIR, "weather.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            country TEXT,
            temperature REAL,
            humidity INTEGER,
            feels_like REAL,
            description TEXT,
            icon TEXT,
            wind_speed REAL,
            searched_at TEXT NOT NULL,)
            """
        )