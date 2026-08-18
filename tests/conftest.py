# tests/conftest.py
import os
import sys
import tempfile
import pytest

# ---- 1. Ajouter le chemin racine au PYTHONPATH ----
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 2. Configurer une base temporaire AVANT d'importer api.app ----
import config
db_fd, db_path = tempfile.mkstemp(suffix='.db')
config.DB_PATH = db_path

# ---- 3. Maintenant on peut importer l'application (init_db() utilisera la bonne base) ----
from api.app import app as flask_app
from database.db_manager import init_db
from database.models import AnnonceMubawab, AnnonceSarouty, Lot, Produit, Projet
from database.session import session_scope

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
    with session_scope() as session:
        for projet in TEST_PROJETS:
            projet_obj = Projet(
                url=projet["url"], region=projet["region"], type_bien=projet["type_bien"],
                titre=projet["titre"], localisation=projet["localisation"],
                titre_foncier=projet["titre_foncier"], description=projet["description"],
            )
            for lot in projet["lots"]:
                lot_obj = Lot(
                    lot_titre=lot["titre"], nb_unites=lot["nb_unites"],
                    prix_min=lot["prix_min"], prix_max=lot["prix_max"],
                )
                for ligne in lot["lignes"]:
                    lot_obj.produits.append(Produit(
                        no_produit=ligne["no_produit"], surface=ligne["surface"], prix=ligne["prix"],
                    ))
                projet_obj.lots.append(lot_obj)
            session.add(projet_obj)

        for annonce in TEST_SAROUTY:
            session.add(AnnonceSarouty(**annonce))

        for annonce in TEST_MUBAWAB:
            session.add(AnnonceMubawab(**annonce))

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