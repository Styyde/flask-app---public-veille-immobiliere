# tests/test_health.py
import json
import sqlite3

def test_health_endpoint_success(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['database'] == 'ok'

def test_health_endpoint_db_failure(monkeypatch, client):
    def failing_connect(*args, **kwargs):
        raise sqlite3.OperationalError("Fake DB error")
    monkeypatch.setattr('sqlite3.connect', failing_connect)
    response = client.get('/health')
    assert response.status_code == 503
    data = json.loads(response.data)
    assert data['status'] == 'unhealthy'
    assert 'error' in data['database']