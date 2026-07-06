import sqlite3

import anyio
import pytest
import requests
from fastapi.testclient import TestClient


import main as app_module

@pytest.fixture
def test_db(tmp_path,monkeypatch):
    test_db_path = tmp_path / "test_weather.db"
    monkeypatch.setattr(app_module, "DB_PATH", str(test_db_path))
    app_module.init_db()
    return test_db_path

@pytest.fixture
def client(test_db):
    return TestClient(app_module.app)

def test_get_db_connection(test_db):
    with app_module.get_db() as conn:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

def test_init_db_creates_table(test_db):
    with app_module.get_db() as conn:
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='searches'"
        ).fetchone()

        assert result is not None
        assert result["name"] == "searches"

def test_save_search_weather_data(test_db):
    weather_data = {
        "city": "London",
        "country": "UK",
        "temperature": 31.83,
        "humidity": 29,
        "feels_like": 30.52,
        "description": "Scattered Clouds",
        "icon": "o1d",
        "wind_speed": 3.13,
    }

    app_module.save_search(weather_data)

    history = app_module.get_history()

    assert len(history) == 1
    assert history[0]["city"] == "London"
    assert history[0]["country"] == "UK"
    assert history[0]["temperature"] == 31.83
    assert history[0]["humidity"] == 29
    assert history[0]["feels_like"] == 30.52
    assert history[0]["description"] == "Scattered Clouds"

def test_save_search_max_history(test_db):
    for number in range(5):
        app_module.save_search(
            {
                "city": f"City {number}",
                "country": "UK",
                "temperature": 31.83,
                "humidity": 29,
                "feels_like": 30.52,
                "description": "Scattered Clouds",
                "icon": "o1d",
                "wind_speed": 3.13,
            }
        )

    history = app_module.get_history()

    assert len(history) == app_module.MAX_HISTORY
    assert history[0]["city"] == "City 4"
    assert history[-1]["city"] == "City 0"

def test_history_empty_list(test_db):
    history = app_module.get_history()

    assert history == []

def test_missing_API_key(monkeypatch):
    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "")

    result = app_module.fetch_weather("London")

    assert result["error"] == "API key is missing. Set it as an environment variable."

def test_fetch_weather_request_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.RequestException("Network error")

    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "fake-key")
    monkeypatch.setattr(app_module.requests, "get", fake_get)

    result = app_module.fetch_weather("London")

    assert "Could not reach OpenWeather" in result["error"]

def fetch_weather_invalid_API_key(monkeypatch):
    class FakeResponse:
        status_code = 401

    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "fake-key")
    monkeypatch.setattr(app_module.requests, "get", lambda *args, **kwargs: FakeResponse())

    result = app_module.fetch_weather("London")

    assert result["error"] == "API key is invalid."

def fetch_weather_city_not_founds(monkeypatch):
    class FakeResponse:
        status_code = 404

    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "fake-key")
    monkeypatch.setattr(app_module.requests, "get", lambda *args, **kwargs: FakeResponse())

    result = app_module.fetch_weather("FakeCity")

    assert result["error"] == "City 'FakeCity' not found."