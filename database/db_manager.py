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
            badge TEXT,
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
            etage TEXT,
            designation TEXT,
            url TEXT,
            FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE
        )
    """)
    # Migrations Al Omrane
    for col in ['etage', 'designation', 'url']:
        try:
            cursor.execute(f"ALTER TABLE produits ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

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
# database/db_manager.py
# ... (garder tout le code existant) ...

# ==================== FONCTIONS POUR LES LISTES DYNAMIQUES ====================

def get_types_by_source(source):
    """
    Retourne la liste des types de biens disponibles pour une source donnée.
    source: 'alomrane', 'sarouty', ou 'all'
    """
    conn = get_connection()
    cursor = conn.cursor()
    if source == 'alomrane':
        cursor.execute("SELECT DISTINCT type_bien FROM projets ORDER BY type_bien")
    elif source == 'sarouty':
        cursor.execute("SELECT DISTINCT type_bien FROM annonces_sarouty ORDER BY type_bien")
    else:  # 'all'
        cursor.execute("""
            SELECT DISTINCT type_bien FROM (
                SELECT type_bien FROM projets
                UNION
                SELECT type_bien FROM annonces_sarouty
            ) ORDER BY type_bien
        """)
    types = [row[0] for row in cursor.fetchall() if row[0] is not None and row[0] != '']
    conn.close()
    return types



def get_types_by_source(source):
    """
    Retourne la liste des types de biens disponibles pour une source donnée.
    source: 'alomrane', 'sarouty', ou 'all'
    """
    conn = get_connection()
    cursor = conn.cursor()
    if source == 'alomrane':
        cursor.execute("SELECT DISTINCT type_bien FROM projets ORDER BY type_bien")
    elif source == 'sarouty':
        cursor.execute("SELECT DISTINCT type_bien FROM annonces_sarouty ORDER BY type_bien")
    else:  # 'all'
        cursor.execute("""
            SELECT DISTINCT type_bien FROM (
                SELECT type_bien FROM projets
                UNION
                SELECT type_bien FROM annonces_sarouty
            ) ORDER BY type_bien
        """)
    types = [row[0] for row in cursor.fetchall() if row[0] is not None and row[0] != '']
    conn.close()
    return types

def get_villes_by_source(source):
    """
    Retourne la liste des villes disponibles pour une source donnée.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if source == 'alomrane':
        cursor.execute("SELECT DISTINCT localisation FROM projets ORDER BY localisation")
    elif source == 'sarouty':
        cursor.execute("SELECT DISTINCT ville FROM annonces_sarouty ORDER BY ville")
    else:
        cursor.execute("""
            SELECT DISTINCT ville FROM (
                SELECT localisation AS ville FROM projets
                UNION
                SELECT ville FROM annonces_sarouty
            ) ORDER BY ville
        """)
    villes = [row[0] for row in cursor.fetchall() if row[0] is not None and row[0] != '']
    conn.close()
    return villes

def get_villes_by_source(source):
    """
    Retourne la liste des villes disponibles pour une source donnée.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if source == 'alomrane':
        cursor.execute("SELECT DISTINCT localisation FROM projets ORDER BY localisation")
    elif source == 'sarouty':
        cursor.execute("SELECT DISTINCT ville FROM annonces_sarouty ORDER BY ville")
    else:
        cursor.execute("""
            SELECT DISTINCT ville FROM (
                SELECT localisation AS ville FROM projets
                UNION
                SELECT ville FROM annonces_sarouty
            ) ORDER BY ville
        """)
    villes = [row[0] for row in cursor.fetchall() if row[0] is not None and row[0] != '']
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
                (url, region, type_bien, titre, localisation, titre_foncier, description, badge)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                projet.get('lien', ''),
                projet.get('region', ''),
                projet.get('type_bien', ''),
                projet.get('titre', ''),
                projet.get('localisation', ''),
                projet.get('titre_foncier', ''),
                projet.get('description', ''),
                projet.get('badge', '')
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
                            INSERT INTO produits (lot_id, no_produit, surface, prix, etage, designation, url)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            lot_id,
                            ligne.get('no_produit', ''),
                            ligne.get('surface', ''),
                            ligne.get('prix', ''),
                            ligne.get('etage', ''),
                            ligne.get('designation', ''),
                            ligne.get('url', '')
                        ))
        conn.commit()
        print(f"💾 {inserted} projets Al Omrane insérés.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Al Omrane : {e}")
    finally:
        conn.close()
    return inserted

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
            lot_dict['lignes'] = [dict(prod) for prod in cursor.fetchall()]
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
        query += " AND ville = ?"
        params.append(filters['ville'])
    if 'type_bien' in filters and filters['type_bien']:
        query += " AND type_bien = ?"
        params.append(filters['type_bien'])
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
    
    cursor.execute("SELECT DISTINCT localisation FROM projets")
    stats['villes'] = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT type_bien FROM projets")
    stats['types_biens'] = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT badge FROM projets")
    stats['badges'] = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT etage FROM produits WHERE etage IS NOT NULL AND etage != ''")
    stats['etages'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT ville FROM annonces_sarouty")
    stats['villes_sarouty'] = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT type_bien FROM annonces_sarouty")
    stats['types_sarouty'] = [row[0] for row in cursor.fetchall()]
    conn.close()
    return stats

def get_prix_m2_stats(ville=None, type_bien=None, etage=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            p.localisation,
            p.type_bien,
            pr.surface,
            pr.prix,
            pr.etage,
            CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) as surface_m2,
            CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) as prix_brut
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE 1=1
    """
    params = []
    if ville:
        query += " AND p.localisation = ?"
        params.append(ville)
    if type_bien:
        query += " AND p.type_bien = ?"
        params.append(type_bien)
    if etage:
        query += " AND pr.etage = ?"
        params.append(etage)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    prix_m2_list = []
    for row in rows:
        try:
            surface = float(row[5])
            prix = float(row[6])
            if surface > 0:
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