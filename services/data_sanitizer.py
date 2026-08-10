# services/data_sanitizer.py
"""
Règles de nettoyage et de normalisation des données immobilières.

Ces règles s'appliquent de manière transversale à toutes les sources
(Al Omrane, Sarouty, Mubawab) avant l'affichage ou le calcul statistique.

Règles métier :
  1. PRIX/M² ANORMAL  : si prix_m2 < SEUIL_PRIX_M2_MIN (400 DH), la valeur est
                        manifestement erronée (ex : prix en centaines et surface en m²).
                        Dans ce cas, on substitue prix_m2 par le prix total brut.
  2. EXCLUSION STATS  : toute annonce avec prix == 0 ou prix_m2 == 0 est exclue
                        des calculs statistiques (histogramme, moyennes, graphiques).
"""

import re

# ── Constantes ────────────────────────────────────────────────────────────────
SEUIL_PRIX_M2_MIN: float = 400.0   # DH — seuil en-dessous duquel prix/m² est suspect


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_float(val) -> float | None:
    """Convertit proprement une valeur en float, qu'il s'agisse d'un nombre ou
    d'une chaîne avec unités (DH, m², espaces, virgules…)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = re.sub(r'[^\d.]', '', str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


# ── Règle 1 : Correction du prix/m² anormal ───────────────────────────────────

def fix_prix_m2(prix_m2: float | None, prix: float | None) -> float | None:
    """
    Si le prix/m² est inférieur au seuil SEUIL_PRIX_M2_MIN, cela indique
    que la valeur est probablement le prix unitaire et non un vrai ratio.
    On substitue alors le prix total en guise de prix/m².

    Args:
        prix_m2: valeur prix/m² fournie par la source (peut être None).
        prix:    prix total de l'annonce.

    Returns:
        La valeur corrigée du prix/m², ou None si non calculable.
    """
    pm2 = _to_float(prix_m2)
    p   = _to_float(prix)

    if pm2 is None:
        return None
    if pm2 < SEUIL_PRIX_M2_MIN:
        # On retourne le prix total comme proxy du prix/m²
        return p if p and p > 0 else None
    return pm2


# ── Règle 2 : Filtre d'exclusion statistique ──────────────────────────────────

def is_valid_for_stats(prix: float | None, prix_m2: float | None) -> bool:
    """
    Retourne True si l'annonce est éligible aux calculs statistiques
    et aux meilleures opportunités.

    Une annonce est EXCLUE si :
      - son prix total est nul ou absent  (données incomplètes)
      - son prix/m² est nul ou absent     (ratio non calculable)
      - son prix/m² est < SEUIL_PRIX_M2_MIN (400 DH)  (valeur manifestement erronée)

    Args:
        prix:    prix total (float ou None).
        prix_m2: prix au m² (float ou None).

    Returns:
        bool — True = inclus dans les stats, False = exclu.
    """
    p   = _to_float(prix)
    pm2 = _to_float(prix_m2)

    if not p or p <= 0:
        return False
    if not pm2 or pm2 <= 0:
        return False
    if pm2 < SEUIL_PRIX_M2_MIN:
        return False
    return True


# ── API publique ──────────────────────────────────────────────────────────────

def sanitize_annonce_for_display(annonce: dict) -> dict:
    """
    Applique la RÈGLE 1 (correction du prix/m²) sur un dictionnaire d'annonce
    avant son envoi au frontend pour affichage.

    Le dict est muté sur place ET retourné pour faciliter le chaînage.
    """
    prix    = _to_float(annonce.get('prix'))
    prix_m2 = _to_float(annonce.get('prix_m2'))
    annonce['prix_m2'] = fix_prix_m2(prix_m2, prix)
    return annonce


def filter_for_stats(data: list[dict]) -> list[dict]:
    """
    Applique la RÈGLE 2 (exclusion des prix nuls) sur une liste d'annonces
    unifiées avant les calculs statistiques (graphiques, moyennes…).

    Args:
        data: liste de dicts unifiés (champs 'prix' et 'prix_m2' attendus).

    Returns:
        Sous-liste ne contenant que les annonces valides pour les stats.
    """
    return [
        d for d in data
        if is_valid_for_stats(d.get('prix'), d.get('prix_m2'))
    ]
