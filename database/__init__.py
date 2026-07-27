# database/__init__.py
from .db_manager import (
    init_db,
    get_existing_urls,
    save_projets,
    get_all_projets,
    get_annonces_sarouty_filtered,
    save_annonces_sarouty,
    get_statistiques_globales,
    get_projet_detail,
    get_projets_resume,
    save_annonces_mubawab,
    get_annonces_mubawab_filtered,
    get_villes_by_source,
    get_types_by_source,
)

__all__ = [
    "init_db",
    "get_existing_urls",
    "save_projets",
    "get_all_projets",
    "get_annonces_sarouty_filtered",
    "save_annonces_sarouty",
    "get_statistiques_globales",
    "get_projet_detail",
    "get_projets_resume",
    "save_annonces_mubawab",
    "get_annonces_mubawab_filtered",
    "get_villes_by_source",
    "get_types_by_source",
]