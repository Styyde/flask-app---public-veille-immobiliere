# scraper/runner.py
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio

import nodriver as uc

from config import (
    BASE_URL,
    HEADLESS,
    LIMITE_PAGES,
    MAX_PAGES_PAR_LOT,
    REGIONS,
    TYPES_BIENS,
)
from core.core import scrape_combination
from database.db_manager import get_existing_urls, init_db, save_projets


# nodriver cherche Chrome dans les emplacements système standards
# (/usr/bin/chromium...), mais l'image Docker utilise le Chromium installé
# par Playwright (RUN playwright install --with-deps chromium dans le
# Dockerfile), qui vit dans /ms-playwright/chromium-<build>/chrome-linux64/
# -- sans ce chemin explicite, nodriver lève FileNotFoundError. Résolution
# par glob (pas de chemin en dur) pour survivre aux montées de version du
# build Playwright entre deux images.
def _chrome_executable_path():
    matches = glob.glob("/ms-playwright/chromium-*/chrome-linux64/chrome")
    return matches[0] if matches else None


async def run_full_scraping(headless=HEADLESS, limit_pages=LIMITE_PAGES, base_url=BASE_URL, deep_scrape=False):
    """
    Lance le scraping complet pour toutes les régions et types de biens.
    
    Args:
        headless (bool): Mode silencieux (True = pas de fenêtre visible)
        limit_pages (int): Nombre max de pages de résultats à scraper par combinaison
        base_url (str): URL de base du site
        deep_scrape (bool): Si True, extrait l'étage et la désignation pour chaque produit
    """
    print("🚀 Lancement du scraping multi-régions / multi-types...")
    if deep_scrape:
        print("🔬 Mode DEEP_SCRAPE activé : extraction des étages et désignations (plus lent)")
    
    # 1. Initialiser la base et récupérer les URLs existantes
    init_db()
    existing_urls = get_existing_urls()
    print(f"📚 {len(existing_urls)} projets déjà en base (ils seront ignorés).")
    
    browser = await uc.start(headless=headless, browser_executable_path=_chrome_executable_path())
    all_projects = []
    
    try:
        for region in REGIONS:
            region_id = region["id"]
            region_name = region["nom"]
            
            for type_code, type_label in TYPES_BIENS.items():
                projets = await scrape_combination(
                    browser=browser,
                    region_id=region_id,
                    region_name=region_name,
                    type_code=type_code,
                    type_label=type_label,
                    existing_urls=existing_urls,
                    limit_pages=limit_pages,
                    base_url=base_url,
                    max_pages_lot=MAX_PAGES_PAR_LOT,
                    deep_scrape=deep_scrape
                )
                all_projects.extend(projets)
                print(f"📊 Sous-total après {region_name} - {type_label} : {len(all_projects)} nouveaux projets.")
        
        # 2. Sauvegarde UNIQUE à la fin
        if all_projects:
            save_projets(all_projects)
            print(f"💾 {len(all_projects)} nouveaux projets sauvegardés en base.")
        else:
            print("⚠️ Aucun nouveau projet à sauvegarder.")
                
        print(f"\n✅ SCRAPING TERMINÉ : {len(all_projects)} nouveaux projets uniques extraits.")
        
    except Exception as e:
        print(f"❌ Erreur générale : {e}")
    finally:
        try:
            await browser.stop()
            await asyncio.sleep(0.5)
        except:
            pass
    
    return all_projects

# ============================================================
# NOUVELLE FONCTION : scraper une liste de régions spécifiques
# ============================================================
async def scrape_regions(region_ids, headless=True, limit_pages=None, deep_scrape=False):
    """
    Lance le scraping pour les régions dont les IDs sont donnés.
    region_ids : liste d'IDs (ex: [78, 414])
    Retourne la liste des nouveaux projets extraits.
    """
    print(f"🚀 Lancement du scraping pour les régions {region_ids}...")
    if deep_scrape:
        print("🔬 Mode DEEP_SCRAPE activé : extraction des étages et désignations")
    
    # Filtrer les régions
    regions = [r for r in REGIONS if r['id'] in region_ids]
    if not regions:
        print("⚠️ Aucune région trouvée pour les IDs donnés.")
        return []
    
    init_db()
    existing_urls = get_existing_urls()
    print(f"📚 {len(existing_urls)} projets déjà en base.")
    
    browser = await uc.start(headless=headless, browser_executable_path=_chrome_executable_path())
    all_projects = []
    
    try:
        for region in regions:
            region_id = region["id"]
            region_name = region["nom"]
            for type_code, type_label in TYPES_BIENS.items():
                projets = await scrape_combination(
                    browser=browser,
                    region_id=region_id,
                    region_name=region_name,
                    type_code=type_code,
                    type_label=type_label,
                    existing_urls=existing_urls,
                    limit_pages=limit_pages,
                    base_url=BASE_URL,
                    max_pages_lot=MAX_PAGES_PAR_LOT,
                    deep_scrape=deep_scrape
                )
                all_projects.extend(projets)
                print(f"📊 Sous-total {region_name} - {type_label} : {len(all_projects)} nouveaux projets.")
        
        if all_projects:
            save_projets(all_projects)
            print(f"💾 {len(all_projects)} nouveaux projets sauvegardés.")
        else:
            print("⚠️ Aucun nouveau projet trouvé.")
                
        print(f"✅ Scraping terminé pour les régions {region_ids}. {len(all_projects)} nouveaux projets.")
    except Exception as e:
        print(f"❌ Erreur générale : {e}")
    finally:
        try:
            await browser.stop()
        except:
            pass
    
    return all_projects

if __name__ == "__main__":
    async def test():
        # Pour un test rapide : deep_scrape=False
        # Pour une analyse complète : deep_scrape=True
        results = await run_full_scraping(headless=False, limit_pages=2, deep_scrape=True)
        print(f"\n🔍 {len(results)} nouveaux projets trouvés.")
    asyncio.run(test())