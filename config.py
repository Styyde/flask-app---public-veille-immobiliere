# config.py
# Configuration centrale pour l'application Al Omrane Analyzer
import os

# URLs de base
BASE_URL = "https://www.alomrane.gov.ma/Nos-produits/Projets"

# Régions à scraper (ID utilisé dans le paramètre affiliate[])
REGIONS = [
    {"id": 78, "nom": "Casablanca-Settat"},
    {"id": 414, "nom": "Rabat-Salé-Kénitra"}
]

# Types de biens (Mapping des codes utilisés dans le paramètre type[])
# Copie conforme du mapping original
TYPES_BIENS = {
    "228": "Appartements",
    "27119": "Maisons individuels",
    "27121": "Villas",
    "29228": "Villas semi finis",
    "229": "Lots de terrains pour habitat",
    "29227": "Lots de terrains artisanales",
    "1891": "Lots d'activités industrielles",
    "1892": "Lots d'activités commerciales",
    "3694": "Magasins et commerces",
    "230": "Ilots pour promotion immobilière"
}

# Paramètres du scraper
HEADLESS = True          # Mettre True pour le mode silencieux (planificateur)
LIMITE_PAGES = None       # None pour tout scraper, ou un entier (ex: 2)
DELAI_ENTRE_PAGES = 2     # Secondes d'attente entre les pages
MAX_PAGES_PAR_LOT = 3

# Base de données : utilise la variable d'environnement DB_PATH si définie, sinon "alomrane.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'alomrane.db'))

# ---- Mubawab ----
MUBAWAB_REGIONS = {
    "casablanca": {
        "nom": "Casablanca",
        "url": "https://www.mubawab.ma/fr/ct/casablanca/immobilier-a-vendre-all:o:n:sc:commercial-sale,land-sale,other-sale,riad-sale,villa-sale",
    },
    "rabat": {
        "nom": "Rabat",
        "url": "https://www.mubawab.ma/fr/ct/rabat/immobilier-a-vendre-all:sc:land-sale,riad-sale,villa-sale",
    },
}
MUBAWAB_MAX_PAGES = 3
MUBAWAB_HEADLESS = True