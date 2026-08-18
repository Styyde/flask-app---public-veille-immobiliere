# tests/test_routes.py
import json
from unittest.mock import patch

# ---- Routes existantes ----

def test_metrics_endpoint(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    assert 'flask_http_request_duration_seconds' in content
    assert 'flask_http_request_total' in content
    assert 'app_info' in content

def test_stats_endpoint(client):
    response = client.get('/api/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    expected_keys = [
        'nb_projets', 'nb_lots', 'nb_produits',
        'nb_sarouty', 'nb_mubawab', 'nb_favoris'
    ]
    for key in expected_keys:
        assert key in data
    # Après l'ajout du projet4, les compteurs ont augmenté
    assert data['nb_projets'] >= 4
    assert data['nb_lots'] >= 4
    assert data['nb_produits'] >= 8
    assert data['nb_sarouty'] >= 3
    assert data['nb_mubawab'] >= 3

def test_options_endpoint(client):
    response = client.get('/api/options?source=all')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'villes' in data
    assert 'types' in data
    assert 'Casablanca' in data['villes']
    assert 'Rabat' in data['villes']
    assert len(data['types']) > 0

def test_analytics_endpoint(client):
    response = client.get('/api/analytics')
    assert response.status_code == 200
    data = json.loads(response.data)
    expected_keys = ['histogram', 'comparaison', 'opportunites', 'scatter']
    for key in expected_keys:
        assert key in data

def test_alomrane_produits_sans_filtre(client):
    response = client.get('/api/alomrane/produits')
    assert response.status_code == 200
    data = json.loads(response.data)
    # 8 produits maintenant (projet4 ajouté)
    assert len(data) == 8

def test_sarouty_annonces_sans_filtre(client):
    response = client.get('/api/sarouty/annonces')
    assert response.status_code == 200
    data = json.loads(response.data)
    # 3 annonces Sarouty (originales 2 + nouvelle)
    assert len(data) == 3

def test_mubawab_annonces_sans_filtre(client):
    response = client.get('/api/mubawab/annonces')
    assert response.status_code == 200
    data = json.loads(response.data)
    # 3 annonces Mubawab (originales 2 + nouvelle)
    assert len(data) == 3

def test_alomrane_produits_avec_filtre_compose(client):
    params = {
        'ville': 'Casablanca',
        'budget_min': '700000',
        'surface_max': '120'
    }
    response = client.get('/api/alomrane/produits', query_string=params)
    assert response.status_code == 200
    data = json.loads(response.data)
    # Seul A2 (Casablanca, 720k, 120) correspond
    assert len(data) == 1
    assert data[0]['produit'] == 'A2'

# ---- Nouveaux tests ----

def test_alomrane_projets(client):
    response = client.get('/api/alomrane/projets')
    assert response.status_code == 200
    data = json.loads(response.data)
    # 4 projets maintenant
    assert len(data) == 4
    projet = data[0]
    assert 'id' in projet
    assert 'titre' in projet
    assert 'localisation' in projet
    assert 'nb_lots' in projet
    assert 'nb_produits' in projet

def test_alomrane_projet_detail(client):
    response = client.get('/api/alomrane/projets')
    projets = json.loads(response.data)
    projet_id = projets[0]['id']
    response = client.get(f'/api/alomrane/projets/{projet_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == projet_id
    assert 'titre' in data
    assert 'lots' in data
    assert len(data['lots']) > 0
    lot = data['lots'][0]
    assert 'lignes' in lot
    assert len(lot['lignes']) > 0

def test_alomrane_projet_detail_not_found(client):
    response = client.get('/api/alomrane/projets/99999')
    assert response.status_code == 404

def test_moyennes_endpoint(client):
    response = client.get('/api/moyennes')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'moyenne' in data
    assert 'ecart_type' in data
    assert 'nombre' in data
    response = client.get('/api/moyennes?ville=Casablanca')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['nombre'] > 0
    response = client.get('/api/moyennes?type_bien=Commercial')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['nombre'] == 2

# ---- Tests Favoris ----

def test_favoris_ajout(client):
    payload = {
        'source': 'sarouty',
        'annonce_id': '101',
        'url': 'http://sarouty.ma/101',
        'titre': 'Villa Sarouty',
        'localisation': 'Casablanca',
        'type_bien': 'Villa',
        'surface': '200 m²',
        'prix': '2500000 DH',
        'prix_m2': 12500
    }
    response = client.post('/api/favoris', json=payload)
    assert response.status_code in (200, 201)
    response = client.get('/api/favoris')
    favoris = json.loads(response.data)
    assert any(f['annonce_id'] == '101' and f['source'] == 'sarouty' for f in favoris)

def test_favoris_ajout_deja_present(client):
    payload = {
        'source': 'mubawab',
        'annonce_id': '201',
        'url': 'http://mubawab.ma/201',
        'titre': 'Terrain Mubawab',
        'localisation': 'Rabat',
        'type_bien': 'Terrain',
        'surface': '300 m²',
        'prix': '600000 DH'
    }
    client.post('/api/favoris', json=payload)
    response = client.post('/api/favoris', json=payload)
    assert response.status_code in (200, 409)

def test_favoris_ajout_missing_fields(client):
    payload = {'source': 'sarouty'}
    response = client.post('/api/favoris', json=payload)
    assert response.status_code == 400

def test_favoris_suppression(client):
    payload = {'source': 'sarouty', 'annonce_id': '102', 'titre': 'Appart Sarouty'}
    client.post('/api/favoris', json=payload)
    response = client.delete('/api/favoris?source=sarouty&annonce_id=102')
    assert response.status_code == 200
    response = client.get('/api/favoris')
    favoris = json.loads(response.data)
    assert not any(f['annonce_id'] == '102' and f['source'] == 'sarouty' for f in favoris)

def test_favoris_suppression_inexistant(client):
    response = client.delete('/api/favoris?source=sarouty&annonce_id=999')
    assert response.status_code == 404

def test_favoris_set(client):
    client.post('/api/favoris', json={'source': 'sarouty', 'annonce_id': '101'})
    client.post('/api/favoris', json={'source': 'mubawab', 'annonce_id': '201'})
    response = client.get('/api/favoris/set')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'sarouty' in data
    assert 'mubawab' in data
    assert '101' in data['sarouty']
    assert '201' in data['mubawab']

def test_favoris_check(client):
    client.post('/api/favoris', json={'source': 'sarouty', 'annonce_id': '101'})
    response = client.get('/api/favoris/check/sarouty/101')
    assert response.status_code == 200
    assert json.loads(response.data)['favori'] is True
    response = client.get('/api/favoris/check/sarouty/999')
    assert response.status_code == 200
    assert json.loads(response.data)['favori'] is False

# ---- Tests Scraping ----

def test_scraper_alomrane_validation(client):
    response = client.post('/api/scraper', json={})
    assert response.status_code == 400
    assert 'Aucune région sélectionnée' in response.json['error']
    response = client.post('/api/scraper', json={'region_ids': [999]})
    assert response.status_code == 400
    assert 'Région(s) invalide(s)' in response.json['error']

@patch('api.app.start_scraping_task')
def test_scraper_alomrane_valid(mock_start, client):
    response = client.post('/api/scraper', json={'region_ids': [78], 'deep': False})
    assert response.status_code == 200
    data = response.json
    assert 'task_id' in data
    assert 'message' in data
    mock_start.assert_called_once()
    task_id = data['task_id']
    from database.db_manager import get_task_status
    status = get_task_status(task_id)
    assert status is not None
    assert status['status'] == 'en_cours'

@patch('api.app.start_scraping_task')
def test_scraper_sarouty_valid(mock_start, client):
    response = client.post('/api/scraper_sarouty', json={'region': 'casablanca', 'max_pages': 2})
    assert response.status_code == 200
    data = response.json
    assert 'task_id' in data
    mock_start.assert_called_once()
    args, kwargs = mock_start.call_args
    # args[1] = source
    assert args[1] == 'Sarouty'

@patch('api.app.start_scraping_task')
def test_scraper_mubawab_valid(mock_start, client):
    response = client.post('/api/scraper_mubawab', json={'region': 'rabat', 'max_pages': 3})
    assert response.status_code == 200
    data = response.json
    assert 'task_id' in data
    mock_start.assert_called_once()

def test_scraper_mubawab_invalid_region(client):
    response = client.post('/api/scraper_mubawab', json={'region': 'tanger'})
    assert response.status_code == 400
    assert 'Région invalide' in response.json['error']

def test_scraper_status(client):
    with patch('api.app.start_scraping_task'):
        response = client.post('/api/scraper', json={'region_ids': [78]})
        task_id = response.json['task_id']
    response = client.get(f'/api/scraper/status/{task_id}')
    assert response.status_code == 200
    data = response.json
    assert data['id'] == task_id
    assert 'status' in data
    assert 'message' in data

def test_scraper_status_not_found(client):
    response = client.get('/api/scraper/status/invalid-id')
    assert response.status_code == 404

# ---- Route Legacy ----

def test_filtrer_legacy(client):
    response = client.get('/api/filtrer?source=all&ville=Casablanca')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    for item in data:
        ville = item.get('ville', '')
        localisation = item.get('localisation', '')
        region = item.get('region', '')
        assert ('Casablanca' in ville or 'Casablanca' in localisation or region == 'Casablanca-Settat')

def test_filtrer_legacy_source_sarouty(client):
    response = client.get('/api/filtrer?source=sarouty')
    assert response.status_code == 200
    data = json.loads(response.data)
    for item in data:
        assert item.get('source') == 'Sarouty'