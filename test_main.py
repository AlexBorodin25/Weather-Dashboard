import sqlite3

import pytest
import requests
from fastapi.testclient import TestClient

import main as app_module

@pytest.fixture
def test_db(tmp_path,monkeypatch):
    test_db_path = tmp_path / "test_weather.db"
    monkeypatch.setattr(app_module, "DB_FILE", str(test_db_path))
    app_module.init_db()
    return test_db_path

@pytest.fixture
def client(test_db):
    return TestClient(app_module.app)

@def test_get_db_connection(test_db):
    with app.module.get_db() as conn:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

def test_init_db_creates_table(test_db):
    with app_module.get_db() as conn:
        results = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='searches'"
        ).fetchone()

        assert result is not None
        assert results["name"] == "searches"