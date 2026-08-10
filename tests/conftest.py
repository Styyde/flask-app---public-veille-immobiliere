# tests/conftest.py
import os
import sys
import tempfile
import pytest
import sqlite3

# ---- 1. Ajouter le chemin racine au PYTHONPATH ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 2. Configurer une base temporaire AVANT d'importer api.app ----
import config
db_fd, db_path = tempfile.mkstemp(suffix='.db')
config.DB_PATH = db_path

# ---- 3. Maintenant on peut importer l'application (init_db() utilisera la bonne base) ----
from api.app import app as flask_app
from database.db_manager import init_db, get_connection

# ---- 4. Données de test ----
TEST_PROJETS = [
    {
        "url": "https://test.ma/projet1",
        "region": "Casablanca-Settat",
        "type_bien": "Appartements",
        "titre": "Résidence A",
        "localisation": "Casablanca",
        "titre_foncier": "TF1",
        "description": "Projet test",
        "lots": [
            {
                "titre": "Lot 1",
                "nb_unites": "5 unités",
                "prix_min": "500 000 DH",
                "prix_max": "800 000 DH",
                "lignes": [
                    {"no_produit": "A1", "surface": "100 m²", "prix": "600 000 DH"},
                    {"no_produit": "A2", "surface": "120 m²", "prix": "720 000 DH"},
                ]
            }
        ]
    },
    {
        "url": "https://test.ma/projet2",
        "region": "Rabat-Salé-Kénitra",
        "type_bien": "Magasins et commerces",
        "titre": "Centre Commercial B",
        "localisation": "Rabat",
        "titre_foncier": "TF2",
        "description": "Projet commercial",
        "lots": [
            {
                "titre": "Lot 2",
                "nb_unites": "3 unités",
                "prix_min": "1 000 000 DH",
                "prix_max": "1 500 000 DH",
                "lignes": [
                    {"no_produit": "B1", "surface": "80 m²", "prix": "1 200 000 DH"},
                    {"no_produit": "B2", "surface": "100 m²", "prix": "1 400 000 DH"},
                ]
            }
        ]
    },
    {
        "url": "https://test.ma/projet3",
        "region": "Casablanca-Settat",
        "type_bien": "Lots de terrains pour habitat",
        "titre": "Lotissement C",
        "localisation": "Mohammedia",
        "titre_foncier": "TF3",
        "description": "Terrain",
        "lots": [
            {
                "titre": "Lot 3",
                "nb_unites": "2 unités",
                "prix_min": "300 000 DH",
                "prix_max": "400 000 DH",
                "lignes": [
                    {"no_produit": "C1", "surface": "200 m²", "prix": "350 000 DH"},
                    {"no_produit": "C2", "surface": "250 m²", "prix": "400 000 DH"},
                ]
            }
        ]
    }
]

TEST_SAROUTY = [
    {"property_id": 101, "url_annonce": "http://sarouty.ma/101", "titre": "Villa Sarouty", "description": "belle", "prix": 2500000, "superficie": 200, "type_bien": "Villa", "quartier": "Anfa", "ville": "Casablanca"},
    {"property_id": 102, "url_annonce": "http://sarouty.ma/102", "titre": "Appart Sarouty", "description": "centre", "prix": 800000, "superficie": 80, "type_bien": "Appartement", "quartier": "Agdal", "ville": "Rabat"},
]

TEST_MUBAWAB = [
    {"url_annonce": "http://mubawab.ma/201", "titre": "Terrain Mubawab", "description": "constructible", "prix": 600000, "superficie": 300, "type_bien": "Terrain", "localisation": "Souissi", "ville": "Rabat", "region": "Rabat-Salé-Kénitra"},
    {"url_annonce": "http://mubawab.ma/202", "titre": "Local commercial", "description": "boutique", "prix": 900000, "superficie": 50, "type_bien": "Local commercial", "localisation": "Mers Sultan", "ville": "Casablanca", "region": "Casablanca-Settat"},
]

# ---- 5. Fonction de peuplement ----
def populate_test_db():
    conn = get_connection()
    cursor = conn.cursor()

    for projet in TEST_PROJETS:
        cursor.execute("""
            INSERT INTO projets (url, region, type_bien, titre, localisation, titre_foncier, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (projet["url"], projet["region"], projet["type_bien"], projet["titre"],
              projet["localisation"], projet["titre_foncier"], projet["description"]))
        projet_id = cursor.lastrowid
        for lot in projet["lots"]:
            cursor.execute("""
                INSERT INTO lots (projet_id, lot_titre, nb_unites, prix_min, prix_max)
                VALUES (?, ?, ?, ?, ?)
            """, (projet_id, lot["titre"], lot["nb_unites"], lot["prix_min"], lot["prix_max"]))
            lot_id = cursor.lastrowid
            for ligne in lot["lignes"]:
                cursor.execute("""
                    INSERT INTO produits (lot_id, no_produit, surface, prix)
                    VALUES (?, ?, ?, ?)
                """, (lot_id, ligne["no_produit"], ligne["surface"], ligne["prix"]))

    for annonce in TEST_SAROUTY:
        cursor.execute("""
            INSERT OR IGNORE INTO annonces_sarouty
            (property_id, url_annonce, titre, description, prix, superficie, type_bien, quartier, ville)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (annonce["property_id"], annonce["url_annonce"], annonce["titre"],
              annonce["description"], annonce["prix"], annonce["superficie"],
              annonce["type_bien"], annonce["quartier"], annonce["ville"]))

    for annonce in TEST_MUBAWAB:
        cursor.execute("""
            INSERT OR IGNORE INTO annonces_mubawab
            (url_annonce, titre, description, prix, superficie, type_bien, localisation, ville, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (annonce["url_annonce"], annonce["titre"], annonce["description"],
              annonce["prix"], annonce["superficie"], annonce["type_bien"],
              annonce["localisation"], annonce["ville"], annonce["region"]))

    conn.commit()
    conn.close()

# ---- 6. Fixtures ----
@pytest.fixture(scope='session', autouse=True)
def setup_db():
    """Initialise et peuple la base temporaire pour toute la session de tests."""
    init_db()          # Crée les tables dans la base temporaire
    populate_test_db() # Insère les données de test
    yield
    # Nettoyage à la fin de la session de tests
    try:
        os.close(db_fd)
        os.unlink(db_path)
    except:
        pass

@pytest.fixture
def client():
    """Client de test Flask."""
    return flask_app.test_client()

@pytest.fixture
def app():
    """Instance de l'application (pour les éventuels besoins)."""
    return flask_app