# database/__init__.py
from .db_manager import (
    get_all_projets,
    get_annonces_mubawab_filtered,
    get_annonces_sarouty_filtered,
    get_existing_urls,
    get_projet_detail,
    get_projets_resume,
    get_statistiques_globales,
    get_types_by_source,
    get_villes_by_source,
    init_db,
    save_annonces_mubawab,
    save_annonces_sarouty,
    save_projets,
)

__all__ = [
    "get_all_projets",
    "get_annonces_mubawab_filtered",
    "get_annonces_sarouty_filtered",
    "get_existing_urls",
    "get_projet_detail",
    "get_projets_resume",
    "get_statistiques_globales",
    "get_types_by_source",
    "get_villes_by_source",
    "init_db",
    "save_annonces_mubawab",
    "save_annonces_sarouty",
    "save_projets",
]