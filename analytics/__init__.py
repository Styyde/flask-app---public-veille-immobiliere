# analytics/__init__.py
from .scorer import (
    calculer_prix_m2_tous_produits,
    identifier_opportunites,
    afficher_top_opportunites,
    get_top_opportunities_for_email
)

__all__ = [
    "calculer_prix_m2_tous_produits",
    "identifier_opportunites",
    "afficher_top_opportunites",
    "get_top_opportunities_for_email"
]