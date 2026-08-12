# services/stats_service.py
from sqlalchemy import func, select

from database.expressions import clean_numeric_col
from database.models import Lot, Produit, Projet
from database.session import session_scope

ALLOWED_GROUPERS = {'type_bien', 'localisation'}

def get_stats_distribution(grouper="type_bien", filtre_ville=None):
    if grouper not in ALLOWED_GROUPERS:
        grouper = 'type_bien'
    group_col = getattr(Projet, grouper)

    prix_clean = clean_numeric_col(Produit.prix, 'DH')
    surface_clean = clean_numeric_col(Produit.surface, 'm²')
    pm2 = prix_clean / func.nullif(surface_clean, 0)
    prix_m2_moyen_col = func.avg(pm2).label('prix_m2_moyen')

    with session_scope() as session:
        stmt = (
            select(
                group_col.label('groupe'),
                func.count(Produit.id).label('nb_produits'),
                prix_m2_moyen_col,
                func.min(prix_clean).label('prix_min'),
                func.max(prix_clean).label('prix_max'),
                func.avg(surface_clean).label('surface_moyenne'),
            )
            .select_from(Produit)
            .join(Lot, Lot.id == Produit.lot_id)
            .join(Projet, Projet.id == Lot.projet_id)
            .where(prix_clean > 0)
        )
        if filtre_ville:
            stmt = stmt.where(Projet.localisation == filtre_ville)
        stmt = stmt.group_by(group_col).order_by(prix_m2_moyen_col.asc())

        rows = session.execute(stmt).all()

    return [{
        "groupe": row.groupe or "Inconnu",
        "nb_produits": row.nb_produits,
        "prix_m2_moyen": round(row.prix_m2_moyen, 2) if row.prix_m2_moyen else 0,
        "prix_min": row.prix_min or 0,
        "prix_max": row.prix_max or 0,
        "surface_moyenne": round(row.surface_moyenne, 2) if row.surface_moyenne else 0,
    } for row in rows]

def get_distribution_prix_m2(group_by="type_bien", filtre_ville=None):
    return get_stats_distribution(grouper=group_by, filtre_ville=filtre_ville)

def get_histogram_prix_m2(filtre_ville=None, filtre_type=None, bins=10):
    prix_clean = clean_numeric_col(Produit.prix, 'DH')
    surface_clean = clean_numeric_col(Produit.surface, 'm²')
    pm2 = (prix_clean / func.nullif(surface_clean, 0)).label('prix_m2')

    with session_scope() as session:
        stmt = (
            select(pm2)
            .select_from(Produit)
            .join(Lot, Lot.id == Produit.lot_id)
            .join(Projet, Projet.id == Lot.projet_id)
            .where(prix_clean > 0, surface_clean > 0)
        )
        if filtre_ville:
            stmt = stmt.where(Projet.localisation == filtre_ville)
        if filtre_type:
            stmt = stmt.where(Projet.type_bien == filtre_type)
        values = [row[0] for row in session.execute(stmt) if row[0] and row[0] > 0]

    if not values:
        return {'labels': [], 'counts': [], 'seuil_opportunite': 0}
    import statistics
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return {
            'labels': [f'{round(min_v)}'],
            'counts': [len(values)],
            'seuil_opportunite': round(min_v, 2)
        }
    step = (max_v - min_v) / bins
    counts = [0] * bins
    labels = []
    for i in range(bins):
        lo = min_v + i * step
        hi = lo + step
        labels.append(f'{round(lo):,}–{round(hi):,}')
        counts[i] = sum(1 for v in values if (lo <= v < hi) or (i == bins - 1 and v <= hi))
    seuil = statistics.quantiles(values, n=4)[0] if len(values) >= 4 else min_v
    return {
        'labels': labels,
        'counts': counts,
        'seuil_opportunite': round(seuil, 2)
    }
