# scraper/__init__.py
# Rend le dossier "scraper" un package Python importable

from .core import (
    click_element,
    get_page_soup,
    scroll_to_bottom,
    extraire_lots,
    extraire_detail_projet,
    ajouter_parametre_url,
    extraire_types_depuis_url,
    retour_liste,
    scrape_combination
)
from .runner import run_full_scraping

__all__ = [
    "click_element",
    "get_page_soup",
    "scroll_to_bottom",
    "extraire_lots",
    "extraire_detail_projet",
    "ajouter_parametre_url",
    "extraire_types_depuis_url",
    "retour_liste",
    "scrape_combination",
    "run_full_scraping"
]