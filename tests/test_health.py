# tests/test_health.py
import json

def test_health_endpoint_success(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['database'] == 'ok'

def test_health_endpoint_db_failure(monkeypatch, client):
    import api.app as app_module

    def failing_get_engine():
        raise RuntimeError("Fake DB error")
    monkeypatch.setattr(app_module, 'get_engine', failing_get_engine)
    response = client.get('/health')
    assert response.status_code == 503
    data = json.loads(response.data)
    assert data['status'] == 'unhealthy'
    assert 'error' in data['database']