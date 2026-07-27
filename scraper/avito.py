import asyncio
import os
import random
import re
import sys
from urllib.parse import urljoin

# ============================================================
# CONFIGURATION
# ============================================================
BASE_URL = "https://www.avito.ma/fr/maroc/terrains_et_fermes-%C3%A0_vendre?"
PAGES = 3
DELAY_BETWEEN_PAGES = (5, 10)  # secondes

# --- Proxy résidentiel (INDISPENSABLE pour Avito) ---
# Obtenez un proxy résidentiel (ex: BrightData, Oxylabs, Smartproxy)
# Format : "http://user:pass@host:port"
PROXY = None  # Mettez votre proxy ici, sinon le risque de blocage est élevé

# --- Clé API Capsolver ---
CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "VOTRE_CLE_API_CAPSOLVER")

# ============================================================
# FONCTIONS D'EXTRACTION (inchangées)
# ============================================================
async def extract_ad_data(ad_element, page):
    data = {
        "titre": None,
        "type": None,
        "prix": None,
        "ville": None,
        "url": None,
        "surface": None,
    }
    href = await ad_element.get_attribute("href")
    if href:
        data["url"] = urljoin("https://www.avito.ma", href)
    h3 = await ad_element.query_selector("h3")
    if h3:
        data["titre"] = (await h3.text_content()).strip()
    type_div = await ad_element.query_selector('div[class*="sc-j5d10c-11"]')
    if type_div:
        type_span = await type_div.query_selector("span")
        if type_span:
            data["type"] = (await type_span.text_content()).strip()
    price_div = await ad_element.query_selector('div[class*="sc-j5d10c-13"]')
    if price_div:
        price_span = await price_div.query_selector('span[class*="sc-b6852cba-2"]')
        if price_span:
            price_text = await price_span.text_content()
            price_clean = re.sub(r"[^\d]", "", price_text)
            if price_clean:
                data["prix"] = price_clean + " DH"
    location_div = await ad_element.query_selector('div[class*="sc-j5d10c-22"]')
    if location_div:
        location_spans = await location_div.query_selector_all('span[class*="sc-j5d10c-23"]')
        if location_spans:
            data["ville"] = (await location_spans[0].text_content()).strip()
    surface = None
    if data["titre"]:
        match = re.search(r"(\d+)\s*m²", data["titre"], re.IGNORECASE)
        if match:
            surface = match.group(1) + " m²"
    if not surface:
        text = await ad_element.text_content()
        match = re.search(r"(\d+)\s*m²", text, re.IGNORECASE)
        if match:
            surface = match.group(1) + " m²"
    data["surface"] = surface
    return data

# ============================================================
# FONCTION DE RÉSOLUTION CAPTCHA AVEC CAPSOLVER
# ============================================================
async def solve_captcha_with_capsolver(page, api_key):
    """
    Détecte la présence d'un CAPTCHA (reCAPTCHA, hCaptcha, Turnstile)
    et le résout via Capsolver en injectant le token.
    Retourne True si résolu, False sinon.
    """
    # 1. Vérifier la présence d'un CAPTCHA
    # Sélecteurs courants pour différents types
    recaptcha_iframe = await page.query_selector('iframe[src*="recaptcha"]')
    hcaptcha_iframe = await page.query_selector('iframe[src*="hcaptcha"]')
    turnstile_div = await page.query_selector('div[class*="turnstile"]')

    if not (recaptcha_iframe or hcaptcha_iframe or turnstile_div):
        return False

    print("🧩 CAPTCHA détecté, résolution en cours...")

    # 2. Déterminer le type et récupérer le sitekey
    # Pour simplifier, on suppose que c'est un reCAPTCHA v2 ou hCaptcha
    # On peut extraire le sitekey depuis un attribut data-sitekey ou depuis l'URL
    sitekey = None
    if recaptcha_iframe:
        # Pour reCAPTCHA, le sitekey est souvent dans un div parent avec data-sitekey
        parent = await recaptcha_iframe.evaluate_handle("el => el.closest('div[data-sitekey]')")
        if parent:
            sitekey = await parent.get_attribute("data-sitekey")
        if not sitekey:
            # Fallback : extraire depuis l'URL de l'iframe
            src = await recaptcha_iframe.get_attribute("src")
            match = re.search(r"k=([^&]+)", src)
            if match:
                sitekey = match.group(1)
        captcha_type = "ReCaptchaV2TaskProxyless"
    elif hcaptcha_iframe:
        # Pour hCaptcha, similaire
        parent = await hcaptcha_iframe.evaluate_handle("el => el.closest('div[data-sitekey]')")
        if parent:
            sitekey = await parent.get_attribute("data-sitekey")
        captcha_type = "HCaptchaTaskProxyless"
    elif turnstile_div:
        # Turnstile (Cloudflare)
        sitekey = await turnstile_div.get_attribute("data-sitekey")
        captcha_type = "AntiTurnstileTaskProxyless"
    else:
        return False

    if not sitekey:
        print("⚠️ Impossible de récupérer le sitekey du CAPTCHA.")
        return False

    print(f"🔑 Sitekey : {sitekey}, Type : {captcha_type}")

    # 3. Appeler l'API Capsolver
    import capsolver
    capsolver.api_key = api_key

    try:
        solution = capsolver.solve({
            "type": captcha_type,
            "websiteURL": page.url,
            "websiteKey": sitekey,
        })
        token = solution.get("gRecaptchaResponse") or solution.get("solution", {}).get("gRecaptchaResponse")
        if not token:
            token = solution.get("token")  # pour Turnstile
        if token:
            # 4. Injecter le token dans la page
            # Pour reCAPTCHA, on appelle la callback
            await page.evaluate(f"""
                document.getElementById('g-recaptcha-response').innerHTML = '{token}';
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    ___grecaptcha_cfg.clients[0].callback('{token}');
                }}
            """)
            # Pour hCaptcha, on fait de même
            await page.evaluate(f"""
                if (typeof hcaptcha !== 'undefined') {{
                    hcaptcha.setResponse('{token}');
                }}
            """)
            print("✅ CAPTCHA résolu avec succès.")
            # Attendre que la page se recharge ou que le token soit validé
            await asyncio.sleep(3)
            return True
        else:
            print("❌ Aucun token reçu de Capsolver.")
            return False
    except Exception as e:
        print(f"⚠️ Erreur Capsolver : {e}")
        return False

# ============================================================
# SCRAPING D'UNE PAGE
# ============================================================
async def scrape_page(page, page_number, api_key):
    if page_number == 1:
        url = BASE_URL.rstrip("?")
    else:
        url = f"{BASE_URL}o={page_number}"
    print(f"🌐 Page {page_number} : {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

    # Résoudre le CAPTCHA si présent
    if api_key and api_key != "VOTRE_CLE_API_CAPSOLVER":
        solved = await solve_captcha_with_capsolver(page, api_key)
        if solved:
            print("🔄 Attente du rechargement après CAPTCHA...")
            await page.wait_for_load_state("networkidle", timeout=30000)

    # Attendre les annonces
    try:
        await page.wait_for_selector('a[data-testid^="ad-card-v2-"]', timeout=15000)
    except Exception:
        print("⏳ Aucune annonce trouvée. Vérifiez le proxy ou la résolution du CAPTCHA.")
        return []

    # CloakBrowser gère déjà le scroll et les mouvements via humanize=True
    # On laisse un petit délai supplémentaire
    await asyncio.sleep(random.uniform(1, 3))

    ad_links = await page.query_selector_all('a[data-testid^="ad-card-v2-"]')
    print(f"🔍 {len(ad_links)} annonces détectées.")
    ads = []
    for link in ad_links:
        ad_data = await extract_ad_data(link, page)
        if ad_data["titre"]:
            ads.append(ad_data)
    return ads

# ============================================================
# MAIN
# ============================================================
async def main():
    from cloakbrowser import launch

    # Vérifier la clé Capsolver
    use_solver = CAPSOLVER_API_KEY and CAPSOLVER_API_KEY != "VOTRE_CLE_API_CAPSOLVER"
    if not use_solver:
        print("⚠️ Aucune clé Capsolver valide. Les CAPTCHA ne seront pas résolus.")
        print("   Obtenez une clé sur https://www.capsolver.com/ et définissez CAPSOLVER_API_KEY.")

    if not PROXY:
        print("⚠️ Aucun proxy configuré. Avito bloquera très probablement votre IP.")
        print("   Utilisez un proxy résidentiel pour éviter le blocage.")

    browser = await launch(
        headless=False,          # Mettre True si vous voulez exécuter en arrière-plan (moins réaliste)
        humanize=True,           # Simule les mouvements de souris et le scroll
        proxy=PROXY,             # Indispensable
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-infobars",
        ]
    )

    context = await browser.new_context(
        viewport={"width": random.randint(1200, 1920), "height": random.randint(800, 1080)},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        user_agent=random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        ])
    )
    page = await context.new_page()

    all_ads = []
    for page_num in range(1, PAGES + 1):
        ads = await scrape_page(page, page_num, CAPSOLVER_API_KEY if use_solver else None)
        all_ads.extend(ads)
        print(f"✅ Page {page_num} : {len(ads)} annonces extraites.")
        if page_num < PAGES:
            delay = random.uniform(*DELAY_BETWEEN_PAGES)
            print(f"⏳ Attente de {delay:.1f} secondes avant la page suivante...")
            await asyncio.sleep(delay)

    print(f"\n📊 Total : {len(all_ads)} annonces récupérées.")
    for i, ad in enumerate(all_ads, 1):
        print(f"\n--- Annonce {i} ---")
        for key, value in ad.items():
            print(f"{key}: {value}")

    await browser.close()

if __name__ == "__main__":
    asyncio.run(main())