# services/__init__.py
from .filter_service import (
    filtrer_produits,
    filtrer_alomrane,
    filtrer_sarouty,
    filtrer_mubawab,
    get_filtres_disponibles,
    get_filtered_data,
    parse_filtres_from_request,
    get_statistiques_globales_wrapper,
    get_prix_m2_moyen_par_groupe,
)
from .stats_service import get_stats_distribution
from .analysis_service import get_analytics_dashboard, analyser_opportunites

__all__ = [
    "filtrer_produits",
    "filtrer_alomrane",
    "filtrer_sarouty",
    "filtrer_mubawab",
    "get_filtres_disponibles",
    "get_filtered_data",
    "parse_filtres_from_request",
    "get_statistiques_globales_wrapper",
    "get_prix_m2_moyen_par_groupe",
    "get_stats_distribution",
    "get_analytics_dashboard",
    "analyser_opportunites",
]
