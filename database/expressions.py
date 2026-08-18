# database/expressions.py
"""Expressions SQLAlchemy partagees, pour eviter de dupliquer le nettoyage
numerique (ex: "720 000 DH" -> 720000.0) dans chaque requete qui en a besoin
(get_projets_resume, get_prix_m2_stats, filtrer_produits, stats_service...).
"""
from sqlalchemy import Float, Numeric, cast, func


def clean_numeric_col(column, unit=None):
    """CAST(REPLACE(REPLACE(column, unit, ''), ' ', '') AS REAL)."""
    expr = column
    if unit:
        expr = func.replace(expr, unit, '')
    expr = func.replace(expr, ' ', '')
    return cast(expr, Float)


def prix_m2_expr(prix_col, surface_col, prix_unit='DH', surface_unit='m²'):
    """ROUND(prix_nettoye / NULLIF(surface_nettoyee, 0), 2).

    Cast explicite en Numeric avant ROUND : PostgreSQL n'a pas de
    round(double precision, integer) (seulement round(double precision) a 1
    argument, ou round(numeric, integer)), contrairement a SQLite qui accepte
    round(real, int) sans probleme.
    """
    prix = clean_numeric_col(prix_col, prix_unit)
    surface = clean_numeric_col(surface_col, surface_unit)
    return func.round(cast(prix / func.nullif(surface, 0), Numeric), 2)
