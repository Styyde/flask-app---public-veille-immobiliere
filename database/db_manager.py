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

    # ---- Table Favoris (avec migration) ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favoris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            annonce_id TEXT NOT NULL,
            url TEXT,
            titre TEXT,
            localisation TEXT,
            type_bien TEXT,
            surface TEXT,
            prix TEXT,
            prix_m2 REAL,
            date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, annonce_id)
        )
    """)
    
    # Migration : ajouter les colonnes manquantes
    cursor.execute("PRAGMA table_info(favoris)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    # Migration legacy : ancienne colonne id_annonce → annonce_id
    if 'id_annonce' in existing_columns:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favoris_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                annonce_id TEXT NOT NULL,
                url TEXT,
                titre TEXT,
                localisation TEXT,
                type_bien TEXT,
                surface TEXT,
                prix TEXT,
                prix_m2 REAL,
                date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, annonce_id)
            )
        """)
        cursor.execute("""
            INSERT INTO favoris_new
                (source, annonce_id, url, titre, localisation, type_bien, surface, prix, prix_m2, date_ajout)
            SELECT
                source,
                COALESCE(NULLIF(annonce_id, ''), id_annonce),
                url, titre, localisation, type_bien, surface, prix, prix_m2, date_ajout
            FROM favoris
            WHERE COALESCE(NULLIF(annonce_id, ''), id_annonce) IS NOT NULL
              AND COALESCE(NULLIF(annonce_id, ''), id_annonce) != ''
        """)
        cursor.execute("DROP TABLE favoris")
        cursor.execute("ALTER TABLE favoris_new RENAME TO favoris")
        existing_columns = [
            col[1] for col in cursor.execute("PRAGMA table_info(favoris)").fetchall()
        ]
    
    columns_to_add = {
        'annonce_id': 'TEXT NOT NULL DEFAULT ""',
        'url': 'TEXT',
        'titre': 'TEXT',
        'localisation': 'TEXT',
        'type_bien': 'TEXT',
        'surface': 'TEXT',
        'prix': 'TEXT',
        'prix_m2': 'REAL',
        'date_ajout': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
    }
    
    for col, col_type in columns_to_add.items():
        if col not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE favoris ADD COLUMN {col} {col_type}")
                print(f"✅ Migration : colonne '{col}' ajoutée à la table favoris")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Impossible d'ajouter la colonne {col} : {e}")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_favoris_source ON favoris (source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_favoris_date ON favoris (date_ajout)")
    
    # ---- Table Taches (Background Tasks) ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS taches (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            result TEXT,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_fin DATETIME
        )
    """)

    # ---- Suivi historique (évolution dans le temps) ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME,
            statut TEXT DEFAULT 'en_cours',
            nb_annonces INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listing_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scrape_run_id INTEGER,
            source TEXT NOT NULL,
            listing_key TEXT NOT NULL,
            type_bien TEXT,
            ville TEXT,
            quartier TEXT,
            surface REAL,
            prix REAL,
            prix_m2 REAL,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scrape_run_id) REFERENCES scrape_runs (id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_date ON listing_snapshots (scraped_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_group ON listing_snapshots (type_bien, ville)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_key ON listing_snapshots (source, listing_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_run ON listing_snapshots (scrape_run_id)")

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

def save_projets(projets_list, scrape_run_id=None):
    if not projets_list:
        return 0
    own_run = scrape_run_id is None
    if own_run:
        scrape_run_id = start_scrape_run('alomrane')
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    snapshot_rows = []
    try:
        cursor.execute("BEGIN TRANSACTION")
        for projet in projets_list:
            url = projet.get('lien', '')
            cursor.execute("SELECT id FROM projets WHERE url = ?", (url,))
            existing = cursor.fetchone()

            if existing:
                projet_id = existing[0]
                cursor.execute("""
                    UPDATE projets SET region = ?, type_bien = ?, titre = ?, localisation = ?,
                        titre_foncier = ?, description = ?
                    WHERE id = ?
                """, (
                    projet.get('region', ''),
                    projet.get('type_bien', ''),
                    projet.get('titre', ''),
                    projet.get('localisation', ''),
                    projet.get('titre_foncier', ''),
                    projet.get('description', ''),
                    projet_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO projets
                    (url, region, type_bien, titre, localisation, titre_foncier, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    url,
                    projet.get('region', ''),
                    projet.get('type_bien', ''),
                    projet.get('titre', ''),
                    projet.get('localisation', ''),
                    projet.get('titre_foncier', ''),
                    projet.get('description', '')
                ))
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

            # Snapshot : capture l'état courant des produits de ce projet pour cette campagne
            cursor.execute("""
                SELECT pr.no_produit, pr.surface, pr.prix
                FROM produits pr JOIN lots l ON l.id = pr.lot_id
                WHERE l.projet_id = ?
            """, (projet_id,))
            ville = projet.get('localisation', '')
            type_bien = projet.get('type_bien', '')
            for no_produit, surface, prix in cursor.fetchall():
                snapshot_rows.append({
                    'source': 'alomrane',
                    'listing_key': f"{url}::{no_produit}",
                    'type_bien': type_bien,
                    'ville': ville,
                    'quartier': None,
                    'surface': _clean_numeric(surface, 'm²'),
                    'prix': _clean_numeric(prix, 'DH'),
                    'prix_m2': _parse_prix_m2(prix, surface),
                })

        _insert_snapshots(cursor, scrape_run_id, snapshot_rows)
        conn.commit()
        print(f"💾 {inserted} projets Al Omrane insérés.")
        if own_run:
            finish_scrape_run(scrape_run_id, 'succes', inserted)
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Al Omrane : {e}")
        if own_run:
            finish_scrape_run(scrape_run_id, 'erreur', inserted)
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

def _clean_numeric(val, unit=None):
    """Convertit une valeur texte (ex: '720 000 DH', '120 m²') en float, ou None."""
    if val is None:
        return None
    try:
        s = str(val)
        if unit:
            s = s.replace(unit, '')
        s = s.replace('\xa0', '').replace(' ', '').strip()
        return float(s) if s else None
    except (TypeError, ValueError):
        return None

# ==================== HISTORIQUE (scrape_runs / listing_snapshots) ====================

def start_scrape_run(source):
    """Ouvre une nouvelle campagne de scraping et retourne son id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scrape_runs (source, statut) VALUES (?, 'en_cours')", (source,))
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def finish_scrape_run(run_id, statut='succes', nb_annonces=0):
    """Clôture une campagne de scraping avec son statut final."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scrape_runs SET statut = ?, nb_annonces = ?, finished_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (statut, nb_annonces, run_id))
    conn.commit()
    conn.close()

def _insert_snapshots(cursor, scrape_run_id, rows):
    """Insère un lot de lignes dans listing_snapshots (dans la transaction/cursor en cours)."""
    if not rows:
        return
    cursor.executemany("""
        INSERT INTO listing_snapshots
        (scrape_run_id, source, listing_key, type_bien, ville, quartier, surface, prix, prix_m2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            scrape_run_id, r['source'], r['listing_key'], r.get('type_bien'),
            r.get('ville'), r.get('quartier'), r.get('surface'), r.get('prix'), r.get('prix_m2'),
        )
        for r in rows
    ])

def get_snapshots(date_from=None, date_to=None, villes=None):
    """Retourne les lignes de listing_snapshots, optionnellement filtrées par période/villes."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = """
        SELECT ls.scraped_at, ls.scrape_run_id, ls.source, ls.listing_key, ls.type_bien,
               ls.ville, ls.quartier, ls.surface, ls.prix, ls.prix_m2, sr.started_at AS run_started_at
        FROM listing_snapshots ls
        LEFT JOIN scrape_runs sr ON sr.id = ls.scrape_run_id
        WHERE 1=1
    """
    params = []
    if villes:
        placeholders = ','.join(['?'] * len(villes))
        query += f" AND ls.ville IN ({placeholders})"
        params.extend(villes)
    if date_from:
        query += " AND date(ls.scraped_at) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(ls.scraped_at) <= date(?)"
        params.append(date_to)
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

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
def save_annonces_sarouty(annonces_list, scrape_run_id=None):
    if not annonces_list:
        return 0
    own_run = scrape_run_id is None
    if own_run:
        scrape_run_id = start_scrape_run('sarouty')
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    snapshot_rows = []
    try:
        cursor.execute("BEGIN TRANSACTION")
        for a in annonces_list:
            property_id = a.get('property_id')
            if property_id is None:
                continue

            cursor.execute("SELECT 1 FROM annonces_sarouty WHERE property_id = ?", (property_id,))
            is_new = cursor.fetchone() is None

            cursor.execute("""
                INSERT INTO annonces_sarouty
                (property_id, url_annonce, titre, description, prix, superficie, chambres, salles_de_bain, type_bien, quartier, ville)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(property_id) DO UPDATE SET
                    url_annonce = excluded.url_annonce,
                    titre = excluded.titre,
                    description = excluded.description,
                    prix = excluded.prix,
                    superficie = excluded.superficie,
                    chambres = excluded.chambres,
                    salles_de_bain = excluded.salles_de_bain,
                    type_bien = excluded.type_bien,
                    quartier = excluded.quartier,
                    ville = excluded.ville
            """, (
                property_id,
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
            if is_new:
                inserted += 1

            prix = a.get('prix') or 0
            superficie = a.get('superficie') or 0
            snapshot_rows.append({
                'source': 'sarouty',
                'listing_key': str(property_id),
                'type_bien': a.get('type_bien'),
                'ville': a.get('ville'),
                'quartier': a.get('quartier'),
                'surface': superficie or None,
                'prix': prix or None,
                'prix_m2': round(prix / superficie, 2) if superficie else None,
            })

        _insert_snapshots(cursor, scrape_run_id, snapshot_rows)
        conn.commit()
        print(f"💾 {inserted} annonces Sarouty insérées.")
        if own_run:
            finish_scrape_run(scrape_run_id, 'succes', inserted)
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Sarouty : {e}")
        if own_run:
            finish_scrape_run(scrape_run_id, 'erreur', inserted)
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
def save_annonces_mubawab(annonces_list, scrape_run_id=None):
    if not annonces_list:
        return 0
    own_run = scrape_run_id is None
    if own_run:
        scrape_run_id = start_scrape_run('mubawab')
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    snapshot_rows = []
    try:
        cursor.execute("BEGIN TRANSACTION")
        for a in annonces_list:
            url_annonce = a.get('url_annonce') or a.get('url')
            if not url_annonce:
                continue

            cursor.execute("SELECT 1 FROM annonces_mubawab WHERE url_annonce = ?", (url_annonce,))
            is_new = cursor.fetchone() is None

            prix = a.get('prix', 0)
            superficie = a.get('superficie') if a.get('superficie') is not None else a.get('surface', 0)
            type_bien = a.get('type_bien')
            localisation = a.get('localisation') or a.get('location')
            ville = a.get('ville')

            cursor.execute("""
                INSERT INTO annonces_mubawab
                (url_annonce, titre, description, prix, superficie, type_bien, localisation, ville, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url_annonce) DO UPDATE SET
                    titre = excluded.titre,
                    description = excluded.description,
                    prix = excluded.prix,
                    superficie = excluded.superficie,
                    type_bien = excluded.type_bien,
                    localisation = excluded.localisation,
                    ville = excluded.ville,
                    region = excluded.region
            """, (
                url_annonce,
                a.get('titre') or a.get('title'),
                a.get('description'),
                prix,
                superficie,
                type_bien,
                localisation,
                ville,
                a.get('region'),
            ))
            if is_new:
                inserted += 1

            prix = prix or 0
            superficie = superficie or 0
            snapshot_rows.append({
                'source': 'mubawab',
                'listing_key': url_annonce,
                'type_bien': type_bien,
                'ville': ville,
                'quartier': localisation,
                'surface': superficie or None,
                'prix': prix or None,
                'prix_m2': round(prix / superficie, 2) if superficie else None,
            })

        _insert_snapshots(cursor, scrape_run_id, snapshot_rows)
        conn.commit()
        print(f"💾 {inserted} annonces Mubawab insérées.")
        if own_run:
            finish_scrape_run(scrape_run_id, 'succes', inserted)
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur insertion Mubawab : {e}")
        if own_run:
            finish_scrape_run(scrape_run_id, 'erreur', inserted)
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

    # --- FILTRE REGION ---
    if 'region' in filters and filters['region']:
        query += " AND region = ?"
        params.append(filters['region'])
    # --------------------

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
    
    # Favoris
    cursor.execute("SELECT COUNT(*) FROM favoris")
    stats['nb_favoris'] = cursor.fetchone()[0]
    
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

# ==================== FAVORIS ====================

def ajouter_favori(source, annonce_id, url, titre, localisation, type_bien, surface, prix, prix_m2):
    """Ajoute une annonce aux favoris."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO favoris 
            (source, annonce_id, url, titre, localisation, type_bien, surface, prix, prix_m2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (source, annonce_id, url, titre, localisation, type_bien, surface, prix, prix_m2))
        conn.commit()
        inserted = cursor.rowcount > 0
        conn.close()
        return inserted
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def supprimer_favori(source, annonce_id):
    """Supprime une annonce des favoris."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM favoris WHERE source = ? AND annonce_id = ?", (source, annonce_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def get_favoris():
    """Retourne la liste de tous les favoris, triés par date d'ajout décroissante."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM favoris ORDER BY date_ajout DESC")
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result


def get_favoris_set():
    """Retourne un dict {source: [annonce_id, ...]} pour le frontend."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source, annonce_id FROM favoris")
    result = {}
    for source, annonce_id in cursor.fetchall():
        key = str(source)
        if key not in result:
            result[key] = []
        result[key].append(str(annonce_id))
    conn.close()
    return result

def est_favori(source, annonce_id):
    """Vérifie si une annonce est déjà dans les favoris."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM favoris WHERE source = ? AND annonce_id = ?", (source, annonce_id))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# ==================== GESTION DES TACHES ====================

def create_task(task_id, source, initial_message="En attente..."):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO taches (id, source, status, message) 
        VALUES (?, ?, 'en_cours', ?)
    """, (task_id, source, initial_message))
    conn.commit()
    conn.close()

def update_task_status(task_id, status, message=None, result=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = ["status = ?"]
    params = [status]
    
    if message is not None:
        updates.append("message = ?")
        params.append(message)
    if result is not None:
        import json
        updates.append("result = ?")
        params.append(json.dumps(result))
        
    if status in ['termine', 'erreur']:
        updates.append("date_fin = CURRENT_TIMESTAMP")
        
    query = f"UPDATE taches SET {', '.join(updates)} WHERE id = ?"
    params.append(task_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def get_task_status(task_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM taches WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        import json
        if d.get('result'):
            try:
                d['result'] = json.loads(d['result'])
            except:
                pass
        return d
    return None