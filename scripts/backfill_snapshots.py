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

from sqlalchemy import select

from database.db_manager import (
    _clean_numeric,
    _insert_snapshots,
    _parse_prix_m2,
    finish_scrape_run,
    init_db,
    start_scrape_run,
)
from database.models import AnnonceMubawab, AnnonceSarouty, Lot, Produit, Projet
from database.session import session_scope


def backfill_alomrane():
    run_id = start_scrape_run('alomrane')
    with session_scope() as session:
        rows_data = session.execute(
            select(Projet.url, Projet.localisation, Projet.type_bien,
                   Produit.no_produit, Produit.surface, Produit.prix)
            .select_from(Produit)
            .join(Lot, Lot.id == Produit.lot_id)
            .join(Projet, Projet.id == Lot.projet_id)
        ).all()
        rows = []
        for url, ville, type_bien, no_produit, surface, prix in rows_data:
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
        _insert_snapshots(session, run_id, rows)
    finish_scrape_run(run_id, 'succes', len(rows))
    print(f"✅ Backfill Al Omrane : {len(rows)} snapshots créés.")


def backfill_sarouty():
    run_id = start_scrape_run('sarouty')
    with session_scope() as session:
        rows_data = session.execute(
            select(AnnonceSarouty.property_id, AnnonceSarouty.type_bien, AnnonceSarouty.ville,
                   AnnonceSarouty.quartier, AnnonceSarouty.superficie, AnnonceSarouty.prix)
        ).all()
        rows = []
        for property_id, type_bien, ville, quartier, superficie, prix in rows_data:
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
        _insert_snapshots(session, run_id, rows)
    finish_scrape_run(run_id, 'succes', len(rows))
    print(f"✅ Backfill Sarouty : {len(rows)} snapshots créés.")


def backfill_mubawab():
    run_id = start_scrape_run('mubawab')
    with session_scope() as session:
        rows_data = session.execute(
            select(AnnonceMubawab.url_annonce, AnnonceMubawab.type_bien, AnnonceMubawab.ville,
                   AnnonceMubawab.localisation, AnnonceMubawab.superficie, AnnonceMubawab.prix)
        ).all()
        rows = []
        for url_annonce, type_bien, ville, localisation, superficie, prix in rows_data:
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
        _insert_snapshots(session, run_id, rows)
    finish_scrape_run(run_id, 'succes', len(rows))
    print(f"✅ Backfill Mubawab : {len(rows)} snapshots créés.")


if __name__ == '__main__':
    init_db()
    backfill_alomrane()
    backfill_sarouty()
    backfill_mubawab()
    print("🎉 Backfill terminé. L'historique est amorcé, les prochains scrapes ajouteront de nouveaux points.")
