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

def test_fetch_weather_invalid_API_key(monkeypatch):
    class FakeResponse:
        status_code = 401

    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "fake-key")
    monkeypatch.setattr(app_module.requests, "get", lambda *args, **kwargs: FakeResponse())

    result = app_module.fetch_weather("London")

    assert result["error"] == "API key is invalid."

def test_fetch_weather_city_not_founds(monkeypatch):
    class FakeResponse:
        status_code = 404

    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "fake-key")
    monkeypatch.setattr(app_module.requests, "get", lambda *args, **kwargs: FakeResponse())

    result = app_module.fetch_weather("FakeCity")

    assert result["error"] == "City 'FakeCity' not found."

def test_fetch_weather(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "name": "London",
                "sys": {"country": "UK"},
                "main": {
                    "temp": 31.83,
                    "humidity": 29,
                    "feels_like": 30.52,
                },
                "weather": [
                    {
                        "description": "Scattered Clouds",
                        "icon": "o1d",
                    }
                ],
                "wind": {"speed": 3.13},
            }

    def fake_get(url, params, timeout):
        assert url == app_module.OPENWEATHER_URL
        assert params["q"] == "London"
        assert params["units"] == "metric"
        assert params["appid"] == "fake-key"
        assert timeout == 10
        return FakeResponse()

    monkeypatch.setattr(app_module, "OPENWEATHER_API_KEY", "fake-key")
    monkeypatch.setattr(app_module.requests, "get", fake_get)

    result = app_module.fetch_weather("London")

    assert result["city"] == "London"
    assert result["country"] == "UK"
    assert result["temperature"] == 31.83
    assert result["humidity"] == 29
    assert result["feels_like"] == 30.52
    assert result["description"] == "Scattered Clouds"
    assert result["icon"] == "o1d"
    assert result["wind_speed"] == 3.13

def test_index_renders_html(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Weather Dashboard" in response.text
    assert "Enter city name" in response.text
    assert "No searches yet." in response.text

def test_index_shows_history(client):
    app_module.save_search(
        {
            "city": "London",
            "country": "UK",
            "temperature": 31.83,
            "humidity": 29,
            "feels_like": 30.52,
            "description": "Scattered Clouds",
            "icon": "o1d",
            "wind_speed": 3.13,
        }
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "Last 1 Search" in response.text
    assert "London, UK" in response.text
    assert "31.83" in response.text
    assert "Scattered Clouds" in response.text
    assert "Clear history" in response.text

def test_search_empty_city(client):
    response = client.post("/", data={"city": "   "})

    assert response.status_code == 200
    assert "City is required." in response.text

def test_search_API_error(client, monkeypatch):
    monkeypatch.setattr(app_module, "fetch_weather", lambda city: {"error": "City not found"})

    response = client.post("/", data={"city": "Unknown"})

    assert response.status_code == 200
    assert "City not found" in response.text

def test_search_success(client, monkeypatch):
    fake_weather = {
        "city": "London",
        "country": "UK",
        "temperature": 31.83,
        "humidity": 29,
        "feels_like": 30.52,
        "description": "Scattered Clouds",
        "icon": "o1d",
        "wind_speed": 3.13,
    }

    monkeypatch.setattr(app_module, "fetch_weather", lambda city: fake_weather)

    response = client.post("/", data={"city": "London"})

    assert response.status_code == 200
    assert "London, UK" in response.text
    assert "31.83" in response.text
    assert "Scattered Clouds" in response.text
    assert "Humidity: 29%" in response.text
    assert "Wind speed: 3.13" in response.text
    assert "Last 1 Search" in response.text

def test_clear_history(client):
    app_module.save_search(
        {
            "city": "London",
            "country": "UK",
            "temperature": 31.83,
            "humidity": 29,
            "feels_like": 30.52,
            "description": "Scattered Clouds",
            "icon": "o1d",
            "wind_speed": 3.13,
        }
    )

    response = client.get("/clear", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert app_module.get_history() == []