# scripts/backfill_snapshots.py
"""
Amorce l'historique (listing_snapshots) à partir des données déjà présentes en base,
en les datant d'aujourd'hui. À exécuter une seule fois après la mise en place du suivi
d'évolution, pour ne pas partir d'un historique vide.

Usage : python scripts/backfill_snapshots.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import (
    init_db,
    get_connection,
    start_scrape_run,
    finish_scrape_run,
    _insert_snapshots,
    _clean_numeric,
    _parse_prix_m2,
)


def backfill_alomrane():
    run_id = start_scrape_run('alomrane')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.url, p.localisation, p.type_bien, pr.no_produit, pr.surface, pr.prix
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
    """)
    rows = []
    for url, ville, type_bien, no_produit, surface, prix in cursor.fetchall():
        rows.append({
            'source': 'alomrane',
            'listing_key': f"{url}::{no_produit}",
            'type_bien': type_bien,
            'ville': ville,
            'quartier': None,
            'surface': _clean_numeric(surface, 'm²'),
            'prix': _clean_numeric(prix, 'DH'),
            'prix_m2': _parse_prix_m2(prix, surface),
        })
    _insert_snapshots(cursor, run_id, rows)
    conn.commit()
    conn.close()
    finish_scrape_run(run_id, 'succes', len(rows))
    print(f"✅ Backfill Al Omrane : {len(rows)} snapshots créés.")


def backfill_sarouty():
    run_id = start_scrape_run('sarouty')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT property_id, type_bien, ville, quartier, superficie, prix FROM annonces_sarouty")
    rows = []
    for property_id, type_bien, ville, quartier, superficie, prix in cursor.fetchall():
        prix = prix or 0
        superficie = superficie or 0
        rows.append({
            'source': 'sarouty',
            'listing_key': str(property_id),
            'type_bien': type_bien,
            'ville': ville,
            'quartier': quartier,
            'surface': superficie or None,
            'prix': prix or None,
            'prix_m2': round(prix / superficie, 2) if superficie else None,
        })
    _insert_snapshots(cursor, run_id, rows)
    conn.commit()
    conn.close()
    finish_scrape_run(run_id, 'succes', len(rows))
    print(f"✅ Backfill Sarouty : {len(rows)} snapshots créés.")


def backfill_mubawab():
    run_id = start_scrape_run('mubawab')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT url_annonce, type_bien, ville, localisation, superficie, prix FROM annonces_mubawab")
    rows = []
    for url_annonce, type_bien, ville, localisation, superficie, prix in cursor.fetchall():
        prix = prix or 0
        superficie = superficie or 0
        rows.append({
            'source': 'mubawab',
            'listing_key': url_annonce,
            'type_bien': type_bien,
            'ville': ville,
            'quartier': localisation,
            'surface': superficie or None,
            'prix': prix or None,
            'prix_m2': round(prix / superficie, 2) if superficie else None,
        })
    _insert_snapshots(cursor, run_id, rows)
    conn.commit()
    conn.close()
    finish_scrape_run(run_id, 'succes', len(rows))
    print(f"✅ Backfill Mubawab : {len(rows)} snapshots créés.")


if __name__ == '__main__':
    init_db()
    backfill_alomrane()
    backfill_sarouty()
    backfill_mubawab()
    print("🎉 Backfill terminé. L'historique est amorcé, les prochains scrapes ajouteront de nouveaux points.")
