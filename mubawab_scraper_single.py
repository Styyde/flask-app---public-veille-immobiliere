import asyncio
import re
import random
from playwright.async_api import async_playwright

# Configuration
BASE_URL = "https://www.mubawab.ma/fr/ct/casablanca/immobilier-a-vendre-all:o:n:sc:commercial-sale,land-sale,other-sale,riad-sale,villa-sale"
HEADLESS = False  # Garder False pour éviter la détection
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def random_delay(min_sec=1, max_sec=3):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def extract_listing_links(page):
    ad_links = []
    boxes = await page.query_selector_all("div.listingBox")
    for box in boxes:
        linkref = await box.get_attribute("linkref")
        if linkref:
            ad_links.append(linkref)
        else:
            a_tag = await box.query_selector("h2.listingTit a")
            if a_tag:
                href = await a_tag.get_attribute("href")
                if href:
                    ad_links.append(href)
    return ad_links

async def extract_ad_detail(page, url):
    print(f"   🔍 Scraping détail : {url}")
    try:
        await page.goto(url, timeout=15000)
        await page.wait_for_selector("h1.searchTitle, h3.orangeTit", timeout=8000)
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.3);")
        await random_delay(0.5, 1.5)
        await page.evaluate("window.scrollBy(0, window.innerHeight * 0.2);")
        await random_delay(0.3, 0.8)
    except:
        pass

    data = {"url": url}

    # Titre
    try:
        title_elem = await page.query_selector("h1.searchTitle")
        data["title"] = await title_elem.inner_text() if title_elem else None
    except:
        data["title"] = None

    # Prix
    try:
        price_elem = await page.query_selector("h3.orangeTit")
        data["price"] = await price_elem.inner_text() if price_elem else None
    except:
        data["price"] = None

    # Localisation
    try:
        loc_elem = await page.query_selector("h3.greyTit")
        data["location"] = await loc_elem.inner_text() if loc_elem else None
    except:
        data["location"] = None

    # Surface
    surface = None
    try:
        details = await page.query_selector_all(".adDetailFeature")
        for detail in details:
            icon = await detail.query_selector("i")
            if not icon:
                continue
            icon_class = await icon.get_attribute("class") or ""
            if "icon-triangle" in icon_class:
                span = await detail.query_selector("span")
                if span:
                    text = await span.inner_text()
                    match = re.search(r'([\d\s]+)\s*m²', text)
                    if match:
                        surface = match.group(1).replace(' ', '')
                        break
    except:
        pass
    data["surface"] = surface

    # Type de bien
    type_bien = None
    try:
        carac_block = await page.query_selector(".caractBlockProp")
        if carac_block:
            features = await carac_block.query_selector_all(".adMainFeature")
            for feat in features:
                label_elem = await feat.query_selector(".adMainFeatureContentLabel")
                value_elem = await feat.query_selector(".adMainFeatureContentValue")
                if label_elem and value_elem:
                    label = await label_elem.inner_text()
                    if "Type de bien" in label:
                        type_bien = await value_elem.inner_text()
                        break
    except:
        pass
    data["type_bien"] = type_bien

    # Description
    description = None
    scripts = await page.query_selector_all('script')
    for script in scripts:
        try:
            content = await script.inner_text()
            match = re.search(r'"description"\s*:\s*"([^"]*?)"', content, re.DOTALL)
            if match:
                desc = match.group(1)
                desc = desc.replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/')
                if desc.strip():
                    description = desc
                    break
        except:
            continue

    if not description:
        try:
            meta_desc = await page.query_selector('meta[name="description"]')
            if meta_desc:
                desc = await meta_desc.get_attribute("content")
                if desc and desc.strip():
                    description = desc
        except:
            pass

    if not description:
        try:
            block_prop = await page.query_selector("div.blockProp")
            if block_prop:
                desc = await block_prop.inner_text()
                if desc.strip():
                    description = desc
        except:
            pass

    if not description:
        try:
            paragraphs = await page.query_selector_all("p")
            for p in paragraphs:
                text = await p.inner_text()
                if len(text.strip()) > 50:
                    description = text
                    break
        except:
            pass

    if description:
        description = re.sub(r'\s+', ' ', description).strip()

    data["description"] = description

    if description:
        print(f"      📝 Description extraite ({len(description)} caractères)")
    else:
        print(f"      ⚠️ Description non trouvée pour {url}")

    return data

async def get_total_pages(page, base_url):
    await page.goto(base_url, timeout=20000)
    await random_delay(1, 2)
    try:
        await page.wait_for_selector("div.listingBox", timeout=15000)
    except:
        return 1

    dots = await page.query_selector_all("a.Dots")
    if not dots:
        return 1

    max_page = 1
    for dot in dots:
        text = await dot.inner_text()
        try:
            num = int(text.strip())
            if num > max_page:
                max_page = num
        except:
            continue

    if max_page == 1:
        for dot in dots:
            href = await dot.get_attribute("href")
            if href:
                match = re.search(r':p:(\d+)', href)
                if match:
                    num = int(match.group(1))
                    if num > max_page:
                        max_page = num
    return max_page

async def scrape_all_pages(playwright, base_url):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
        ]
    )
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1366, 'height': 768},
        locale='fr-FR',
        timezone_id='Europe/Paris',
        extra_http_headers={
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )
    page = await context.new_page()
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['fr-FR', 'fr']
        });
    """)

    total_pages = await get_total_pages(page, base_url)
    print(f"📚 Nombre total de pages détecté : {total_pages}")

    # === MODIFICATION ICI : scraper les 3 premières pages ===
    pages_to_scrape = list(range(1, min(total_pages, 3) + 1))
    print(f"🎯 Pages cibles : {pages_to_scrape}")

    all_ads = []
    seen_urls = set()

    for page_num in pages_to_scrape:
        current_url = base_url + f":p:{page_num}"
        print(f"\n📄 Page {page_num} : {current_url}")

        await page.goto(current_url, timeout=20000)
        await random_delay(1.5, 3)
        try:
            await page.wait_for_selector("div.listingBox", timeout=10000)
        except:
            print(f"   ⚠️ Aucune annonce sur la page {page_num} – arrêt.")
            break

        links = await extract_listing_links(page)
        print(f"   {len(links)} annonces trouvées.")

        for link in links:
            if link in seen_urls:
                print(f"   ⏭️ Déjà scrapé : {link}")
                continue
            ad_data = await extract_ad_detail(page, link)
            if ad_data and ad_data.get("title") is not None:
                all_ads.append(ad_data)
                seen_urls.add(link)
                print(f"      ✅ {ad_data.get('title', 'Sans titre')} - {ad_data.get('price', 'Prix non indiqué')} - {ad_data.get('surface', '?')} m²")
            else:
                print(f"      ⚠️ Annonce ignorée (données manquantes) : {link}")
            await random_delay(0.5, 2)

    await browser.close()
    return all_ads

async def main():
    print("🚀 Lancement du scraper Mubawab (3 premières pages + version indétectable)...")
    async with async_playwright() as p:
        all_ads = await scrape_all_pages(p, BASE_URL)
        print(f"\n✅ Scraping terminé. Total d'annonces : {len(all_ads)}")
        for idx, ad in enumerate(all_ads, 1):
            print(f"\n--- Annonce {idx} ---")
            print(f"URL: {ad.get('url')}")
            print(f"Titre: {ad.get('title')}")
            print(f"Prix: {ad.get('price')}")
            print(f"Surface: {ad.get('surface')} m²")
            print(f"Type: {ad.get('type_bien')}")
            print(f"Localisation: {ad.get('location')}")
            desc = ad.get('description', '')
            if desc:
                print(f"Description: {desc[:300]}{'...' if len(desc) > 300 else ''}")
            else:
                print("Description: (non trouvée)")

if __name__ == "__main__":
    asyncio.run(main())