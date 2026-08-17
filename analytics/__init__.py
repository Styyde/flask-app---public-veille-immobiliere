# analytics/__init__.py
from .scorer import (
    identifier_opportunites,
    get_top_opportunities_for_email,
    afficher_top_opportunites,
)

__all__ = [
    "identifier_opportunites",
    "get_top_opportunities_for_email",
    "afficher_top_opportunites",
]