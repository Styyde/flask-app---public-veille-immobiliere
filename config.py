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

# Note : le dashboard d'évolution (prix/m², nombre d'annonces) ne se configure
# plus ici -- les villes suivies sont dérivées dynamiquement des données
# scrapées (voir services/trends_service.get_villes_disponibles).

# ---- Sarouty ----
# `loc` = identifiant interne Sarouty pour la ville, tel qu'utilisé dans l'URL
# de recherche du site (ex: sarouty.ma/recherche/?cat=1&trans=1&loc=55 -> Kénitra).
# `trans` (1=achat/2=location) et `cat` (1=résidentiel/2=commercial) de cette
# même URL correspondent aux filtres "buy_or_rent" et "category" déjà gérés
# par core/sarouty.scraper_sarouty (indépendants de la ville).
SAROUTY_REGIONS = {
    "casablanca": {"nom": "Casablanca", "loc": 35},
    "rabat": {"nom": "Rabat", "loc": 113},
    "kenitra": {"nom": "Kénitra", "loc": 55},
    "sale": {"nom": "Salé", "loc": 103},
}

# ---- Mubawab ----
# Casablanca/Rabat : recherche multi-catégories (villas, terrains, riads...).
# Les villes ci-dessous utilisent des URLs "terrains-a-vendre" (fournies telles
# quelles) -- ce sont des marchés plus petits où seuls les lots de terrain sont
# suivis pour l'instant. Rien n'empêche de repasser sur une URL multi-catégories
# si Mubawab en propose une pour ces villes plus tard.
MUBAWAB_REGIONS = {
    "casablanca": {
        "nom": "Casablanca",
        "url": "https://www.mubawab.ma/fr/ct/casablanca/immobilier-a-vendre-all:o:n:sc:commercial-sale,land-sale,other-sale,riad-sale,villa-sale",
    },
    "rabat": {
        "nom": "Rabat",
        "url": "https://www.mubawab.ma/fr/ct/rabat/immobilier-a-vendre-all:sc:land-sale,riad-sale,villa-sale",
    },
    "kenitra": {
        "nom": "Kénitra",
        "url": "https://www.mubawab.ma/fr/st/k%C3%A9nitra/terrains-a-vendre",
    },
    "sale": {
        "nom": "Salé",
        "url": "https://www.mubawab.ma/fr/st/sal%C3%A9/terrains-a-vendre",
    },
    "rommani": {
        "nom": "Rommani",
        "url": "https://www.mubawab.ma/fr/st/rommani/terrains-a-vendre",
    },
    "khemisset": {
        "nom": "Khémisset",
        "url": "https://www.mubawab.ma/fr/st/kh%C3%A9misset/terrains-a-vendre",
    },
    "bouznika": {
        "nom": "Bouznika",
        "url": "https://www.mubawab.ma/fr/st/bouznika/terrains-a-vendre",
    },
}
MUBAWAB_MAX_PAGES = 3
MUBAWAB_HEADLESS = True