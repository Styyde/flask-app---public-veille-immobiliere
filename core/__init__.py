# scraper/__init__.py
# Rend le dossier "scraper" un package Python importable

from .core import (
    ajouter_parametre_url,
    click_element,
    extraire_detail_projet,
    extraire_lots,
    extraire_types_depuis_url,
    get_page_soup,
    retour_liste,
    scrape_combination,
    scroll_to_bottom,
)
from .runner import run_full_scraping

__all__ = [
    "ajouter_parametre_url",
    "click_element",
    "extraire_detail_projet",
    "extraire_lots",
    "extraire_types_depuis_url",
    "get_page_soup",
    "retour_liste",
    "run_full_scraping",
    "scrape_combination",
    "scroll_to_bottom"
]