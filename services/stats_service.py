# services/stats_service.py
# Statistiques pour l'analyse des données (distribution des prix)

import sqlite3
from config import DB_PATH

def get_stats_distribution(grouper="type_bien", filtre_etage=None, filtre_ville=None):
    """
    Retourne des statistiques groupées par un critère (type_bien, localisation, etage, badge).
    Calcule le nombre de produits, prix moyen, prix min, prix max, surface moyenne.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Construction de la requête
    query = f"""
        SELECT 
            p.{grouper} as groupe,
            COUNT(pr.id) as nb_produits,
            AVG(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) / 
                NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0)) as prix_m2_moyen,
            MIN(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL)) as prix_min,
            MAX(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL)) as prix_max,
            AVG(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL)) as surface_moyenne
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

    query += f" GROUP BY p.{grouper} ORDER BY prix_m2_moyen ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        stats.append({
            "groupe": row[0],
            "nb_produits": row[1],
            "prix_m2_moyen": round(row[2], 2) if row[2] else 0,
            "prix_min": row[3] or 0,
            "prix_max": row[4] or 0,
            "surface_moyenne": round(row[5], 2) if row[5] else 0
        })

    return stats