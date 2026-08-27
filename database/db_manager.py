# database/db_manager.py
import logging
import os

from sqlalchemy import Numeric, cast, delete, distinct, false, func, or_, select, union, update
from sqlalchemy.orm import selectinload

from database.compat import upsert_ignore, upsert_update
from database.expressions import clean_numeric_col, prix_m2_expr
from database.models import (
    AnnonceMubawab,
    AnnonceSarouty,
    Favori,
    ListingSnapshot,
    Lot,
    Produit,
    Projet,
    ScrapeRun,
    Tache,
)
from database.session import session_scope

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def init_db():
    """Cree/met a jour le schema en appliquant les migrations Alembic
    (voir alembic/versions/) jusqu'a la revision la plus recente."""
    from alembic.config import Config

    from alembic import command

    cfg = Config(os.path.join(_REPO_ROOT, 'alembic.ini'))
    cfg.set_main_option('script_location', os.path.join(_REPO_ROOT, 'alembic'))
    command.upgrade(cfg, 'head')
    logger.info("Base de données initialisée avec succès.")


def _model_to_dict(obj):
    """Convertit une instance ORM en dict plat, meme forme que dict(sqlite3.Row)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ==================== AL OMRANE ====================
def get_existing_urls():
    with session_scope() as session:
        return {row[0] for row in session.execute(select(Projet.url))}

# ==================== LISTES DYNAMIQUES ====================

def get_types_by_source(source):
    with session_scope() as session:
        if source == 'alomrane':
            stmt = select(distinct(Projet.type_bien)).order_by(Projet.type_bien)
        elif source == 'sarouty':
            stmt = select(distinct(AnnonceSarouty.type_bien)).order_by(AnnonceSarouty.type_bien)
        elif source == 'mubawab':
            stmt = select(distinct(AnnonceMubawab.type_bien)).order_by(AnnonceMubawab.type_bien)
        else:
            sub = union(
                select(Projet.type_bien),
                select(AnnonceSarouty.type_bien),
                select(AnnonceMubawab.type_bien),
            ).subquery()
            stmt = select(sub.c.type_bien).order_by(sub.c.type_bien)
        return [row[0] for row in session.execute(stmt) if row[0]]

def get_villes_by_source(source):
    # La liste proposee au choix ne s'appuie que sur la colonne 'ville' dediee
    # (jamais 'quartier'/'localisation', qui sont des sous-decoupages et
    # pollueraient la liste). La recherche elle-meme reste elargie et matche
    # aussi sur le quartier/la localisation (voir get_annonces_*_filtered).
    with session_scope() as session:
        if source == 'alomrane':
            stmt = select(distinct(Projet.localisation)).order_by(Projet.localisation)
        elif source == 'sarouty':
            stmt = (
                select(distinct(AnnonceSarouty.ville))
                .where(AnnonceSarouty.ville.isnot(None), AnnonceSarouty.ville != '')
                .order_by(AnnonceSarouty.ville)
            )
        elif source == 'mubawab':
            stmt = (
                select(distinct(AnnonceMubawab.ville))
                .where(AnnonceMubawab.ville.isnot(None), AnnonceMubawab.ville != '')
                .order_by(AnnonceMubawab.ville)
            )
        else:
            sub = union(
                select(Projet.localisation.label('ville')),
                select(AnnonceSarouty.ville.label('ville')),
                select(AnnonceMubawab.ville.label('ville')),
            ).subquery()
            stmt = (
                select(sub.c.ville)
                .where(sub.c.ville.isnot(None), sub.c.ville != '')
                .order_by(sub.c.ville)
            )
        return [row[0] for row in session.execute(stmt) if row[0]]

def save_projets(projets_list, scrape_run_id=None):
    if not projets_list:
        return 0
    own_run = scrape_run_id is None
    if own_run:
        scrape_run_id = start_scrape_run('alomrane')
    inserted = 0
    snapshot_rows = []
    try:
        with session_scope() as session:
            for projet in projets_list:
                url = projet.get('lien', '')
                existing = session.execute(
                    select(Projet).where(Projet.url == url)
                ).scalar_one_or_none()

                if existing:
                    existing.region = projet.get('region', '')
                    existing.type_bien = projet.get('type_bien', '')
                    existing.titre = projet.get('titre', '')
                    existing.localisation = projet.get('localisation', '')
                    existing.titre_foncier = projet.get('titre_foncier', '')
                    existing.description = projet.get('description', '')
                    projet_obj = existing
                else:
                    projet_obj = Projet(
                        url=url,
                        region=projet.get('region', ''),
                        type_bien=projet.get('type_bien', ''),
                        titre=projet.get('titre', ''),
                        localisation=projet.get('localisation', ''),
                        titre_foncier=projet.get('titre_foncier', ''),
                        description=projet.get('description', ''),
                    )
                    session.add(projet_obj)
                    inserted += 1
                    for lot in projet.get('lots', []):
                        lot_obj = Lot(
                            lot_titre=lot.get('titre', ''),
                            nb_unites=lot.get('nb_unites', ''),
                            prix_min=lot.get('prix_min', ''),
                            prix_max=lot.get('prix_max', ''),
                        )
                        projet_obj.lots.append(lot_obj)
                        for ligne in lot.get('lignes', []):
                            lot_obj.produits.append(Produit(
                                no_produit=ligne.get('no_produit', ''),
                                surface=ligne.get('surface', ''),
                                prix=ligne.get('prix', ''),
                            ))

                session.flush()

                # Snapshot : capture l'état courant des produits de ce projet pour cette campagne
                rows = session.execute(
                    select(Produit.no_produit, Produit.surface, Produit.prix)
                    .join(Lot, Lot.id == Produit.lot_id)
                    .where(Lot.projet_id == projet_obj.id)
                ).all()
                ville = projet.get('localisation', '')
                type_bien = projet.get('type_bien', '')
                for no_produit, surface, prix in rows:
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

            _insert_snapshots(session, scrape_run_id, snapshot_rows)
        logger.info("%d projets Al Omrane insérés.", inserted)
        if own_run:
            finish_scrape_run(scrape_run_id, 'succes', inserted)
    except Exception:
        logger.exception("Erreur insertion Al Omrane")
        if own_run:
            finish_scrape_run(scrape_run_id, 'erreur', inserted)
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
    with session_scope() as session:
        run = ScrapeRun(source=source, statut='en_cours')
        session.add(run)
        session.flush()
        return run.id

def finish_scrape_run(run_id, statut='succes', nb_annonces=0):
    """Clôture une campagne de scraping avec son statut final."""
    with session_scope() as session:
        session.execute(
            update(ScrapeRun)
            .where(ScrapeRun.id == run_id)
            .values(statut=statut, nb_annonces=nb_annonces, finished_at=func.now())
        )

def _insert_snapshots(session, scrape_run_id, rows):
    """Insère un lot de lignes dans listing_snapshots (dans la session/transaction en cours)."""
    if not rows:
        return
    session.execute(
        ListingSnapshot.__table__.insert(),
        [
            {
                'scrape_run_id': scrape_run_id,
                'source': r['source'],
                'listing_key': r['listing_key'],
                'type_bien': r.get('type_bien'),
                'ville': r.get('ville'),
                'quartier': r.get('quartier'),
                'surface': r.get('surface'),
                'prix': r.get('prix'),
                'prix_m2': r.get('prix_m2'),
            }
            for r in rows
        ],
    )

def get_snapshots(date_from=None, date_to=None, villes=None):
    """Retourne les lignes de listing_snapshots, optionnellement filtrées par période/villes."""
    with session_scope() as session:
        stmt = (
            select(
                ListingSnapshot.scraped_at,
                ListingSnapshot.scrape_run_id,
                ListingSnapshot.source,
                ListingSnapshot.listing_key,
                ListingSnapshot.type_bien,
                ListingSnapshot.ville,
                ListingSnapshot.quartier,
                ListingSnapshot.surface,
                ListingSnapshot.prix,
                ListingSnapshot.prix_m2,
                ScrapeRun.started_at.label('run_started_at'),
            )
            .select_from(ListingSnapshot)
            .outerjoin(ScrapeRun, ScrapeRun.id == ListingSnapshot.scrape_run_id)
        )
        if villes:
            stmt = stmt.where(ListingSnapshot.ville.in_(villes))
        if date_from:
            stmt = stmt.where(func.date(ListingSnapshot.scraped_at) >= func.date(date_from))
        if date_to:
            stmt = stmt.where(func.date(ListingSnapshot.scraped_at) <= func.date(date_to))
        return [dict(row._mapping) for row in session.execute(stmt)]

def _enrich_produit(prod):
    row = dict(prod)
    row['prix_m2'] = _parse_prix_m2(row.get('prix'), row.get('surface'))
    return row

def _projet_to_dict(projet_obj):
    d = _model_to_dict(projet_obj)
    d['lots'] = []
    for lot in projet_obj.lots:
        lot_dict = _model_to_dict(lot)
        lot_dict['lignes'] = [_enrich_produit(_model_to_dict(p)) for p in lot.produits]
        d['lots'].append(lot_dict)
    return d

def get_projet_detail(projet_id):
    with session_scope() as session:
        projet_obj = session.execute(
            select(Projet)
            .options(selectinload(Projet.lots).selectinload(Lot.produits))
            .where(Projet.id == projet_id)
        ).unique().scalar_one_or_none()
        if not projet_obj:
            return None
        return _projet_to_dict(projet_obj)

def get_projets_resume(**filters):
    with session_scope() as session:
        pm2 = prix_m2_expr(Produit.prix, Produit.surface)
        prix_clean = clean_numeric_col(Produit.prix, 'DH')
        surface_clean = clean_numeric_col(Produit.surface, 'm²')
        prix_m2_min_col = func.min(pm2).label('prix_m2_min')
        prix_m2_max_col = func.max(pm2).label('prix_m2_max')

        stmt = (
            select(
                Projet.id,
                Projet.titre,
                Projet.localisation,
                Projet.type_bien,
                Projet.url,
                Projet.region,
                func.count(distinct(Lot.id)).label('nb_lots'),
                func.count(Produit.id).label('nb_produits'),
                prix_m2_min_col,
                prix_m2_max_col,
            )
            .select_from(Projet)
            .join(Lot, Lot.projet_id == Projet.id)
            .join(Produit, Produit.lot_id == Lot.id)
            .where(prix_clean > 0)
        )

        if filters.get('ville'):
            stmt = stmt.where(Projet.localisation == filters['ville'])
        if filters.get('type_brut_list'):
            stmt = stmt.where(Projet.type_bien.in_(filters['type_brut_list']))
        elif filters.get('type_bien'):
            from services.type_mapping import get_brut_types_for_normalized
            brut_list = get_brut_types_for_normalized(filters['type_bien'])
            stmt = stmt.where(Projet.type_bien.in_(brut_list)) if brut_list else stmt.where(false())
        if filters.get('budget_min') is not None:
            stmt = stmt.where(prix_clean >= filters['budget_min'])
        if filters.get('budget_max') is not None:
            stmt = stmt.where(prix_clean <= filters['budget_max'])
        if filters.get('surface_min') is not None:
            stmt = stmt.where(surface_clean >= filters['surface_min'])
        if filters.get('surface_max') is not None:
            stmt = stmt.where(surface_clean <= filters['surface_max'])
        if filters.get('prix_m2_min') is not None:
            stmt = stmt.where(pm2 >= filters['prix_m2_min'])
        if filters.get('prix_m2_max') is not None:
            stmt = stmt.where(pm2 <= filters['prix_m2_max'])

        stmt = stmt.group_by(Projet.id).order_by(prix_m2_min_col.asc())
        if filters.get('limit'):
            stmt = stmt.limit(filters['limit'])

        return [dict(row._mapping) for row in session.execute(stmt)]

def get_all_projets(limit=100):
    with session_scope() as session:
        projets_obj = session.execute(
            select(Projet)
            .options(selectinload(Projet.lots).selectinload(Lot.produits))
            .order_by(Projet.date_extraction.desc())
            .limit(limit)
        ).unique().scalars().all()
        return [_projet_to_dict(p) for p in projets_obj]

# ==================== SAROUTY ====================
def save_annonces_sarouty(annonces_list, scrape_run_id=None):
    if not annonces_list:
        return 0
    own_run = scrape_run_id is None
    if own_run:
        scrape_run_id = start_scrape_run('sarouty')
    inserted = 0
    snapshot_rows = []
    try:
        with session_scope() as session:
            for a in annonces_list:
                property_id = a.get('property_id')
                if property_id is None:
                    continue

                is_new = session.execute(
                    select(AnnonceSarouty.id).where(AnnonceSarouty.property_id == property_id)
                ).first() is None

                values = dict(
                    property_id=property_id,
                    url_annonce=a.get('url_annonce'),
                    titre=a.get('titre'),
                    description=a.get('description'),
                    prix=a.get('prix', 0),
                    superficie=a.get('superficie', 0),
                    chambres=a.get('chambres'),
                    salles_de_bain=a.get('salles_de_bain'),
                    type_bien=a.get('type_bien'),
                    quartier=a.get('quartier'),
                    ville=a.get('ville'),
                )
                stmt = upsert_update(AnnonceSarouty, values, index_elements=['property_id'])
                session.execute(stmt)
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

            _insert_snapshots(session, scrape_run_id, snapshot_rows)
        logger.info("%d annonces Sarouty insérées.", inserted)
        if own_run:
            finish_scrape_run(scrape_run_id, 'succes', inserted)
    except Exception:
        logger.exception("Erreur insertion Sarouty")
        if own_run:
            finish_scrape_run(scrape_run_id, 'erreur', inserted)
    return inserted

def get_annonces_sarouty_filtered(**filters):
    with session_scope() as session:
        pm2 = func.round(cast(AnnonceSarouty.prix, Numeric) / func.nullif(AnnonceSarouty.superficie, 0), 2).label('prix_m2')
        stmt = select(AnnonceSarouty, pm2)

        if filters.get('ville'):
            stmt = stmt.where(or_(
                AnnonceSarouty.ville == filters['ville'],
                AnnonceSarouty.quartier == filters['ville'],
            ))

        if filters.get('type_bien'):
            from services.type_mapping import get_brut_types_for_normalized
            brut_list = get_brut_types_for_normalized(filters['type_bien'])
            stmt = stmt.where(AnnonceSarouty.type_bien.in_(brut_list)) if brut_list else stmt.where(false())
        elif filters.get('type_brut_list'):
            stmt = stmt.where(AnnonceSarouty.type_bien.in_(filters['type_brut_list']))

        if filters.get('budget_min'):
            stmt = stmt.where(AnnonceSarouty.prix >= filters['budget_min'])
        if filters.get('budget_max'):
            stmt = stmt.where(AnnonceSarouty.prix <= filters['budget_max'])
        if filters.get('superficie_min'):
            stmt = stmt.where(AnnonceSarouty.superficie >= filters['superficie_min'])
        if filters.get('superficie_max'):
            stmt = stmt.where(AnnonceSarouty.superficie <= filters['superficie_max'])
        if filters.get('prix_m2_min'):
            stmt = stmt.where(pm2 >= filters['prix_m2_min'])
        if filters.get('prix_m2_max'):
            stmt = stmt.where(pm2 <= filters['prix_m2_max'])

        stmt = stmt.order_by(pm2.asc())
        result = []
        for row in session.execute(stmt):
            d = _model_to_dict(row[0])
            d['prix_m2'] = row[1]
            result.append(d)
        return result

# ==================== MUBAWAB ====================
def save_annonces_mubawab(annonces_list, scrape_run_id=None):
    if not annonces_list:
        return 0
    own_run = scrape_run_id is None
    if own_run:
        scrape_run_id = start_scrape_run('mubawab')
    inserted = 0
    snapshot_rows = []
    try:
        with session_scope() as session:
            for a in annonces_list:
                url_annonce = a.get('url_annonce') or a.get('url')
                if not url_annonce:
                    continue

                is_new = session.execute(
                    select(AnnonceMubawab.id).where(AnnonceMubawab.url_annonce == url_annonce)
                ).first() is None

                prix = a.get('prix', 0)
                superficie = a.get('superficie') if a.get('superficie') is not None else a.get('surface', 0)
                type_bien = a.get('type_bien')
                localisation = a.get('localisation') or a.get('location')
                ville = a.get('ville')

                values = dict(
                    url_annonce=url_annonce,
                    titre=a.get('titre') or a.get('title'),
                    description=a.get('description'),
                    prix=prix,
                    superficie=superficie,
                    type_bien=type_bien,
                    localisation=localisation,
                    ville=ville,
                    region=a.get('region'),
                )
                stmt = upsert_update(AnnonceMubawab, values, index_elements=['url_annonce'])
                session.execute(stmt)
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

            _insert_snapshots(session, scrape_run_id, snapshot_rows)
        logger.info("%d annonces Mubawab insérées.", inserted)
        if own_run:
            finish_scrape_run(scrape_run_id, 'succes', inserted)
    except Exception:
        logger.exception("Erreur insertion Mubawab")
        if own_run:
            finish_scrape_run(scrape_run_id, 'erreur', inserted)
    return inserted

def get_annonces_mubawab_filtered(**filters):
    with session_scope() as session:
        pm2 = func.round(cast(AnnonceMubawab.prix, Numeric) / func.nullif(AnnonceMubawab.superficie, 0), 2).label('prix_m2')
        stmt = select(AnnonceMubawab, pm2)

        if filters.get('ville'):
            stmt = stmt.where(or_(
                AnnonceMubawab.ville == filters['ville'],
                AnnonceMubawab.localisation == filters['ville'],
            ))

        if filters.get('type_bien'):
            from services.type_mapping import get_brut_types_for_normalized
            brut_list = get_brut_types_for_normalized(filters['type_bien'])
            stmt = stmt.where(AnnonceMubawab.type_bien.in_(brut_list)) if brut_list else stmt.where(false())
        elif filters.get('type_brut_list'):
            stmt = stmt.where(AnnonceMubawab.type_bien.in_(filters['type_brut_list']))

        # --- FILTRE REGION ---
        if filters.get('region'):
            stmt = stmt.where(AnnonceMubawab.region == filters['region'])
        # --------------------

        if filters.get('budget_min') is not None:
            stmt = stmt.where(AnnonceMubawab.prix >= filters['budget_min'])
        if filters.get('budget_max') is not None:
            stmt = stmt.where(AnnonceMubawab.prix <= filters['budget_max'])
        if filters.get('superficie_min') is not None:
            stmt = stmt.where(AnnonceMubawab.superficie >= filters['superficie_min'])
        if filters.get('superficie_max') is not None:
            stmt = stmt.where(AnnonceMubawab.superficie <= filters['superficie_max'])
        if filters.get('prix_m2_min') is not None:
            stmt = stmt.where(pm2 >= filters['prix_m2_min'])
        if filters.get('prix_m2_max') is not None:
            stmt = stmt.where(pm2 <= filters['prix_m2_max'])

        stmt = stmt.order_by(pm2.asc())
        result = []
        for row in session.execute(stmt):
            d = _model_to_dict(row[0])
            d['prix_m2'] = row[1]
            result.append(d)
        return result

# ==================== STATISTIQUES GLOBALES ====================
def get_statistiques_globales():
    with session_scope() as session:
        stats = {}
        stats['nb_projets'] = session.execute(select(func.count()).select_from(Projet)).scalar()
        stats['nb_lots'] = session.execute(select(func.count()).select_from(Lot)).scalar()
        stats['nb_produits'] = session.execute(select(func.count()).select_from(Produit)).scalar()
        stats['nb_sarouty'] = session.execute(select(func.count()).select_from(AnnonceSarouty)).scalar()
        stats['nb_mubawab'] = session.execute(select(func.count()).select_from(AnnonceMubawab)).scalar()

        stats['villes'] = [row[0] for row in session.execute(select(distinct(Projet.localisation)))]
        stats['types_biens'] = [row[0] for row in session.execute(select(distinct(Projet.type_bien)))]

        stats['villes_sarouty'] = [row[0] for row in session.execute(select(distinct(AnnonceSarouty.ville)))]
        stats['types_sarouty'] = [row[0] for row in session.execute(select(distinct(AnnonceSarouty.type_bien)))]

        stats['villes_mubawab'] = [row[0] for row in session.execute(select(distinct(AnnonceMubawab.ville)))]
        stats['types_mubawab'] = [row[0] for row in session.execute(select(distinct(AnnonceMubawab.type_bien)))]

        # Favoris
        stats['nb_favoris'] = session.execute(select(func.count()).select_from(Favori)).scalar()

        return stats

def get_prix_m2_stats(ville=None, type_bien=None):
    with session_scope() as session:
        surface_m2 = clean_numeric_col(Produit.surface, 'm²').label('surface_m2')
        prix_brut = clean_numeric_col(Produit.prix, 'DH').label('prix_brut')
        stmt = (
            select(surface_m2, prix_brut)
            .select_from(Produit)
            .join(Lot, Lot.id == Produit.lot_id)
            .join(Projet, Projet.id == Lot.projet_id)
            .where(clean_numeric_col(Produit.prix, 'DH') > 0)
        )
        if ville:
            stmt = stmt.where(Projet.localisation == ville)
        if type_bien:
            from services.type_mapping import get_brut_types_for_normalized
            brut_list = get_brut_types_for_normalized(type_bien)
            stmt = stmt.where(Projet.type_bien.in_(brut_list)) if brut_list else stmt.where(false())
        rows = session.execute(stmt).all()

    prix_m2_list = [
        prix / surface
        for surface, prix in rows
        if surface and prix and surface > 0 and prix > 0
    ]
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
    with session_scope() as session:
        values = dict(
            source=source, annonce_id=annonce_id, url=url, titre=titre,
            localisation=localisation, type_bien=type_bien, surface=surface,
            prix=prix, prix_m2=prix_m2,
        )
        stmt = upsert_ignore(Favori, values, index_elements=['source', 'annonce_id'])
        result = session.execute(stmt)
        return result.rowcount > 0

def supprimer_favori(source, annonce_id):
    """Supprime une annonce des favoris."""
    with session_scope() as session:
        result = session.execute(
            delete(Favori).where(Favori.source == source, Favori.annonce_id == annonce_id)
        )
        return result.rowcount > 0

def get_favoris():
    """Retourne la liste de tous les favoris, triés par date d'ajout décroissante."""
    with session_scope() as session:
        rows = session.execute(select(Favori).order_by(Favori.date_ajout.desc())).scalars().all()
        return [_model_to_dict(row) for row in rows]


def get_favoris_set():
    """Retourne un dict {source: [annonce_id, ...]} pour le frontend."""
    with session_scope() as session:
        result = {}
        for source, annonce_id in session.execute(select(Favori.source, Favori.annonce_id)):
            key = str(source)
            result.setdefault(key, []).append(str(annonce_id))
        return result

def est_favori(source, annonce_id):
    """Vérifie si une annonce est déjà dans les favoris."""
    with session_scope() as session:
        return session.execute(
            select(Favori.id).where(Favori.source == source, Favori.annonce_id == annonce_id)
        ).first() is not None

# ==================== GESTION DES TACHES ====================

def create_task(task_id, source, initial_message="En attente..."):
    with session_scope() as session:
        session.add(Tache(id=task_id, source=source, status='en_cours', message=initial_message))

def update_task_status(task_id, status, message=None, result=None):
    with session_scope() as session:
        tache = session.get(Tache, task_id)
        if not tache:
            return

        tache.status = status
        if message is not None:
            tache.message = message
        if result is not None:
            import json
            tache.result = json.dumps(result)
        if status in ('termine', 'erreur'):
            tache.date_fin = func.now()

def get_task_status(task_id):
    with session_scope() as session:
        tache = session.get(Tache, task_id)
        if not tache:
            return None
        d = _model_to_dict(tache)
        import json
        if d.get('result'):
            try:
                d['result'] = json.loads(d['result'])
            except (TypeError, ValueError):
                pass
        return d
