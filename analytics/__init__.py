# analytics/__init__.py
from .scorer import (
    afficher_top_opportunites,
    get_top_opportunities_for_email,
    identifier_opportunites,
)

__all__ = [
    "afficher_top_opportunites",
    "get_top_opportunities_for_email",
    "identifier_opportunites",
]