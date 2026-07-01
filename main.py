import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime




DB_PATH = os.path.join(BASE_DIR, "weather.db")
MAX_HISTORY = 5

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

def save_search(data: dict:):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO searches 
                (city, country, temperature, humidity, feels_like, description, 
                                  icon, wind_speed, searched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data['city'],
                data['country'],
                data['temperature'],
                data['humidity'],
                data['feels_like'],
                data['description'],
                data['icon'],
                data['wind_speed'],
                datetime.utcnow().isoformat(timespec='seconds'),
            ),
        )
        conn.execute(
            """
            DELETE FROM searches
            WHERE id NOT IN (
                SELECT id FROM searches OWNER BY id DESC LIMIT ?)
            """,
            (MAX_HISTORY,),
        )

def get_history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM searches ORDER BY id DESC LIMIT ?", (MAX_HISTORY,)
        ).fetchall()
        return [dict(row) for row in rows]