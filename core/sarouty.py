# scraper/sarouty.py
import re
import time

import requests

from database.db_manager import init_db, save_annonces_sarouty

API_BASE_URL = "https://b2c-be-prod.api.sarouty.ma/api/properties"
MAX_PAGES = 5

def slugify(text):
    if not text: return "bien"
    text = text.lower()
    accents = {'â': 'a', 'à': 'a', 'ä': 'a', 'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'î': 'i', 'ï': 'i', 'ô': 'o', 'ö': 'o', 'û': 'u', 'ù': 'u', 'ü': 'u', 'ç': 'c'}
    for char, repl in accents.items(): text = text.replace(char, repl)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def nettoyer_ville(slug):
    """Transforme un slug de ville en nom lisible (ex: 'rabat-sale' -> 'Rabat Sale')."""
    if not slug:
        return None
    # Remplacer les tirets par des espaces et mettre en titre (première lettre de chaque mot en majuscule)
    return slug.replace('-', ' ').title()

def construire_url_annonce(prop, list_item=None):
    """Construit une URL Sarouty fiable."""
    list_item = list_item or {}
    pid = prop.get("property_id") or list_item.get("property_id")
    if not pid:
        return None

    category_key = (
        prop.get("property_category_key")
        or list_item.get("property_category_key")
        or "buy"
    )
    categorie = "louer" if category_key == "rent" else "acheter"

    type_bien = slugify(
        prop.get("property_housing_type")
        or list_item.get("property_housing_type")
        or "bien"
    )
    loc = prop.get("location") or {}
    ville_raw = (
        loc.get("url_city_slug")
        or list_item.get("location_url_slug")
        or "maroc"
    )
    ville = slugify(ville_raw) or "maroc"
    quartier_raw = loc.get("name_primary") or list_item.get("location_name") or ""
    quartier = slugify(quartier_raw) if quartier_raw else ""
    if quartier == "bien":
        quartier = ""

    if quartier and quartier != ville:
        return f"https://www.sarouty.ma/{categorie}/{type_bien}-{ville}-{quartier}-{pid}/"
    return f"https://www.sarouty.ma/{categorie}/{type_bien}-{ville}-{pid}/"

def scraper_sarouty(max_pages=MAX_PAGES, region_ids=None, category='1'):
    """
    category: '1' pour résidentiel, '2' pour commercial
    """
    if region_ids is None: region_ids = [35, 113]
    location_value = ",".join(str(id) for id in region_ids)

    filters = [
        '{"field":"buy_or_rent","operator":"eq","value":1}',
        f'{{"field":"type","operator":"eq","value":"{category}"}}',
        f'{{"field":"location_name","operator":"in","value":"{location_value}"}}',
        '{"field":"housing_type","operator":"in","value":"35,1,22,10,5,48,56"}',
        '{"field":"level","operator":"eq","value":1}',
        '{"field":"published","operator":"eq","value":1}',
        '{"field":"property_published","operator":"eq","value":1}'
    ]

    init_db()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

    toutes = []
    categorie_label = "résidentiel" if category == '1' else "commercial"
    print(f"🚀 Scraping Sarouty pour région(s) {region_ids} - Catégorie : {categorie_label}")

    for page in range(1, max_pages + 1):
        params = {"limit": 25, "page": page, "filters": filters}
        resp = session.get(API_BASE_URL, params=params)
        if resp.status_code != 200:
            break
        annonces = resp.json().get('data', {}).get('data', [])
        if not annonces:
            break

        for item in annonces:
            pid = item.get("property_id")
            if not pid:
                continue

            try:
                detail = session.get(f"{API_BASE_URL}/{pid}", timeout=15).json()
            except requests.RequestException as e:
                print(f"⚠️ Annonce {pid} ignorée (erreur réseau) : {e}")
                continue
            prop = detail.get("data", {}).get("data", detail.get("data", {}))

            loc = prop.get("location", {})
            quartier_brut = loc.get("name_primary") or item.get("location_name")
            ville_brute = loc.get("url_city_slug") or item.get("location_url_slug")

            # Nettoyer la ville
            ville = nettoyer_ville(ville_brute)

            url_annonce = construire_url_annonce(prop, list_item=item)

            toutes.append({
                "property_id": pid,
                "url_annonce": url_annonce,
                "titre": prop.get("property_title_fr") or item.get("property_title_fr") or "Sans titre",
                "description": prop.get("property_text_fr") or "",
                "prix": (prop.get("price") or {}).get("price") or (item.get("price") or {}).get("price") or 0,
                "superficie": prop.get("property_sqft") or item.get("property_sqft") or 0,
                "type_bien": prop.get("property_housing_type") or item.get("property_housing_type"),
                "quartier": quartier_brut,  # nom brut du quartier (peut contenir la ville entre parenthèses)
                "ville": ville              # ville nettoyée (ex: "Rabat Sale")
            })
            time.sleep(0.3)
        time.sleep(1)

    if toutes:
        save_annonces_sarouty(toutes)
    return len(toutes)

if __name__ == "__main__":
    scraper_sarouty()