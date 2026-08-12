# database/expressions.py
"""Expressions SQLAlchemy partagees, pour eviter de dupliquer le nettoyage
numerique (ex: "720 000 DH" -> 720000.0) dans chaque requete qui en a besoin
(get_projets_resume, get_prix_m2_stats, filtrer_produits, stats_service...).
"""
from sqlalchemy import Float, cast, func


def clean_numeric_col(column, unit=None):
    """CAST(REPLACE(REPLACE(column, unit, ''), ' ', '') AS REAL)."""
    expr = column
    if unit:
        expr = func.replace(expr, unit, '')
    expr = func.replace(expr, ' ', '')
    return cast(expr, Float)


def prix_m2_expr(prix_col, surface_col, prix_unit='DH', surface_unit='m²'):
    """ROUND(prix_nettoye / NULLIF(surface_nettoyee, 0), 2)."""
    prix = clean_numeric_col(prix_col, prix_unit)
    surface = clean_numeric_col(surface_col, surface_unit)
    return func.round(prix / func.nullif(surface, 0), 2)
