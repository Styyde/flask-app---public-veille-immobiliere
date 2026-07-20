# filters.py
import sqlite3
import pandas as pd
from config import DB_PATH
from database.db_manager import get_annonces_sarouty_filtered

def get_filtered_data(
    source='all',
    budget_min=None,
    budget_max=None,
    ville=None,
    type_bien=None,
    badge=None,
    etage=None,
    prix_m2_min=None,
    prix_m2_max=None,
    surface_min=None,
    surface_max=None,
    limit=None
):
    """
    Retourne un DataFrame pandas des produits/annonces filtrés.
    source : 'alomrane', 'sarouty', 'all'
    """
    dfs = []
    
    # --- Source Al Omrane ---
    if source in ('all', 'alomrane'):
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT 
                p.titre AS projet,
                p.localisation AS ville,
                p.region,
                p.type_bien,
                p.badge,
                p.date_extraction,
                l.lot_titre AS lot,
                l.nb_unites AS unites,
                l.prix_min AS prix_lot_min,
                l.prix_max AS prix_lot_max,
                pr.no_produit AS produit,
                pr.surface,
                pr.prix,
                pr.etage,
                pr.designation,
                CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) AS surface_m2,
                CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) AS prix_brut,
                ROUND(
                    CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) / 
                    CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL),
                    2
                ) AS prix_m2,
                'Al Omrane' AS source
            FROM produits pr
            JOIN lots l ON l.id = pr.lot_id
            JOIN projets p ON p.id = l.projet_id
            WHERE 1=1
        """
        params = []
        if budget_min is not None:
            query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) >= ?"
            params.append(budget_min)
        if budget_max is not None:
            query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) <= ?"
            params.append(budget_max)
        if ville:
            query += " AND p.localisation = ?"
            params.append(ville)
        if type_bien:
            query += " AND p.type_bien = ?"
            params.append(type_bien)
        if badge:
            query += " AND p.badge = ?"
            params.append(badge)
        if etage:
            query += " AND pr.etage = ?"
            params.append(etage)
        if prix_m2_min is not None:
            query += " AND prix_m2 >= ?"
            params.append(prix_m2_min)
        if prix_m2_max is not None:
            query += " AND prix_m2 <= ?"
            params.append(prix_m2_max)
        if surface_min is not None:
            query += " AND surface_m2 >= ?"
            params.append(surface_min)
        if surface_max is not None:
            query += " AND surface_m2 <= ?"
            params.append(surface_max)
        query += " ORDER BY prix_m2 ASC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        df_alomrane = pd.read_sql_query(query, conn, params=params)
        conn.close()
        if not df_alomrane.empty:
            dfs.append(df_alomrane)

    # --- Source Sarouty ---
    if source in ('all', 'sarouty'):
        filters = {}
        if budget_min is not None:
            filters['budget_min'] = budget_min
        if budget_max is not None:
            filters['budget_max'] = budget_max
        if ville:
            filters['ville'] = ville
        if type_bien:
            filters['type_bien'] = type_bien
        if prix_m2_min is not None:
            filters['prix_m2_min'] = prix_m2_min
        if prix_m2_max is not None:
            filters['prix_m2_max'] = prix_m2_max
        if surface_min is not None:
            filters['superficie_min'] = surface_min
        if surface_max is not None:
            filters['superficie_max'] = surface_max
        sarouty_data = get_annonces_sarouty_filtered(**filters)
        if sarouty_data:
            df_sarouty = pd.DataFrame(sarouty_data)
            # Renommer pour correspondre aux colonnes Al Omrane
            df_sarouty.rename(columns={
                'titre': 'projet',
                'ville': 'ville',
                'type_bien': 'type_bien',
                'prix': 'prix_brut',
                'superficie': 'surface_m2',
                'url_annonce': 'url',
                'date_extraction': 'date_extraction'
            }, inplace=True)
            # Ajouter des colonnes manquantes pour l'uniformisation
            df_sarouty['region'] = 'Maroc'
            df_sarouty['badge'] = None
            df_sarouty['lot'] = None
            df_sarouty['unites'] = None
            df_sarouty['prix_lot_min'] = None
            df_sarouty['prix_lot_max'] = None
            df_sarouty['produit'] = None
            df_sarouty['surface'] = df_sarouty['surface_m2'].astype(str) + ' m²'
            df_sarouty['prix'] = df_sarouty['prix_brut'].astype(str) + ' DH'
            df_sarouty['etage'] = None
            df_sarouty['designation'] = None
            df_sarouty['source'] = 'Sarouty'
            df_sarouty['prix_m2'] = df_sarouty.apply(
                lambda row: round(row['prix_brut'] / row['surface_m2'], 2) if row['surface_m2'] and row['surface_m2'] > 0 else None,
                axis=1
            )
            # Garder seulement les colonnes communes pour l'affichage
            common_cols = ['projet', 'ville', 'region', 'type_bien', 'badge', 'date_extraction',
                           'lot', 'unites', 'prix_lot_min', 'prix_lot_max', 'produit',
                           'surface', 'prix', 'etage', 'designation', 'source', 'prix_m2']
            for col in common_cols:
                if col not in df_sarouty.columns:
                    df_sarouty[col] = None
            df_sarouty = df_sarouty[common_cols]
            dfs.append(df_sarouty)

    if not dfs:
        return pd.DataFrame()
    df_final = pd.concat(dfs, ignore_index=True)
    if 'prix_m2' in df_final.columns:
        df_final = df_final.sort_values('prix_m2')
    if limit:
        df_final = df_final.head(limit)
    return df_final

def get_statistiques_globales():
    from database.db_manager import get_statistiques_globales as db_stats
    return db_stats()

def get_prix_m2_moyen_par_groupe(ville=None, type_bien=None, etage=None):
    from database.db_manager import get_prix_m2_stats
    return get_prix_m2_stats(ville, type_bien, etage)