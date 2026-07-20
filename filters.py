# filters.py
import sqlite3
import pandas as pd
from config import DB_PATH
from database.db_manager import get_annonces_sarouty_filtered

def get_filtered_data(
    source='all',
    budget_min=None, budget_max=None,
    ville=None, type_bien=None, badge=None, etage=None,
    prix_m2_min=None, prix_m2_max=None,
    surface_min=None, surface_max=None,
    limit=None
):
    print(f"🔍 Filtrage demandé : source={source}, ville={ville}, type={type_bien}")  # LOG CONSOLE
    dfs = []
    
    # ---- 1. AL OMRANE ----
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
        if budget_min is not None: query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) >= ?"; params.append(budget_min)
        if budget_max is not None: query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) <= ?"; params.append(budget_max)
        if ville: query += " AND p.localisation = ?"; params.append(ville)
        if type_bien: query += " AND p.type_bien = ?"; params.append(type_bien)
        if badge: query += " AND p.badge = ?"; params.append(badge)
        if etage: query += " AND pr.etage = ?"; params.append(etage)
        if prix_m2_min is not None: query += " AND prix_m2 >= ?"; params.append(prix_m2_min)
        if prix_m2_max is not None: query += " AND prix_m2 <= ?"; params.append(prix_m2_max)
        if surface_min is not None: query += " AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) >= ?"; params.append(surface_min)
        if surface_max is not None: query += " AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) <= ?"; params.append(surface_max)
        query += " ORDER BY prix_m2 ASC"
        if limit: query += " LIMIT ?"; params.append(limit)
        
        df_al = pd.read_sql_query(query, conn, params=params)
        conn.close()
        if not df_al.empty:
            dfs.append(df_al)

    # ---- 2. SAROUTY ----
    if source in ('all', 'sarouty'):
        sarouty_filters = {}
        if budget_min is not None: sarouty_filters['budget_min'] = budget_min
        if budget_max is not None: sarouty_filters['budget_max'] = budget_max
        if ville: sarouty_filters['ville'] = ville
        if type_bien: sarouty_filters['type_bien'] = type_bien
        if prix_m2_min is not None: sarouty_filters['prix_m2_min'] = prix_m2_min
        if prix_m2_max is not None: sarouty_filters['prix_m2_max'] = prix_m2_max
        if surface_min is not None: sarouty_filters['superficie_min'] = surface_min
        if surface_max is not None: sarouty_filters['superficie_max'] = surface_max
        
        sarouty_data = get_annonces_sarouty_filtered(**sarouty_filters)
        if sarouty_data:
            df_sar = pd.DataFrame(sarouty_data)
            # Renommage pour correspondre aux colonnes Al Omrane
            df_sar.rename(columns={
                'titre': 'projet',
                'ville': 'ville',
                'type_bien': 'type_bien',
                'prix': 'prix_brut',  # on garde pour calcul
                'superficie': 'surface_m2',
                'date_extraction': 'date_extraction'
            }, inplace=True)
            
            # Ajout des colonnes manquantes avec des valeurs par défaut
            df_sar['region'] = 'Maroc'
            df_sar['badge'] = None
            df_sar['lot'] = None
            df_sar['unites'] = None
            df_sar['prix_lot_min'] = None
            df_sar['prix_lot_max'] = None
            df_sar['produit'] = None
            df_sar['etage'] = None
            df_sar['designation'] = None
            df_sar['source'] = 'Sarouty'
            
            # Formatage surface et prix pour l'affichage
            df_sar['surface'] = df_sar['surface_m2'].astype(str) + ' m²'
            df_sar['prix'] = df_sar['prix_brut'].astype(str) + ' DH'
            df_sar['prix_m2'] = df_sar.apply(
                lambda row: round(row['prix_brut'] / row['surface_m2'], 2) if row['surface_m2'] and row['surface_m2'] > 0 else None,
                axis=1
            )
            
            # Conserver uniquement les colonnes identiques aux deux DataFrames
            common_cols = ['projet', 'ville', 'region', 'type_bien', 'badge', 'date_extraction',
                           'lot', 'unites', 'prix_lot_min', 'prix_lot_max', 'produit',
                           'surface', 'prix', 'etage', 'designation', 'source', 'prix_m2']
            # Si une colonne commune n'existe pas, on la crée vide
            for col in common_cols:
                if col not in df_sar.columns:
                    df_sar[col] = None
            df_sar = df_sar[common_cols]
            dfs.append(df_sar)

    if not dfs:
        print("⚠️ Aucune donnée trouvée pour les filtres.")
        return pd.DataFrame()
    
    # Fusionner les deux sources
    df_final = pd.concat(dfs, ignore_index=True)
    if not df_final.empty and 'prix_m2' in df_final.columns:
        df_final = df_final.sort_values('prix_m2')
    if limit:
        df_final = df_final.head(limit)
    
    print(f"✅ Résultat : {len(df_final)} lignes retournées.")
    return df_final

def get_statistiques_globales():
    from database.db_manager import get_statistiques_globales as db_stats
    return db_stats()

def get_prix_m2_moyen_par_groupe(ville=None, type_bien=None, etage=None):
    from database.db_manager import get_prix_m2_stats
    return get_prix_m2_stats(ville, type_bien, etage)