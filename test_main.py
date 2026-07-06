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