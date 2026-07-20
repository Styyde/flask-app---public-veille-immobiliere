# scraper/sarouty.py
import requests, re, time
from database.db_manager import save_annonces_sarouty, init_db

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

def extraire_ville(quartier):
    if not quartier: return None
    match = re.search(r'\(([^)]+)\)', quartier)
    return match.group(1) if match else quartier

def scraper_sarouty(max_pages=MAX_PAGES, region_ids=None, category='1'):
    """
    category: '1' pour résidentiel, '2' pour commercial
    """
    if region_ids is None: region_ids = [35, 113]
    location_value = ",".join(str(id) for id in region_ids)

    # Construction des filtres avec la catégorie choisie
    filters = [
        '{"field":"buy_or_rent","operator":"eq","value":1}',
        f'{{"field":"type","operator":"eq","value":"{category}"}}',  # ← dynamique
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
        if resp.status_code != 200: break
        annonces = resp.json().get('data', {}).get('data', [])
        if not annonces: break
        for item in annonces:
            pid = item.get("property_id")
            if not pid: continue
            detail = session.get(f"{API_BASE_URL}/{pid}").json()
            prop = detail.get("data", {}).get("data", detail.get("data", {}))
            
            loc = prop.get("location", {})
            quartier_brut = loc.get("name_primary")
            ville_brute = loc.get("url_city_slug")
            path = prop.get("path") or prop.get("slug")
            url_annonce = f"https://www.sarouty.ma{path}" if path and path.startswith('/') else f"https://www.sarouty.ma/{path}"
            
            toutes.append({
                "property_id": pid, "url_annonce": url_annonce,
                "titre": prop.get("property_title_fr") or "Sans titre",
                "description": prop.get("property_text_fr") or "",
                "prix": prop.get("price", {}).get("price") or 0,
                "superficie": prop.get("property_sqft") or 0,
                "chambres": prop.get("total_bedroom"),
                "salles_de_bain": prop.get("total_bathroom"),
                "type_bien": prop.get("property_housing_type"),
                "quartier": quartier_brut,
                "ville": extraire_ville(quartier_brut) or ville_brute
            })
            time.sleep(0.3)
        time.sleep(1)
    
    if toutes:
        save_annonces_sarouty(toutes)
    return len(toutes)

if __name__ == "__main__":
    # Exemple : scraper les résidentiels (défaut)
    scraper_sarouty()