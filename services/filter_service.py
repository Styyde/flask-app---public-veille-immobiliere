# services/filter_service.py
import sqlite3
import pandas as pd
from config import DB_PATH
from database.db_manager import (
    get_annonces_sarouty_filtered,
    get_annonces_mubawab_filtered,
    get_projets_resume,
    get_types_by_source,
    get_villes_by_source,
    get_statistiques_globales,
    get_prix_m2_stats,
)


def parse_filtres_from_request(args):
    """Parse les query params Flask en dict de filtres."""
    def _float(key):
        val = args.get(key)
        if val is not None and val != '':
            try:
                return float(val)
            except ValueError:
                return None
        return None

    def _int(key):
        val = args.get(key)
        if val is not None and val != '':
            try:
                return int(val)
            except ValueError:
                return None
        return None

    return {
        'source': args.get('source', 'all'),
        'budget_min': _float('budget_min'),
        'budget_max': _float('budget_max'),
        'ville': args.get('ville') or None,
        'type_bien': args.get('type_bien') or None,
        'badge': args.get('badge') or None,
        'etage': args.get('etage') or None,
        'prix_m2_min': _float('prix_m2_min'),
        'prix_m2_max': _float('prix_m2_max'),
        'surface_min': _float('surface_min'),
        'surface_max': _float('surface_max'),
        'limit': _int('limit'),
    }


def get_filtres_disponibles(source='all'):
    return {
        'types': get_types_by_source(source),
        'villes': get_villes_by_source(source),
    }


def filtrer_alomrane(**filters):
    """Retourne la liste des projets Al Omrane (résumé avec agrégats)."""
    f = {k: v for k, v in filters.items() if k != 'source'}
    return get_projets_resume(**f)


def _url_sarouty_fiable(row):
    """URL Sarouty fiable : le site redirige /acheter/{id} vers l'URL canonique."""
    pid = row.get('property_id')
    if pid:
        return f"https://www.sarouty.ma/acheter/{pid}"
    url = row.get('url_annonce')
    if url and url.startswith('http') and ' ' not in url and 'None' not in url:
        return url
    return None


def filtrer_sarouty(**filters):
    """Retourne les annonces Sarouty formatées pour l'UI."""
    sarouty_filters = {}
    mapping = {
        'budget_min': 'budget_min',
        'budget_max': 'budget_max',
        'ville': 'ville',
        'type_bien': 'type_bien',
        'prix_m2_min': 'prix_m2_min',
        'prix_m2_max': 'prix_m2_max',
        'surface_min': 'superficie_min',
        'surface_max': 'superficie_max',
    }
    for src, dst in mapping.items():
        if filters.get(src) is not None:
            sarouty_filters[dst] = filters[src]

    rows = get_annonces_sarouty_filtered(**sarouty_filters)
    result = []
    for row in rows:
        localisation = row.get('ville') or ''
        if row.get('quartier'):
            localisation = f"{row['quartier']}, {localisation}" if localisation else row['quartier']
        result.append({
            'id': row.get('id'),
            'property_id': row.get('property_id'),
            'projet': row.get('titre'),
            'localisation': localisation,
            'type': row.get('type_bien'),
            'surface': row.get('superficie'),
            'prix': row.get('prix'),
            'prix_m2': row.get('prix_m2'),
            'url_annonce': _url_sarouty_fiable(row),
        })
    return result


def filtrer_mubawab(**filters):
    """Retourne les annonces Mubawab formatées pour l'UI."""
    mubawab_filters = {}
    mapping = {
        'budget_min': 'budget_min',
        'budget_max': 'budget_max',
        'ville': 'ville',
        'type_bien': 'type_bien',
        'prix_m2_min': 'prix_m2_min',
        'prix_m2_max': 'prix_m2_max',
        'surface_min': 'superficie_min',
        'surface_max': 'superficie_max',
    }
    for src, dst in mapping.items():
        if filters.get(src) is not None:
            mubawab_filters[dst] = filters[src]

    rows = get_annonces_mubawab_filtered(**mubawab_filters)
    result = []
    for row in rows:
        result.append({
            'id': row.get('id'),
            'projet': row.get('titre'),
            'localisation': row.get('localisation') or row.get('ville'),
            'type': row.get('type_bien'),
            'surface': row.get('superficie'),
            'prix': row.get('prix'),
            'prix_m2': row.get('prix_m2'),
            'url_annonce': row.get('url_annonce'),
            'region': row.get('region'),
        })
    return result


def filtrer_produits(**filters):
    """Retourne les produits Al Omrane à plat (pour analytics et rétrocompat)."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            p.id AS projet_id,
            p.titre AS projet,
            p.localisation AS ville,
            p.region,
            p.type_bien,
            p.badge,
            p.url AS url_projet,
            l.lot_titre AS lot,
            pr.no_produit AS produit,
            pr.surface,
            pr.prix,
            pr.etage,
            pr.designation,
            pr.url AS url_produit,
            ROUND(
                CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) /
                NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0),
                2
            ) AS prix_m2,
            'Al Omrane' AS source
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE 1=1
    """
    params = []
    if filters.get('budget_min') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) >= ?"
        params.append(filters['budget_min'])
    if filters.get('budget_max') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) <= ?"
        params.append(filters['budget_max'])
    if filters.get('ville'):
        query += " AND p.localisation = ?"
        params.append(filters['ville'])
    if filters.get('type_bien'):
        query += " AND p.type_bien = ?"
        params.append(filters['type_bien'])
    if filters.get('badge'):
        query += " AND p.badge = ?"
        params.append(filters['badge'])
    if filters.get('etage'):
        query += " AND pr.etage = ?"
        params.append(filters['etage'])
    if filters.get('prix_m2_min') is not None:
        query += " AND prix_m2 >= ?"
        params.append(filters['prix_m2_min'])
    if filters.get('prix_m2_max') is not None:
        query += " AND prix_m2 <= ?"
        params.append(filters['prix_m2_max'])
    if filters.get('surface_min') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) >= ?"
        params.append(filters['surface_min'])
    if filters.get('surface_max') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) <= ?"
        params.append(filters['surface_max'])
    query += " ORDER BY prix_m2 ASC"
    if filters.get('limit'):
        query += " LIMIT ?"
        params.append(filters['limit'])

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    if df.empty:
        return []
    return df.where(pd.notnull(df), None).to_dict(orient='records')


def get_filtered_data(source='all', **filters):
    """Rétrocompatibilité : DataFrame unifié pour gui.py et scripts."""
    dfs = []
    if source in ('all', 'alomrane'):
        rows = filtrer_produits(**filters)
        if rows:
            dfs.append(pd.DataFrame(rows))
    if source in ('all', 'sarouty'):
        sarouty = filtrer_sarouty(**filters)
        if sarouty:
            df_s = pd.DataFrame(sarouty)
            df_s.rename(columns={
                'projet': 'projet',
                'localisation': 'ville',
                'type': 'type_bien',
                'url_annonce': 'url',
            }, inplace=True)
            df_s['source'] = 'Sarouty'
            df_s['surface'] = df_s['surface'].astype(str) + ' m²'
            df_s['prix'] = df_s['prix'].astype(str) + ' DH'
            dfs.append(df_s)
    if source in ('all', 'mubawab'):
        mubawab = filtrer_mubawab(**filters)
        if mubawab:
            df_m = pd.DataFrame(mubawab)
            df_m.rename(columns={
                'projet': 'projet',
                'localisation': 'ville',
                'type': 'type_bien',
                'url_annonce': 'url',
            }, inplace=True)
            df_m['source'] = 'Mubawab'
            df_m['surface'] = df_m['surface'].astype(str) + ' m²'
            df_m['prix'] = df_m['prix'].astype(str) + ' DH'
            dfs.append(df_m)
    if not dfs:
        return pd.DataFrame()
    df_final = pd.concat(dfs, ignore_index=True)
    if 'prix_m2' in df_final.columns:
        df_final = df_final.sort_values('prix_m2')
    if filters.get('limit'):
        df_final = df_final.head(filters['limit'])
    return df_final


def get_statistiques_globales_wrapper():
    return get_statistiques_globales()


def get_prix_m2_moyen_par_groupe(ville=None, type_bien=None, etage=None):
    return get_prix_m2_stats(ville, type_bien, etage)
