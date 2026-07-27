# services/stats_service.py
import sqlite3
from config import DB_PATH

ALLOWED_GROUPERS = {'type_bien', 'localisation'}

def get_stats_distribution(grouper="type_bien", filtre_ville=None):
    if grouper not in ALLOWED_GROUPERS:
        grouper = 'type_bien'
    col = f"p.{grouper}"
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
        WHERE CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) > 0
    """
    params = []
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

def get_distribution_prix_m2(group_by="type_bien", filtre_ville=None):
    return get_stats_distribution(grouper=group_by, filtre_ville=filtre_ville)

def get_histogram_prix_m2(filtre_ville=None, filtre_type=None, bins=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = """
        SELECT
            CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) /
            NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0) AS prix_m2
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) > 0
          AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) > 0
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
    import statistics
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return {
            'labels': [f'{round(min_v)}'],
            'counts': [len(values)],
            'seuil_opportunite': round(min_v, 2)
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
        'seuil_opportunite': round(seuil, 2)
    }