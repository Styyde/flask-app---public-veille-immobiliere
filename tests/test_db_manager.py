# tests/test_db_manager.py
import json
import uuid
import pytest
from database.db_manager import (
    get_connection,
    get_existing_urls,
    save_projets,
    save_annonces_sarouty,
    save_annonces_mubawab,
    get_projet_detail,
    get_projets_resume,
    get_annonces_sarouty_filtered,
    get_annonces_mubawab_filtered,
    get_statistiques_globales,
    get_prix_m2_stats,
    ajouter_favori,
    supprimer_favori,
    get_favoris,
    est_favori,
    get_favoris_set,
    create_task,
    update_task_status,
    get_task_status,
)

def test_get_existing_urls(app):
    urls = get_existing_urls()
    # Après l'ajout du projet4 dans test_save_projets, il y a 4 projets
    # Mais ce test s'exécute avant, donc il y a encore 3 projets
    assert len(urls) >= 3
    assert 'https://test.ma/projet1' in urls

def test_save_projets(app):
    nouveau_projet = [{
        "lien": "https://test.ma/projet4",
        "region": "Casablanca-Settat",
        "type_bien": "Appartements",
        "titre": "Résidence D",
        "localisation": "Casablanca",
        "titre_foncier": "TF4",
        "description": "Nouveau projet",
        "lots": [{
            "titre": "Lot 4",
            "nb_unites": "2 unités",
            "prix_min": "400 000 DH",
            "prix_max": "600 000 DH",
            "lignes": [
                {"no_produit": "D1", "surface": "90 m²", "prix": "500 000 DH"},
                {"no_produit": "D2", "surface": "110 m²", "prix": "550 000 DH"}
            ]
        }]
    }]
    inserted = save_projets(nouveau_projet)
    assert inserted == 1
    urls = get_existing_urls()
    assert 'https://test.ma/projet4' in urls

def test_save_annonces_sarouty(app):
    nouvelles = [
        {"property_id": 103, "url_annonce": "http://sarouty.ma/103", "titre": "Test Sarouty",
         "description": "test", "prix": 500000, "superficie": 70, "type_bien": "Appartement",
         "quartier": "Centre", "ville": "Casablanca"}
    ]
    inserted = save_annonces_sarouty(nouvelles)
    assert inserted == 1
    rows = get_annonces_sarouty_filtered(ville='Casablanca')
    # Maintenant il y a 2 annonces à Casablanca (l'originale + la nouvelle)
    assert len(rows) >= 2
    assert any(row['property_id'] == 103 for row in rows)

def test_save_annonces_mubawab(app):
    nouvelles = [
        {"url_annonce": "http://mubawab.ma/203", "titre": "Test Mubawab",
         "description": "test", "prix": 700000, "superficie": 120,
         "type_bien": "Villa", "localisation": "Agdal", "ville": "Rabat",
         "region": "Rabat-Salé-Kénitra"}
    ]
    inserted = save_annonces_mubawab(nouvelles)
    assert inserted == 1
    rows = get_annonces_mubawab_filtered(ville='Rabat')
    # Maintenant il y a 2 annonces à Rabat
    assert len(rows) >= 2
    assert any(row['url_annonce'] == 'http://mubawab.ma/203' for row in rows)

def test_get_projet_detail(app):
    projets = get_projets_resume()
    projet_id = projets[0]['id']
    detail = get_projet_detail(projet_id)
    assert detail is not None
    assert 'id' in detail
    assert 'lots' in detail
    assert len(detail['lots']) > 0
    assert 'lignes' in detail['lots'][0]

def test_get_projets_resume(app):
    result = get_projets_resume(limit=2)
    assert len(result) == 2
    for r in result:
        assert 'id' in r
        assert 'titre' in r
        assert 'nb_lots' in r
        assert 'nb_produits' in r

def test_get_projets_resume_avec_filtres(app):
    result = get_projets_resume(ville='Casablanca', budget_min=700000)
    # Il y a maintenant 2 projets à Casablanca (projet1 et projet4)
    assert len(result) >= 1
    for r in result:
        assert r['localisation'] == 'Casablanca'
        assert r['prix_m2_min'] is not None

def test_get_annonces_sarouty_filtered(app):
    rows = get_annonces_sarouty_filtered(ville='Casablanca')
    # 2 annonces à Casablanca (originale + celle ajoutée)
    assert len(rows) >= 2
    rows = get_annonces_sarouty_filtered(budget_min=1000000)
    assert len(rows) == 1  # seule la villa à 2.5M

def test_get_annonces_mubawab_filtered(app):
    rows = get_annonces_mubawab_filtered(region='Casablanca-Settat')
    assert len(rows) == 1
    rows = get_annonces_mubawab_filtered(ville='Rabat')
    # 2 annonces à Rabat (originale + celle ajoutée)
    assert len(rows) >= 2

def test_get_statistiques_globales(app):
    stats = get_statistiques_globales()
    # Après l'ajout du projet4, il y a 4 projets
    assert stats['nb_projets'] >= 4
    assert stats['nb_lots'] >= 4
    assert stats['nb_produits'] >= 8
    assert stats['nb_sarouty'] >= 3
    assert stats['nb_mubawab'] >= 3
    assert stats['nb_favoris'] >= 0

def test_get_prix_m2_stats(app):
    stats = get_prix_m2_stats(ville='Casablanca')
    assert stats['nombre'] > 0
    assert stats['moyenne'] > 0

def test_ajouter_favori(app):
    # Supprimer s'il existe déjà
    supprimer_favori('test', '123')
    ajout = ajouter_favori('test', '123', 'http://test.ma', 'Test', 'Rabat', 'Appartement', '100 m²', '500000 DH', 5000)
    assert ajout is True
    favoris = get_favoris()
    assert any(f['annonce_id'] == '123' and f['source'] == 'test' for f in favoris)

def test_ajouter_favori_deja_present(app):
    ajouter_favori('test', '456', 'http://test.ma', 'Test2', 'Rabat', 'Villa', '200 m²', '1000000 DH', 5000)
    ajout = ajouter_favori('test', '456', 'http://test.ma', 'Test2', 'Rabat', 'Villa', '200 m²', '1000000 DH', 5000)
    assert ajout is False

def test_supprimer_favori(app):
    ajouter_favori('test', '789', 'http://test.ma', 'Test3', 'Rabat', 'Terrain', '300 m²', '600000 DH', 2000)
    suppr = supprimer_favori('test', '789')
    assert suppr is True
    favoris = get_favoris()
    assert not any(f['annonce_id'] == '789' and f['source'] == 'test' for f in favoris)

def test_supprimer_favori_inexistant(app):
    suppr = supprimer_favori('test', '999')
    assert suppr is False

def test_get_favoris_set(app):
    # Ajouter quelques favoris avec tous les arguments
    ajouter_favori('source1', 'a1', 'url1', 'Titre1', 'Local1', 'Type1', '100 m²', '100000 DH', 1000)
    ajouter_favori('source1', 'a2', 'url2', 'Titre2', 'Local2', 'Type2', '200 m²', '200000 DH', 2000)
    ajouter_favori('source2', 'b1', 'url3', 'Titre3', 'Local3', 'Type3', '300 m²', '300000 DH', 3000)
    favoris_set = get_favoris_set()
    assert 'source1' in favoris_set
    assert 'a1' in favoris_set['source1']
    assert 'a2' in favoris_set['source1']
    assert 'source2' in favoris_set
    assert 'b1' in favoris_set['source2']

def test_est_favori(app):
    ajouter_favori('test', '555', 'url', 'Titre', 'Local', 'Type', '100 m²', '100000 DH', 1000)
    assert est_favori('test', '555') is True
    assert est_favori('test', '666') is False

def test_create_task(app):
    task_id = str(uuid.uuid4())
    create_task(task_id, 'test_source', 'Initial message')
    status = get_task_status(task_id)
    assert status is not None
    assert status['status'] == 'en_cours'
    assert status['message'] == 'Initial message'

def test_update_task_status(app):
    task_id = str(uuid.uuid4())
    create_task(task_id, 'test_source', 'Démarrage')
    update_task_status(task_id, 'termine', message='Fini', result=42)
    status = get_task_status(task_id)
    assert status['status'] == 'termine'
    assert status['message'] == 'Fini'
    assert status['result'] == 42

def test_get_task_status_not_found(app):
    status = get_task_status('unknown')
    assert status is None