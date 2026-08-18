# tests/test_filters.py
import json
import re


def extraire_nombre(chaine):
    if isinstance(chaine, (int, float)):
        return float(chaine)
    if not chaine:
        return 0.0
    propre = re.sub(r'[^\d.,]', '', str(chaine))
    propre = propre.replace(',', '.')
    try:
        return float(propre)
    except ValueError:
        return 0.0

def extraire_surface(chaine):
    return extraire_nombre(chaine)

def extraire_prix(chaine):
    return extraire_nombre(chaine)

# ---- Al Omrane ----

def test_filter_alomrane_ville(client):
    resp = client.get('/api/alomrane/produits?ville=Casablanca')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    # Maintenant 4 produits à Casablanca (projet1: A1,A2 + projet4: D1,D2)
    assert len(data) == 4
    for p in data:
        assert p['ville'] == 'Casablanca'

def test_filter_alomrane_ville_inexistante(client):
    resp = client.get('/api/alomrane/produits?ville=Inexistante')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []

def test_filter_alomrane_budget_min(client):
    resp = client.get('/api/alomrane/produits?budget_min=700000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) >= 3
    for p in data:
        prix = extraire_prix(p['prix'])
        assert prix >= 700000

def test_filter_alomrane_budget_max(client):
    resp = client.get('/api/alomrane/produits?budget_max=800000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 6
    for p in data:
        prix = extraire_prix(p['prix'])
        assert prix <= 800000

def test_filter_alomrane_budget_min_max(client):
    resp = client.get('/api/alomrane/produits?budget_min=600000&budget_max=1000000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        prix = extraire_prix(p['prix'])
        assert 600000 <= prix <= 1000000

def test_filter_alomrane_surface_min(client):
    resp = client.get('/api/alomrane/produits?surface_min=150')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        surf = extraire_surface(p['surface'])
        assert surf >= 150

def test_filter_alomrane_surface_max(client):
    resp = client.get('/api/alomrane/produits?surface_max=120')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 6
    for p in data:
        surf = extraire_surface(p['surface'])
        assert surf <= 120

def test_filter_alomrane_prix_m2_min(client):
    resp = client.get('/api/alomrane/produits?prix_m2_min=10000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        assert p['prix_m2'] >= 10000

def test_filter_alomrane_prix_m2_max(client):
    resp = client.get('/api/alomrane/produits?prix_m2_max=7000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 6
    for p in data:
        assert p['prix_m2'] <= 7000

def test_filter_alomrane_combinaison_ville_budget(client):
    resp = client.get('/api/alomrane/produits?ville=Casablanca&budget_min=700000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 1
    assert data[0]['produit'] == 'A2'

def test_filter_alomrane_combinaison_surface_prix_m2(client):
    resp = client.get('/api/alomrane/produits?surface_max=100&prix_m2_min=10000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        surf = extraire_surface(p['surface'])
        assert surf <= 100
        assert p['prix_m2'] >= 10000

def test_filter_alomrane_type_normalise_commercial(client):
    resp = client.get('/api/alomrane/produits?type_bien=Commercial')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        assert p['projet'] == 'Centre Commercial B'

def test_filter_alomrane_type_normalise_terrain(client):
    resp = client.get('/api/alomrane/produits?type_bien=Terrain')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        assert p['projet'] == 'Lotissement C'

def test_filter_alomrane_trie_prix_m2(client):
    resp = client.get('/api/alomrane/produits')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    prix_m2 = [p['prix_m2'] for p in data]
    assert prix_m2 == sorted(prix_m2)

# ---- Sarouty ----

def test_filter_sarouty_ville(client):
    resp = client.get('/api/sarouty/annonces?ville=Casablanca')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        assert 'Casablanca' in p['localisation']

def test_filter_sarouty_budget_min(client):
    resp = client.get('/api/sarouty/annonces?budget_min=1000000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 1
    prix = extraire_prix(data[0]['prix'])
    assert prix >= 1000000

def test_filter_sarouty_budget_max(client):
    resp = client.get('/api/sarouty/annonces?budget_max=1000000')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        prix = extraire_prix(p['prix'])
        assert prix <= 1000000

# ---- Mubawab (tests robustes) ----

def test_filter_mubawab_ville(client):
    resp = client.get('/api/mubawab/annonces?ville=Rabat')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for p in data:
        localisation = p.get('localisation', '')
        region = p.get('region', '')
        ville = p.get('ville', '')
        assert 'Rabat' in localisation or 'Rabat' in ville or region == 'Rabat-Salé-Kénitra'

# ---- Cas limites ----

def test_filter_negatif_budget(client):
    resp = client.get('/api/alomrane/produits?budget_min=-100')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 8

def test_filter_tres_grand_budget(client):
    resp = client.get('/api/alomrane/produits?budget_max=999999999')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 8

def test_filter_avec_source_sarouty_et_ville(client):
    resp = client.get('/api/sarouty/annonces?ville=Inexistante')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []