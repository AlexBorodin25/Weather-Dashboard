import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

import requests
from fastapi import FastAPI, Form, Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "weather.db")
MAX_HISTORY = 5
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
OPENWEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

app = FastAPI(title="Weather App")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static"), name="static")

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

def fetch_weather(city: str) -> dict:
    if not OPENWEATHER_API_KEY:
        return {"error": "API key is missing. Set it as an environment variable."}

    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    try:
        resp = requests.get(OPENWEATHER_URL, params=params, timeout=10)
    except requests.RequestException as exc:
        return {"error": f"Could not reach OpenWeather: {exc}"}

    if resp.status_code == 404:
        return {"error": f"City '{city}' not found"}
    if resp.status_code == 401:
        return {"error": "API key is invalid."}
    if resp.status_code != 200:
        return {"error": f"API error: {resp.status_code}"}

    payload = resp.json()
    return {
        "city": payload.get("name", city),
        "country": payload.get("sys", {}).get("country", ""),
        "temperature": payload["main"]["temp"],
        "humidity": payload["main"]["humidity"],
        "feels_like": payload["main"]["feels_like"],
        "description": payload["weather"][0]["description"].title(),
        "icon": payload["weather"][0]["icon"],
        "wind_speed": payload["wind"]["speed"],
    }

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "weather": None,
            "error": None,
            "history": get_history(),
        },
    )

@app.post("/")
def search(request: Request, city: str = Form(...)):
    city = city.strip()
    weather = None
    error = None

    if not city:
        error = "City is required."
    else:
        result = fetch_weather(city)
        if "error" in result:
            error = result["error"]
        else:
            weather = result
            save_search(result)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "weather": weather,
            "error": error,
            "history": get_history(),
        },
    )

@app.get("/clear")
def clear_history():
    with get_db() as conn:
        conn.execute("DELETE FROM searches")
    return RedirectResponse(url="/", status_code=303)