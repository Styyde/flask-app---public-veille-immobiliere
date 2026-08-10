# scraper/core.py
# Contient toute la logique de navigation, extraction et parsing.

import asyncio
import sys
import warnings
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from config import BASE_URL

import nodriver as uc
from bs4 import BeautifulSoup

# --- Correctif Windows ---
if sys.platform == 'win32':
    warnings.filterwarnings("ignore", category=ResourceWarning)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        import asyncio.proactor_events
        org_repr = asyncio.proactor_events._ProactorBasePipeTransport.__repr__
        def safe_repr(self):
            try:
                return org_repr(self)
            except ValueError:
                return f"<{self.__class__.__name__} [pipe fermé]>"
        asyncio.proactor_events._ProactorBasePipeTransport.__repr__ = safe_repr
        
        org_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__
        def safe_del(self):
            try:
                org_del(self)
            except RuntimeError:
                pass
        asyncio.proactor_events._ProactorBasePipeTransport.__del__ = safe_del
    except Exception:
        pass

# --- Mapping des codes de type de bien ---
TYPE_MAPPING = {
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

# --- FONCTIONS UTILITAIRES ---

async def click_element(page, selector, timeout=10):
    try:
        elem = await page.find(selector, timeout=timeout)
        if elem:
            await elem.click()
            return True
    except Exception:
        pass
    return False

async def get_page_soup(page):
    html = await page.get_content()
    return BeautifulSoup(html, 'html.parser')

async def scroll_to_bottom(page, steps=5, delay=0.5):
    for _ in range(steps):
        await page.scroll_down(500)
        await asyncio.sleep(delay)

# ============================================================
# FONCTION : Extraction des détails d'un produit (étage, désignation)
# ============================================================
async def extraire_detail_produit(page, detail_url, base_domain):
    """
    Navigue vers la page de détail d'un produit et extrait l'étage et la désignation.
    Retourne un dictionnaire avec 'etage' et 'designation' ou None en cas d'échec.
    """
    try:
        # Construire l'URL absolue
        if detail_url.startswith('/'):
            detail_url = base_domain + detail_url
        elif not detail_url.startswith('http'):
            detail_url = base_domain + '/' + detail_url
        
        await page.get(detail_url)
        await page.wait_for("div.project-detail__info-box", timeout=8)
        soup = await get_page_soup(page)
        
        etage = None
        designation = None
        
        # Parcourir tous les <p> dans .project-detail__info-box
        for p in soup.select("div.project-detail__info-box p"):
            texte = p.get_text(strip=True)
            if "Etage :" in texte:
                etage = texte.replace("Etage :", "").strip()
            elif "Désignation du bien:" in texte:
                designation = texte.replace("Désignation du bien:", "").strip()
        
        return {"etage": etage, "designation": designation}
    except Exception as e:
        print(f"   ⚠️ Erreur extraction détail produit : {e}")
        return None

# ============================================================
# FONCTION extraire_lots AVEC GESTION DE LA PAGINATION ET DEEP_SCRAPE
# ============================================================
async def extraire_lots(page, max_pages=None, base_domain=None, deep_scrape=False):
    """
    Extrait les lots : infos de base, puis clique sur chaque bouton pour déplier le tableau
    et extrait TOUS les produits, en parcourant toutes les pages de pagination si elles existent.
    
    Args:
        page: Page nodriver
        max_pages: Nombre max de pages à extraire par lot (None = toutes)
        base_domain: Domaine de base pour construire les URLs absolues
        deep_scrape: Si True, va chercher l'étage et la désignation pour chaque produit
    """
    await scroll_to_bottom(page, steps=8, delay=0.8)
    soup = await get_page_soup(page)
    lots = []
    panels_info = soup.select("div.lots-dropdown__panel-info")
    
    for idx, panel_info in enumerate(panels_info, start=1):
        # --- Infos de base du lot ---
        titre_tag = panel_info.select_one("h3.lots-dropdown__panel-title")
        titre = titre_tag.get_text(strip=True) if titre_tag else ""
        
        spans = panel_info.select("span.lots-dropdown__panel-price")
        nb_unites = ""
        prix_min = ""
        prix_max = ""
        for span in spans:
            texte = span.get_text(strip=True)
            if "unité(s) disponible(s)" in texte:
                nb_unites = texte
            elif "De" in texte and "DH" in texte:
                parts = texte.split("à")
                if len(parts) == 2:
                    prix_min = parts[0].replace("De", "").strip()
                    prix_max = parts[1].strip()
                else:
                    prix_min = texte
        
        # Récupérer le data-target pour identifier le tableau
        panel_header = panel_info.find_parent('div', class_='lots-dropdown__panel-header')
        target = panel_header.get('data-target') if panel_header else None
        
        # --- Cliquer sur le toggle pour afficher le tableau ---
        try:
            toggle_selector = f"div.lots-dropdown__panel-header:nth-of-type({idx}) .lots-dropdown__panel-toggle"
            toggle_btn = await page.find(toggle_selector, timeout=2)
            if toggle_btn:
                await toggle_btn.click()
                await asyncio.sleep(1.5)
        except Exception:
            pass
        
        # --- Extraction des produits avec gestion de pagination ---
        lignes = []
        if target:
            await asyncio.sleep(1)
            
            # Récupérer le nombre total de pages
            html = await page.get_content()
            soup_updated = BeautifulSoup(html, 'html.parser')
            
            # Chercher la pagination dans le parent du tableau
            table_tag = soup_updated.select_one(f"#{target}-table")
            pagination_ul = None
            if table_tag:
                parent = table_tag.find_parent()
                if parent:
                    pagination_ul = parent.find("ul", class_="pagination")
            total_pages = 1
            if pagination_ul:
                page_items = pagination_ul.select("li a[data-page]")
                if page_items:
                    pages = [int(a.get('data-page')) for a in page_items if a.get('data-page').isdigit()]
                    if pages:
                        total_pages = max(pages)
            
            # Appliquer la limite éventuelle
            if max_pages is not None and max_pages < total_pages:
                total_pages = max_pages
            
            # Boucle sur les pages
            for page_num in range(1, total_pages + 1):
                if page_num > 1:
                    try:
                        click_selector = f"ul.lots-dropdown__pagination-list a[data-page='{page_num}']"
                        btn = await page.find(click_selector, timeout=5)
                        if btn:
                            await btn.click()
                            await asyncio.sleep(1.5)
                        else:
                            print(f"   ⚠️ Lien page {page_num} non trouvé, arrêt de la pagination.")
                            break
                    except Exception as e:
                        print(f"   ⚠️ Erreur clic page {page_num} : {e}")
                        break
                
                # Extraire les lignes du tableau pour cette page
                html = await page.get_content()
                soup_page = BeautifulSoup(html, 'html.parser')
                rows = soup_page.select(f"#{target}-table tbody tr")
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        no_produit = cols[0].get_text(strip=True)
                        surface = cols[1].get_text(strip=True)
                        prix = cols[2].get_text(strip=True)
                        
                        etage = None
                        designation = None
                        product_url = None
                        
                        # Si deep_scrape est activé, on va chercher les détails
                        if deep_scrape and len(cols) > 3:
                            detail_link = cols[3].find('a') if cols[3] else None
                            if detail_link and detail_link.get('href'):
                                detail_url = detail_link.get('href')
                                # Construire l'URL absolue
                                if detail_url.startswith('/'):
                                    product_url = base_domain + detail_url
                                else:
                                    product_url = detail_url
                                
                                infos = await extraire_detail_produit(page, detail_url, base_domain)
                                if infos:
                                    etage = infos.get('etage')
                                    designation = infos.get('designation')
                                # Revenir à la page du lot
                                await page.back()
                                await asyncio.sleep(1.5)
                        
                        lignes.append({
                            "no_produit": no_produit,
                            "surface": surface,
                            "prix": prix,
                            "etage": etage,
                            "designation": designation,
                            "url": product_url
                        })
        
        lots.append({
            "titre": titre,
            "nb_unites": nb_unites,
            "prix_min": prix_min,
            "prix_max": prix_max,
            "lignes": lignes
        })
    
    return lots

# ============================================================
# FONCTION extraire_detail_projet
# ============================================================
async def extraire_detail_projet(page, badge_text, max_pages=None, base_domain=None, deep_scrape=False):
    """Extrait les détails d'un projet (titre, localisation, description, lots)."""
    soup = await get_page_soup(page)
    
    loc_tag = soup.select_one("div.card__meta.chip.chip--city.card-city-product span")
    localisation = loc_tag.get_text(strip=True) if loc_tag else ""
    
    title_tag = soup.select_one("h1.hero-bien__title")
    titre = title_tag.get_text(strip=True) if title_tag else ""
    
    tf_tag = soup.select_one("span.lame-detail-project__left_highlight")
    titre_foncier = tf_tag.get_text(strip=True) if tf_tag else ""
    
    desc_tag = soup.select_one("div.lame-detail-project__left_content div.eztext-field")
    description = desc_tag.get_text(strip=True) if desc_tag else ""
    
    lots = await extraire_lots(page, max_pages=max_pages, base_domain=base_domain, deep_scrape=deep_scrape)
    
    return {
        "badge": badge_text,
        "localisation": localisation,
        "titre": titre,
        "titre_foncier": titre_foncier,
        "description": description,
        "lots": lots
    }

# ============================================================
# FONCTIONS UTILITAIRES SUPPLÉMENTAIRES
# ============================================================

def ajouter_parametre_url(url, param, valeur):
    """Ajoute un paramètre de pagination à l'URL."""
    parsed = urlparse(url)
    query_dict = parse_qs(parsed.query)
    query_dict[param] = [str(valeur)]
    new_query = urlencode(query_dict, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def extraire_types_depuis_url(url):
    """Extrait les codes types de l'URL pour affichage."""
    parsed = urlparse(url)
    query_dict = parse_qs(parsed.query)
    type_codes = query_dict.get("type[]", [])
    types = []
    for code in type_codes:
        libelle = TYPE_MAPPING.get(code, code)
        types.append(libelle)
    return types

async def retour_liste(page, current_url, max_retries=3):
    """
    Fonction robuste pour revenir à la page de liste.
    Tente de charger l'URL et attend la présence des articles.
    En cas d'échec, réessaie avec un rechargement forcé.
    """
    for attempt in range(max_retries):
        try:
            await page.get(current_url)
            await page.wait_for("article.card.item-result-filter", timeout=10)
            await asyncio.sleep(2)
            html = await page.get_content()
            if "article.card.item-result-filter" in html or "card" in html:
                print("   ✅ Retour à la liste réussi.")
                return True
            else:
                print(f"   ⚠️ Tentative {attempt+1} : pas d'articles détectés.")
                await page.reload()
                await asyncio.sleep(2)
        except Exception as e:
            print(f"   ⚠️ Tentative {attempt+1} échouée : {e}")
            await asyncio.sleep(2)
    print("   ❌ Échec du retour à la liste après plusieurs tentatives.")
    return False

# ============================================================
# FONCTION PRINCIPALE DE SCRAPING D'UNE COMBINAISON
# ============================================================

async def scrape_combination(browser, region_id, region_name, type_code, type_label, 
                             existing_urls=None, limit_pages=None, base_url=BASE_URL,
                             max_pages_lot=None, deep_scrape=False):
    """
    Scrape toutes les annonces avec badge "Promo" pour une région et un type donnés.
    
    Args:
        max_pages_lot: Nombre max de pages de produits à extraire par lot (None = toutes)
        deep_scrape: Si True, extrait l'étage et la désignation pour chaque produit
    """
    if existing_urls is None:
        existing_urls = set()
    
    search_url = f"{base_url}?affiliate[]={region_id}&type[]={type_code}"
    all_projects = []
    page_num = 1
    
    # Récupérer le domaine de base pour les URLs absolues
    parsed_base = urlparse(base_url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    print(f"\n🌍 DEBUT SCRAPING : {region_name} - {type_label}")
    
    # --- Étape 1 : Navigation vers la page et activation de l'onglet "Liste" ---
    page = await browser.get(search_url)
    await asyncio.sleep(3)
    
    if await click_element(page, "#tabList", timeout=5):
        print("✅ Onglet 'Liste' activé.")
        await asyncio.sleep(2)
    else:
        print("⚠️ Impossible de cliquer sur 'Liste', on continue quand même.")
    
    # --- Étape 2 : Boucle sur les pages de résultats ---
    while True:
        if page_num == 1:
            current_url = search_url
        else:
            current_url = ajouter_parametre_url(search_url, "pagelist", page_num)
        
        print(f"📄 [{region_name} - {type_label}] Page {page_num} : {current_url}")
        
        await page.get(current_url)
        
        try:
            await page.wait_for("article.card.item-result-filter", timeout=10)
        except Exception:
            print("⚠️ Aucun article détecté sur cette page (fin naturelle ou page vide).")
            break
        
        await asyncio.sleep(2)
        
        html = await page.get_content()
        if "n'existe pas ou n'est plus disponible" in html:
            print("🛑 Message 404 détecté. Fin du bouclage.")
            break
        
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.select("article.card.item-result-filter")
        if not articles:
            articles = soup.select("div.card, article, div[class*='card']")
        
        print(f"🔍 {len(articles)} articles détectés sur cette page.")
        
        if not articles:
            print("⚠️ Aucun article trouvé. Fin de la pagination.")
            break
        
        # --- Étape 3 : Traitement de chaque article ---
        for idx, article in enumerate(articles, 1):
            # Récupérer le badge
            badge_tag = article.select_one("span.card__badge--promo")
            if not badge_tag:
                continue
            badge_text = badge_tag.get_text(strip=True)
            
            # ✅ FILTRE : On ne garde que les badges "Promotion" ou "Nouveau"
            if badge_text not in ["Promotion", "Nouveau"]:
                continue
            
            print(f"\n🔹 [{region_name}] Produit {idx} : badge '{badge_text}' trouvé.")
            
            # Récupération du lien "Plus d'infos"
            link_tag = article.select_one("a.card__cta")
            if not link_tag:
                link_tag = article.select_one("a")
            if not link_tag:
                print("   ⛔ Lien 'Plus d'infos' introuvable, on passe.")
                continue
            
            href = link_tag.get("href")
            if not href or href == "#":
                continue
            
            if href.startswith("/"):
                full_link = f"{base_domain}{href}"
            elif href.startswith("http"):
                full_link = href
            else:
                full_link = f"{base_domain}/{href}"
            
            if full_link in existing_urls:
                print(f"   ⏭️  Produit déjà traité (doublon), on passe.")
                continue
            existing_urls.add(full_link)
            
            print(f"   🔗 Lien vers le détail : {full_link}")
            
            try:
                await page.get(full_link)
                await page.wait_for("h1.hero-bien__title", timeout=10)
                await asyncio.sleep(3)
                
                # Passage des paramètres max_pages_lot, base_domain et deep_scrape
                detail = await extraire_detail_projet(
                    page, 
                    badge_text, 
                    max_pages=max_pages_lot,
                    base_domain=base_domain,
                    deep_scrape=deep_scrape
                )
                detail["lien"] = full_link
                detail["type_bien"] = type_label
                detail["region"] = region_name
                all_projects.append(detail)
                
                print(f"   ✅ Projet '{detail['titre']}' extrait avec {len(detail['lots'])} lots.")
                
            except Exception as e:
                print(f"   ❌ Erreur lors de la navigation ou extraction : {e}")
            
            try:
                success = await retour_liste(page, current_url)
                if not success:
                    print("   ⚠️ Problème retour à la liste, tentative de rechargement manuel...")
                    await page.get(current_url)
                    await asyncio.sleep(5)
            except Exception as e:
                print(f"   ❌ Erreur critique lors du retour à la liste : {e}")
        
        if limit_pages is not None and page_num >= limit_pages:
            print(f"🛑 Limite de {limit_pages} page(s) atteinte.")
            break
        
        page_num += 1
    
    print(f"🏁 FIN SCRAPING : {region_name} - {type_label} ({len(all_projects)} projets extraits)")
    return all_projects