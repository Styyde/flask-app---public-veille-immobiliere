# services/__init__.py
# Export des services principaux

from .filter_service import filtrer_produits, get_filtres_disponibles
from .stats_service import get_stats_distribution

__all__ = [
    "filtrer_produits",
    "get_filtres_disponibles",
    "get_stats_distribution"
]