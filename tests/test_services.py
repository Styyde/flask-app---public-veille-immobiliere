# tests/test_services.py
import pytest
from services.listings_service import get_all_listings
from services.stats_service import get_stats_distribution, get_histogram_prix_m2
from services.location_service import get_location_hierarchy, get_all_sublocations_for
from services.type_mapping import get_normalized_type, get_brut_types_for_normalized, get_all_normalized_types
from services.task_service import start_scraping_task
from database.db_manager import create_task, get_task_status
import uuid
from unittest.mock import patch, MagicMock

# ---- type_mapping ----

def test_get_normalized_type():
    assert get_normalized_type('Appartements') == 'Appartement'
    assert get_normalized_type('Magasins et commerces') == 'Commercial'
    assert get_normalized_type('Terrain') == 'Terrain'
    assert get_normalized_type('Restaurant') == 'Commercial'
    assert get_normalized_type('Inconnu') == 'Inconnu'
    assert get_normalized_type(None) is None

def test_get_brut_types_for_normalized():
    bruts = get_brut_types_for_normalized('Commercial')
    assert 'Magasins et commerces' in bruts
    assert 'Lots d\'activités commerciales' in bruts

def test_get_all_normalized_types():
    types = get_all_normalized_types()
    assert isinstance(types, list)
    assert len(types) > 0

# ---- listings_service ----

def test_get_all_listings(app):
    listings = get_all_listings()
    assert len(listings) > 0
    sources = {l['source'] for l in listings}
    # Le nom exact est 'Al Omrane' (avec un espace)
    assert 'Al Omrane' in sources
    assert 'Sarouty' in sources
    assert 'Mubawab' in sources

# ---- stats_service ----

def test_get_stats_distribution(app):
    stats = get_stats_distribution(grouper='type_bien')
    assert len(stats) > 0
    for s in stats:
        assert 'groupe' in s
        assert 'nb_produits' in s
        assert 'prix_m2_moyen' in s
    stats = get_stats_distribution(grouper='localisation')
    assert len(stats) > 0

def test_get_stats_distribution_avec_filtre(app):
    stats = get_stats_distribution(grouper='type_bien', filtre_ville='Casablanca')
    assert len(stats) > 0

def test_get_histogram_prix_m2(app):
    hist = get_histogram_prix_m2()
    assert 'labels' in hist
    assert 'counts' in hist
    assert 'seuil_opportunite' in hist

def test_get_histogram_prix_m2_avec_filtres(app):
    hist = get_histogram_prix_m2(filtre_ville='Casablanca', filtre_type='Appartements')
    assert 'labels' in hist

# ---- location_service ----

def test_get_location_hierarchy(app):
    hierarchy = get_location_hierarchy()
    assert len(hierarchy) > 0

def test_get_all_sublocations_for(app):
    subs = get_all_sublocations_for('Casablanca-Settat')
    assert isinstance(subs, list)

# ---- task_service ----

def test_start_scraping_task_sync():
    def fake_target():
        return "done"
    task_id = str(uuid.uuid4())
    create_task(task_id, 'test', 'Starting')
    with patch('threading.Thread') as mock_thread:
        mock_thread.return_value.start = MagicMock()
        start_scraping_task(task_id, 'test', False, fake_target)
        mock_thread.assert_called_once()
    status = get_task_status(task_id)
    assert status is not None