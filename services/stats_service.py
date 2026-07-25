# services/stats_service.py
import sqlite3
import statistics
from config import DB_PATH

ALLOWED_GROUPERS = {'type_bien', 'localisation', 'badge', 'etage'}


def get_stats_distribution(grouper="type_bien", filtre_etage=None, filtre_ville=None):
    """Statistiques groupées par critère (Al Omrane)."""
    if grouper not in ALLOWED_GROUPERS:
        grouper = 'type_bien'

    col = f"p.{grouper}" if grouper != 'etage' else "pr.etage"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = f"""
        SELECT
            {col} AS groupe,
            COUNT(pr.id) AS nb_produits,
            AVG(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) /
                NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0)) AS prix_m2_moyen,
            MIN(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL)) AS prix_min,
            MAX(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL)) AS prix_max,
            AVG(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL)) AS surface_moyenne
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE 1=1
    """
    params = []

    if filtre_etage:
        if filtre_etage.lower() == "inconnu":
            query += " AND (pr.etage IS NULL OR pr.etage = '')"
        else:
            query += " AND pr.etage = ?"
            params.append(filtre_etage)
    if filtre_ville:
        query += " AND p.localisation = ?"
        params.append(filtre_ville)

    query += f" GROUP BY {col} ORDER BY prix_m2_moyen ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{
        "groupe": row[0] or "Inconnu",
        "nb_produits": row[1],
        "prix_m2_moyen": round(row[2], 2) if row[2] else 0,
        "prix_min": row[3] or 0,
        "prix_max": row[4] or 0,
        "surface_moyenne": round(row[5], 2) if row[5] else 0,
    } for row in rows]


def get_distribution_prix_m2(group_by="type_bien", filtre_ville=None, filtre_etage=None):
    grouper = group_by if group_by in ALLOWED_GROUPERS else 'type_bien'
    if grouper == 'localisation':
        grouper = 'localisation'
    return get_stats_distribution(grouper=grouper, filtre_ville=filtre_ville, filtre_etage=filtre_etage)


def get_distribution_etages(filtre_ville=None):
    return get_stats_distribution(grouper='etage', filtre_ville=filtre_ville)


def get_prix_m2_par_ville_et_etage(filtre_ville=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT
            p.localisation,
            pr.etage,
            AVG(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) /
                NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0)) AS prix_m2_moyen,
            COUNT(pr.id) AS nb
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE 1=1
    """
    params = []
    if filtre_ville:
        query += " AND p.localisation = ?"
        params.append(filtre_ville)
    query += " GROUP BY p.localisation, pr.etage ORDER BY prix_m2_moyen ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [{
        'ville': row[0],
        'etage': row[1] or 'Inconnu',
        'prix_m2_moyen': round(row[2], 2) if row[2] else 0,
        'nb': row[3],
    } for row in rows]


def get_histogram_prix_m2(filtre_ville=None, filtre_type=None, bins=10):
    """Histogramme des prix/m² pour Al Omrane."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT
            CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) /
            NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0) AS prix_m2
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) > 0
    """
    params = []
    if filtre_ville:
        query += " AND p.localisation = ?"
        params.append(filtre_ville)
    if filtre_type:
        query += " AND p.type_bien = ?"
        params.append(filtre_type)
    cursor.execute(query, params)
    values = [row[0] for row in cursor.fetchall() if row[0] and row[0] > 0]
    conn.close()

    if not values:
        return {'labels': [], 'counts': [], 'seuil_opportunite': 0}

    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return {
            'labels': [f'{round(min_v)}'],
            'counts': [len(values)],
            'seuil_opportunite': round(min_v, 2),
        }

    step = (max_v - min_v) / bins
    counts = [0] * bins
    labels = []
    for i in range(bins):
        lo = min_v + i * step
        hi = lo + step
        labels.append(f'{round(lo):,}–{round(hi):,}')
        counts[i] = sum(1 for v in values if (lo <= v < hi) or (i == bins - 1 and v <= hi))

    seuil = statistics.quantiles(values, n=4)[0] if len(values) >= 4 else min_v
    return {
        'labels': labels,
        'counts': counts,
        'seuil_opportunite': round(seuil, 2),
    }
