# scraper/mubawab_scraper_single.py
import asyncio
import re
import random

from playwright.async_api import async_playwright

from config import MUBAWAB_REGIONS, MUBAWAB_MAX_PAGES, MUBAWAB_HEADLESS
from database.db_manager import save_annonces_mubawab, init_db

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def parse_prix(prix_str):
    if not prix_str:
        return 0
    digits = re.sub(r"[^\d]", "", str(prix_str))
    try:
        return int(digits) if digits else 0
    except ValueError:
        return 0


def parse_surface(surface_val):
    if surface_val is None:
        return 0
    if isinstance(surface_val, (int, float)):
        return int(surface_val)
    digits = re.sub(r"[^\d]", "", str(surface_val))
    try:
        return int(digits) if digits else 0
    except ValueError:
        return 0


def extraire_ville(localisation, region_key=None):
    if localisation:
        parts = [p.strip() for p in localisation.split(",") if p.strip()]
        if parts:
            return parts[-1]
    if region_key and region_key in MUBAWAB_REGIONS:
        return MUBAWAB_REGIONS[region_key]["nom"]
    return None


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
    except Exception:
        pass

    data = {"url": url}

    try:
        title_elem = await page.query_selector("h1.searchTitle")
        data["title"] = await title_elem.inner_text() if title_elem else None
    except Exception:
        data["title"] = None

    try:
        price_elem = await page.query_selector("h3.orangeTit")
        data["price"] = await price_elem.inner_text() if price_elem else None
    except Exception:
        data["price"] = None

    try:
        loc_elem = await page.query_selector("h3.greyTit")
        data["location"] = await loc_elem.inner_text() if loc_elem else None
    except Exception:
        data["location"] = None

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
                    match = re.search(r"([\d\s]+)\s*m²", text)
                    if match:
                        surface = match.group(1).replace(" ", "")
                        break
    except Exception:
        pass
    data["surface"] = surface

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
    except Exception:
        pass
    data["type_bien"] = type_bien

    description = None
    scripts = await page.query_selector_all("script")
    for script in scripts:
        try:
            content = await script.inner_text()
            match = re.search(r'"description"\s*:\s*"([^"]*?)"', content, re.DOTALL)
            if match:
                desc = match.group(1)
                desc = desc.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/")
                if desc.strip():
                    description = desc
                    break
        except Exception:
            continue

    if not description:
        try:
            meta_desc = await page.query_selector('meta[name="description"]')
            if meta_desc:
                desc = await meta_desc.get_attribute("content")
                if desc and desc.strip():
                    description = desc
        except Exception:
            pass

    if not description:
        try:
            block_prop = await page.query_selector("div.blockProp")
            if block_prop:
                desc = await block_prop.inner_text()
                if desc.strip():
                    description = desc
        except Exception:
            pass

    if not description:
        try:
            paragraphs = await page.query_selector_all("p")
            for p in paragraphs:
                text = await p.inner_text()
                if len(text.strip()) > 50:
                    description = text
                    break
        except Exception:
            pass

    if description:
        description = re.sub(r"\s+", " ", description).strip()
    data["description"] = description
    return data


async def get_total_pages(page, base_url):
    await page.goto(base_url, timeout=20000)
    await random_delay(1, 2)
    try:
        await page.wait_for_selector("div.listingBox", timeout=15000)
    except Exception:
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
        except ValueError:
            continue

    if max_page == 1:
        for dot in dots:
            href = await dot.get_attribute("href")
            if href:
                match = re.search(r":p:(\d+)", href)
                if match:
                    num = int(match.group(1))
                    if num > max_page:
                        max_page = num
    return max_page


async def scrape_all_pages(playwright, base_url, max_pages=None, headless=True, region_key=None):
    max_pages = max_pages or MUBAWAB_MAX_PAGES
    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
        ],
    )
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        extra_http_headers={
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    page = await context.new_page()
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
    """)

    total_pages = await get_total_pages(page, base_url)
    pages_to_scrape = list(range(1, min(total_pages, max_pages) + 1))
    print(f"📚 Pages Mubawab : {total_pages} détectées, scraping {pages_to_scrape}")

    all_ads = []
    seen_urls = set()
    region_nom = MUBAWAB_REGIONS.get(region_key, {}).get("nom") if region_key else None

    for page_num in pages_to_scrape:
        current_url = base_url + f":p:{page_num}"
        print(f"\n📄 Page {page_num} : {current_url}")
        await page.goto(current_url, timeout=20000)
        await random_delay(1.5, 3)
        try:
            await page.wait_for_selector("div.listingBox", timeout=10000)
        except Exception:
            print(f"   ⚠️ Aucune annonce sur la page {page_num}")
            break

        links = await extract_listing_links(page)
        print(f"   {len(links)} annonces trouvées.")

        for link in links:
            if link in seen_urls:
                continue
            ad_data = await extract_ad_detail(page, link)
            if ad_data and ad_data.get("title"):
                all_ads.append({
                    "url_annonce": ad_data.get("url"),
                    "titre": ad_data.get("title"),
                    "description": ad_data.get("description"),
                    "prix": parse_prix(ad_data.get("price")),
                    "superficie": parse_surface(ad_data.get("surface")),
                    "type_bien": ad_data.get("type_bien"),
                    "localisation": ad_data.get("location"),
                    "ville": extraire_ville(ad_data.get("location"), region_key),
                    "region": region_nom,
                })
                seen_urls.add(link)
                print(f"      ✅ {ad_data.get('title')} - {ad_data.get('price')}")
            await random_delay(0.5, 2)

    await browser.close()
    return all_ads


async def scraper_mubawab(region="rabat", max_pages=None, headless=None):
    """
    Scrape Mubawab pour une région et enregistre en base.
    region: 'casablanca' | 'rabat' | 'all'
    """
    init_db()
    headless = MUBAWAB_HEADLESS if headless is None else headless
    max_pages = max_pages or MUBAWAB_MAX_PAGES

    if region == "all":
        regions = list(MUBAWAB_REGIONS.keys())
    elif region in MUBAWAB_REGIONS:
        regions = [region]
    else:
        raise ValueError(f"Région Mubawab invalide : {region}")

    total_inserted = 0
    async with async_playwright() as p:
        for region_key in regions:
            info = MUBAWAB_REGIONS[region_key]
            print(f"🚀 Scraping Mubawab — {info['nom']}")
            ads = await scrape_all_pages(
                p,
                info["url"],
                max_pages=max_pages,
                headless=headless,
                region_key=region_key,
            )
            total_inserted += save_annonces_mubawab(ads)

    return total_inserted


def scraper_mubawab_sync(region="rabat", max_pages=None, headless=None):
    """Wrapper synchrone pour l'API Flask."""
    return asyncio.run(scraper_mubawab(region=region, max_pages=max_pages, headless=headless))


async def main():
    nb = await scraper_mubawab(region="rabat", headless=False)
    print(f"\n✅ Scraping terminé. {nb} nouvelles annonces.")


if __name__ == "__main__":
    asyncio.run(main())
