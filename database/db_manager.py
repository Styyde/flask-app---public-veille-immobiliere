# database/db_manager.py
import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # ---- Tables Al Omrane ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            region TEXT,
            type_bien TEXT,
            titre TEXT,
            localisation TEXT,
            titre_foncier TEXT,
            description TEXT,
            date_extraction DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id INTEGER NOT NULL,
            lot_titre TEXT,
            nb_unites TEXT,
            prix_min TEXT,
            prix_max TEXT,
            FOREIGN KEY (projet_id) REFERENCES projets (id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            no_produit TEXT,
            surface TEXT,
            prix TEXT,
            FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
        )
    """)

    # ---- Tables Sarouty ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS annonces_sarouty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER UNIQUE NOT NULL,
            url_annonce TEXT,
            titre TEXT,
            description TEXT,
            prix INTEGER,
            superficie INTEGER,
            chambres INTEGER,
            salles_de_bain INTEGER,
            type_bien TEXT,
            quartier TEXT,
            ville TEXT,
            date_extraction DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sarouty_ville ON annonces_sarouty (ville)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sarouty_type ON annonces_sarouty (type_bien)")

    # ---- Tables Mubawab ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS annonces_mubawab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_annonce TEXT UNIQUE NOT NULL,
            titre TEXT,
            description TEXT,
            prix INTEGER,
            superficie INTEGER,
            type_bien TEXT,
            localisation TEXT,
            ville TEXT,
            region TEXT,
            date_extraction DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mubawab_ville ON annonces_mubawab (ville)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mubawab_type ON annonces_mubawab (type_bien)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON projets (url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_localisation ON projets (localisation)")
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée avec succès.")

# ==================== AL OMRANE ====================
def get_existing_urls():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM projets")
    urls = {row[0] for row in cursor.fetchall()}
    conn.close()
    return urls

# ==================== LISTES DYNAMIQUES ====================

def get_types_by_source(source):
    conn = get_connection()
    cursor = conn.cursor()
    if source == 'alomrane':
        cursor.execute("SELECT DISTINCT type_bien FROM projets ORDER BY type_bien")
    elif source == 'sarouty':
        cursor.execute("SELECT DISTINCT type_bien FROM annonces_sarouty ORDER BY type_bien")
    elif source == 'mubawab':
        cursor.execute("SELECT DISTINCT type_bien FROM annonces_mubawab ORDER BY type_bien")
    else:
        cursor.execute("""
            SELECT DISTINCT type_bien FROM (
                SELECT type_bien FROM projets
                UNION
                SELECT type_bien FROM annonces_sarouty
                UNION
                SELECT type_bien FROM annonces_mubawab
            ) ORDER BY type_bien
        """)
    types = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return types

def get_villes_by_source(source):
    conn = get_connection()
    cursor = conn.cursor()
    if source == 'alomrane':
        cursor.execute("SELECT DISTINCT localisation FROM projets ORDER BY localisation")
    elif source == 'sarouty':
        cursor.execute("""
            SELECT DISTINCT valeur FROM (
                SELECT ville AS valeur FROM annonces_sarouty
                UNION
                SELECT quartier AS valeur FROM annonces_sarouty
            ) WHERE valeur IS NOT NULL AND valeur != '' ORDER BY valeur
        """)
    elif source == 'mubawab':
        cursor.execute("""
            SELECT DISTINCT valeur FROM (
                SELECT ville AS valeur FROM annonces_mubawab
                UNION
                SELECT localisation AS valeur FROM annonces_mubawab
            ) WHERE valeur IS NOT NULL AND valeur != '' ORDER BY valeur
        """)
    else:
        cursor.execute("""
            SELECT DISTINCT ville FROM (
                SELECT localisation AS ville FROM projets
                UNION
                SELECT ville FROM annonces_sarouty
                UNION
                SELECT quartier AS ville FROM annonces_sarouty
                UNION
                SELECT ville FROM annonces_mubawab
                UNION
                SELECT localisation AS ville FROM annonces_mubawab
            ) WHERE ville IS NOT NULL AND ville != '' ORDER BY ville
        """)
    villes = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return villes

def save_projets(projets_list):
    if not projets_list:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    try:
        cursor.execute("BEGIN TRANSACTION")
        for projet in projets_list:
            cursor.execute("""
                INSERT OR IGNORE INTO projets 
                (url, region, type_bien, titre, localisation, titre_foncier, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                projet.get('lien', ''),
                projet.get('region', ''),
                projet.get('type_bien', ''),
                projet.get('titre', ''),
                projet.get('localisation', ''),
                projet.get('titre_foncier', ''),
                projet.get('description', '')
            ))
            if cursor.rowcount > 0:
                inserted += 1
                projet_id = cursor.lastrowid
                for lot in projet.get('lots', []):
                    cursor.execute("""
                        INSERT INTO lots (projet_id, lot_titre, nb_unites, prix_min, prix_max)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        projet_id,
                        lot.get('titre', ''),
                        lot.get('nb_unites', ''),
                        lot.get('prix_min', ''),
                        lot.get('prix_max', '')
                    ))
                    lot_id = cursor.lastrowid
                    for ligne in lot.get('lignes', []):
                        cursor.execute("""
                            INSERT INTO produits (lot_id, no_produit, surface, prix)
                            VALUES (?, ?, ?, ?)
                        """, (
                            lot_id,
                            ligne.get('no_produit', ''),
                            ligne.get('surface', ''),
                            ligne.get('prix', '')
                        ))
        conn.commit()
        print(f"💾 {inserted} projets Al Omrane insérés.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Al Omrane : {e}")
    finally:
        conn.close()
    return inserted

def _parse_prix_m2(prix_str, surface_str):
    try:
        prix = float(str(prix_str).replace('DH', '').replace(' ', '').strip())
        surface = float(str(surface_str).replace('m²', '').replace(' ', '').strip())
        if surface > 0 and prix > 0:
            return round(prix / surface, 2)
    except (TypeError, ValueError):
        pass
    return None

def _enrich_produit(prod):
    row = dict(prod)
    row['prix_m2'] = _parse_prix_m2(row.get('prix'), row.get('surface'))
    return row

def get_projet_detail(projet_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projets WHERE id = ?", (projet_id,))
    p = cursor.fetchone()
    if not p:
        conn.close()
        return None
    projet = dict(p)
    projet['lots'] = []
    cursor.execute("SELECT * FROM lots WHERE projet_id = ?", (projet_id,))
    for lot in cursor.fetchall():
        lot_dict = dict(lot)
        cursor.execute("SELECT * FROM produits WHERE lot_id = ?", (lot['id'],))
        lot_dict['lignes'] = [_enrich_produit(prod) for prod in cursor.fetchall()]
        projet['lots'].append(lot_dict)
    conn.close()
    return projet

def get_projets_resume(**filters):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    prix_m2_expr = """
        ROUND(
            CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) /
            NULLIF(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL), 0),
            2
        )
    """

    query = f"""
        SELECT
            p.id,
            p.titre,
            p.localisation,
            p.type_bien,
            p.url,
            p.region,
            COUNT(DISTINCT l.id) AS nb_lots,
            COUNT(pr.id) AS nb_produits,
            MIN({prix_m2_expr}) AS prix_m2_min,
            MAX({prix_m2_expr}) AS prix_m2_max
        FROM projets p
        JOIN lots l ON l.projet_id = p.id
        JOIN produits pr ON pr.lot_id = l.id
        WHERE CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) > 0
    """
    params = []

    if filters.get('ville'):
        query += " AND p.localisation = ?"
        params.append(filters['ville'])
    if filters.get('type_brut_list'):
        brut_list = filters['type_brut_list']
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND p.type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"
    elif filters.get('type_bien'):
        from services.type_mapping import get_brut_types_for_normalized
        brut_list = get_brut_types_for_normalized(filters['type_bien'])
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND p.type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"
    if filters.get('budget_min') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) >= ?"
        params.append(filters['budget_min'])
    if filters.get('budget_max') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) <= ?"
        params.append(filters['budget_max'])
    if filters.get('surface_min') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) >= ?"
        params.append(filters['surface_min'])
    if filters.get('surface_max') is not None:
        query += " AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) <= ?"
        params.append(filters['surface_max'])
    if filters.get('prix_m2_min') is not None:
        query += f" AND {prix_m2_expr} >= ?"
        params.append(filters['prix_m2_min'])
    if filters.get('prix_m2_max') is not None:
        query += f" AND {prix_m2_expr} <= ?"
        params.append(filters['prix_m2_max'])

    query += " GROUP BY p.id ORDER BY prix_m2_min ASC"
    if filters.get('limit'):
        query += " LIMIT ?"
        params.append(filters['limit'])

    cursor.execute(query, params)
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result

def get_all_projets(limit=100):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    projets = []
    cursor.execute("SELECT * FROM projets ORDER BY date_extraction DESC LIMIT ?", (limit,))
    for p in cursor.fetchall():
        projet = dict(p)
        projet['lots'] = []
        cursor.execute("SELECT * FROM lots WHERE projet_id = ?", (p['id'],))
        for lot in cursor.fetchall():
            lot_dict = dict(lot)
            cursor.execute("SELECT * FROM produits WHERE lot_id = ?", (lot['id'],))
            lot_dict['lignes'] = [_enrich_produit(prod) for prod in cursor.fetchall()]
            projet['lots'].append(lot_dict)
        projets.append(projet)
    conn.close()
    return projets

# ==================== SAROUTY ====================
def save_annonces_sarouty(annonces_list):
    if not annonces_list:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    try:
        cursor.execute("BEGIN TRANSACTION")
        for a in annonces_list:
            cursor.execute("""
                INSERT OR IGNORE INTO annonces_sarouty 
                (property_id, url_annonce, titre, description, prix, superficie, chambres, salles_de_bain, type_bien, quartier, ville)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a.get('property_id'),
                a.get('url_annonce'),
                a.get('titre'),
                a.get('description'),
                a.get('prix', 0),
                a.get('superficie', 0),
                a.get('chambres'),
                a.get('salles_de_bain'),
                a.get('type_bien'),
                a.get('quartier'),
                a.get('ville')
            ))
            if cursor.rowcount > 0:
                inserted += 1
        conn.commit()
        print(f"💾 {inserted} annonces Sarouty insérées.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Sarouty : {e}")
    finally:
        conn.close()
    return inserted

def get_annonces_sarouty_filtered(**filters):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = """
        SELECT *, 
               ROUND(prix / NULLIF(superficie, 0), 2) AS prix_m2 
        FROM annonces_sarouty 
        WHERE 1=1
    """
    params = []
    if 'ville' in filters and filters['ville']:
        query += " AND (ville = ? OR quartier = ?)"
        params.append(filters['ville'])
        params.append(filters['ville'])
    
    if 'type_bien' in filters and filters['type_bien']:
        from services.type_mapping import get_brut_types_for_normalized
        brut_list = get_brut_types_for_normalized(filters['type_bien'])
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"
    elif 'type_brut_list' in filters and filters['type_brut_list']:
        brut_list = filters['type_brut_list']
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"

    if 'budget_min' in filters and filters['budget_min']:
        query += " AND prix >= ?"
        params.append(filters['budget_min'])
    if 'budget_max' in filters and filters['budget_max']:
        query += " AND prix <= ?"
        params.append(filters['budget_max'])
    if 'superficie_min' in filters and filters['superficie_min']:
        query += " AND superficie >= ?"
        params.append(filters['superficie_min'])
    if 'superficie_max' in filters and filters['superficie_max']:
        query += " AND superficie <= ?"
        params.append(filters['superficie_max'])
    if 'prix_m2_min' in filters and filters['prix_m2_min']:
        query += " AND ROUND(prix / NULLIF(superficie, 0), 2) >= ?"
        params.append(filters['prix_m2_min'])
    if 'prix_m2_max' in filters and filters['prix_m2_max']:
        query += " AND ROUND(prix / NULLIF(superficie, 0), 2) <= ?"
        params.append(filters['prix_m2_max'])
    query += " ORDER BY prix_m2 ASC"
    cursor.execute(query, params)
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result

# ==================== MUBAWAB ====================
def save_annonces_mubawab(annonces_list):
    if not annonces_list:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    try:
        cursor.execute("BEGIN TRANSACTION")
        for a in annonces_list:
            cursor.execute("""
                INSERT OR IGNORE INTO annonces_mubawab
                (url_annonce, titre, description, prix, superficie, type_bien, localisation, ville, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a.get('url_annonce') or a.get('url'),
                a.get('titre') or a.get('title'),
                a.get('description'),
                a.get('prix', 0),
                a.get('superficie') if a.get('superficie') is not None else a.get('surface', 0),
                a.get('type_bien'),
                a.get('localisation') or a.get('location'),
                a.get('ville'),
                a.get('region'),
            ))
            if cursor.rowcount > 0:
                inserted += 1
        conn.commit()
        print(f"💾 {inserted} annonces Mubawab insérées.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Mubawab : {e}")
    finally:
        conn.close()
    return inserted

def get_annonces_mubawab_filtered(**filters):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = """
        SELECT *,
               ROUND(prix / NULLIF(superficie, 0), 2) AS prix_m2
        FROM annonces_mubawab
        WHERE 1=1
    """
    params = []

    if 'ville' in filters and filters['ville']:
        query += " AND (ville = ? OR localisation = ?)"
        params.append(filters['ville'])
        params.append(filters['ville'])

    if 'type_bien' in filters and filters['type_bien']:
        from services.type_mapping import get_brut_types_for_normalized
        brut_list = get_brut_types_for_normalized(filters['type_bien'])
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"
    elif 'type_brut_list' in filters and filters['type_brut_list']:
        brut_list = filters['type_brut_list']
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"

    if 'region' in filters and filters['region']:
        query += " AND region = ?"
        params.append(filters['region'])
    if 'budget_min' in filters and filters['budget_min'] is not None:
        query += " AND prix >= ?"
        params.append(filters['budget_min'])
    if 'budget_max' in filters and filters['budget_max'] is not None:
        query += " AND prix <= ?"
        params.append(filters['budget_max'])
    if 'superficie_min' in filters and filters['superficie_min'] is not None:
        query += " AND superficie >= ?"
        params.append(filters['superficie_min'])
    if 'superficie_max' in filters and filters['superficie_max'] is not None:
        query += " AND superficie <= ?"
        params.append(filters['superficie_max'])
    if 'prix_m2_min' in filters and filters['prix_m2_min'] is not None:
        query += " AND ROUND(prix / NULLIF(superficie, 0), 2) >= ?"
        params.append(filters['prix_m2_min'])
    if 'prix_m2_max' in filters and filters['prix_m2_max'] is not None:
        query += " AND ROUND(prix / NULLIF(superficie, 0), 2) <= ?"
        params.append(filters['prix_m2_max'])

    query += " ORDER BY prix_m2 ASC"
    cursor.execute(query, params)
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result

# ==================== STATISTIQUES GLOBALES ====================
def get_statistiques_globales():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM projets")
    stats['nb_projets'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM lots")
    stats['nb_lots'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM produits")
    stats['nb_produits'] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM annonces_sarouty")
    stats['nb_sarouty'] = cursor.fetchone()[0]
    try:
        cursor.execute("SELECT COUNT(*) FROM annonces_mubawab")
        stats['nb_mubawab'] = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        stats['nb_mubawab'] = 0

    cursor.execute("SELECT DISTINCT localisation FROM projets")
    stats['villes'] = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT type_bien FROM projets")
    stats['types_biens'] = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT ville FROM annonces_sarouty")
    stats['villes_sarouty'] = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT type_bien FROM annonces_sarouty")
    stats['types_sarouty'] = [row[0] for row in cursor.fetchall()]
    try:
        cursor.execute("SELECT DISTINCT ville FROM annonces_mubawab")
        stats['villes_mubawab'] = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT type_bien FROM annonces_mubawab")
        stats['types_mubawab'] = [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        stats['villes_mubawab'] = []
        stats['types_mubawab'] = []
    conn.close()
    return stats

def get_prix_m2_stats(ville=None, type_bien=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            p.localisation,
            p.type_bien,
            pr.surface,
            pr.prix,
            CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) as surface_m2,
            CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) as prix_brut
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) > 0
    """
    params = []
    if ville:
        query += " AND p.localisation = ?"
        params.append(ville)
    if type_bien:
        from services.type_mapping import get_brut_types_for_normalized
        brut_list = get_brut_types_for_normalized(type_bien)
        if brut_list:
            placeholders = ','.join(['?'] * len(brut_list))
            query += f" AND p.type_bien IN ({placeholders})"
            params.extend(brut_list)
        else:
            query += " AND 1=0"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    prix_m2_list = []
    for row in rows:
        try:
            surface = float(row[4])
            prix = float(row[5])
            if surface > 0 and prix > 0:
                prix_m2_list.append(prix / surface)
        except:
            pass
    if not prix_m2_list:
        return {"moyenne": 0, "ecart_type": 0, "nombre": 0}
    import statistics
    return {
        "moyenne": round(statistics.mean(prix_m2_list), 2),
        "ecart_type": round(statistics.stdev(prix_m2_list), 2) if len(prix_m2_list) > 1 else 0,
        "nombre": len(prix_m2_list)
    }