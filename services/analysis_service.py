# services/analysis_service.py
import logging
import statistics
import re
from collections import defaultdict

from .filter_service import filtrer_produits, filtrer_sarouty, filtrer_mubawab
from .type_mapping import get_normalized_type
from analytics.scorer import calculer_opportunites_sur_donnees, annoter_opportunites_sur_donnees

logger = logging.getLogger(__name__)


def _clean_float(val):
    """
    Nettoie une valeur pour la convertir en float.
    Gère les chaînes avec espaces, virgules, unités (DH, m², etc.).
    """
    if val is None:
        return None
    try:
        # Si c'est déjà un nombre, on le retourne
        if isinstance(val, (int, float)):
            return float(val)
        # Sinon, on nettoie la chaîne
        cleaned = re.sub(r'[^\d.]', '', str(val))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def get_analytics_dashboard(filtres=None):
    if filtres is None:
        filtres = {}

    logger.debug(f"Filtres reçus (bruts) : {filtres}")

    # Nettoyage des filtres quantitatifs
    budget_min = _clean_float(filtres.get('budget_min'))
    budget_max = _clean_float(filtres.get('budget_max'))
    surface_min = _clean_float(filtres.get('surface_min'))
    surface_max = _clean_float(filtres.get('surface_max'))
    prix_m2_min = _clean_float(filtres.get('prix_m2_min'))
    prix_m2_max = _clean_float(filtres.get('prix_m2_max'))

    logger.debug(
        f"Filtres quantitatifs nettoyés : budget_min={budget_min}, budget_max={budget_max}, "
        f"surface_min={surface_min}, surface_max={surface_max}, "
        f"prix_m2_min={prix_m2_min}, prix_m2_max={prix_m2_max}"
    )

    # 1. Récupération via les services de filtrage
    produits_alomrane = filtrer_produits(**filtres)
    annonces_sarouty = filtrer_sarouty(**filtres)
    annonces_mubawab = filtrer_mubawab(**filtres)

    valid_data = []

    # 2. Normalisation et unification
    for p in produits_alomrane:
        prix = _clean_float(p.get('prix'))
        surface = _clean_float(p.get('surface'))
        if prix is None or surface is None or surface == 0:
            continue
        type_norm = get_normalized_type(p.get('type_bien'))
        ville = p.get('ville') or p.get('localisation') or 'Inconnue'
        valid_data.append({
            'source': 'Al Omrane',
            'titre': p.get('projet'),
            'type_bien': type_norm,
            'ville': ville,
            'localisation': ville,
            'prix': prix,
            'surface': surface,
            'prix_m2': round(prix / surface, 2),
            'url': p.get('url_projet'),
            'lot': p.get('lot'),
            'no_produit': p.get('produit'),
        })

    for a in annonces_sarouty:
        prix = _clean_float(a.get('prix'))
        surface = _clean_float(a.get('surface'))
        if prix is None or surface is None or surface == 0:
            continue
        type_norm = get_normalized_type(a.get('type'))
        ville = a.get('localisation') or a.get('ville') or 'Inconnue'
        valid_data.append({
            'source': 'Sarouty',
            'titre': a.get('projet'),
            'type_bien': type_norm,
            'ville': ville,
            'localisation': ville,
            'prix': prix,
            'surface': surface,
            'prix_m2': round(prix / surface, 2),
            'url': a.get('url_annonce'),
            'lot': None,
            'no_produit': None,
        })

    for a in annonces_mubawab:
        prix = _clean_float(a.get('prix'))
        surface = _clean_float(a.get('surface'))
        if prix is None or surface is None or surface == 0:
            continue
        type_norm = get_normalized_type(a.get('type'))
        ville = a.get('localisation') or a.get('ville') or 'Inconnue'
        valid_data.append({
            'source': 'Mubawab',
            'titre': a.get('projet'),
            'type_bien': type_norm,
            'ville': ville,
            'localisation': ville,
            'prix': prix,
            'surface': surface,
            'prix_m2': round(prix / surface, 2),
            'url': a.get('url_annonce'),
            'lot': None,
            'no_produit': None,
        })

    logger.debug(f"Données brutes avant filtrage quantitatif : {len(valid_data)}")

    # 3. Filtrage par ville (déjà fait dans les services, mais on sécurise)
    ville_filter = filtres.get('ville')
    if ville_filter:
        before = len(valid_data)
        valid_data = [d for d in valid_data if ville_filter.lower() in (d.get('ville') or '').lower()
                      or ville_filter.lower() in (d.get('localisation') or '').lower()]
        logger.debug(f"Filtrage ville '{ville_filter}' : {before} -> {len(valid_data)}")

    # 4. Filtrage quantitatif en mémoire (budget, surface, prix/m²)
    if budget_min is not None:
        before = len(valid_data)
        valid_data = [d for d in valid_data if d['prix'] >= budget_min]
        logger.debug(f"Filtrage budget_min >= {budget_min} : {before} -> {len(valid_data)}")
    if budget_max is not None:
        before = len(valid_data)
        valid_data = [d for d in valid_data if d['prix'] <= budget_max]
        logger.debug(f"Filtrage budget_max <= {budget_max} : {before} -> {len(valid_data)}")
    if surface_min is not None:
        before = len(valid_data)
        valid_data = [d for d in valid_data if d['surface'] >= surface_min]
        logger.debug(f"Filtrage surface_min >= {surface_min} : {before} -> {len(valid_data)}")
    if surface_max is not None:
        before = len(valid_data)
        valid_data = [d for d in valid_data if d['surface'] <= surface_max]
        logger.debug(f"Filtrage surface_max <= {surface_max} : {before} -> {len(valid_data)}")
    if prix_m2_min is not None:
        before = len(valid_data)
        valid_data = [d for d in valid_data if d['prix_m2'] >= prix_m2_min]
        logger.debug(f"Filtrage prix_m2_min >= {prix_m2_min} : {before} -> {len(valid_data)}")
    if prix_m2_max is not None:
        before = len(valid_data)
        valid_data = [d for d in valid_data if d['prix_m2'] <= prix_m2_max]
        logger.debug(f"Filtrage prix_m2_max <= {prix_m2_max} : {before} -> {len(valid_data)}")

    # 5. Garder uniquement les entrées avec prix_m2 valide (> 0)
    valid_data = [d for d in valid_data if d.get('prix_m2') and d['prix_m2'] > 0]
    logger.debug(f"Données finales après tous les filtres : {len(valid_data)}")

    if not valid_data:
        return {
            'histogram': {'labels': [], 'counts': [], 'seuil_opportunite': 0},
            'comparaison': [],
            'distribution_types': [],
            'distribution_etages': [],
            'ville_etage': [],
            'opportunites': [],
            'scatter': [],
        }

    # 6. Graphiques
    hist = _get_histogram([d['prix_m2'] for d in valid_data])
    comparaison_villes = _groupby_and_avg(valid_data, 'ville')
    distribution_types = _groupby_and_avg(valid_data, 'type_bien')

    # 7. Opportunités + scatter
    annotated = annoter_opportunites_sur_donnees(valid_data)
    ann_lookup = {
        _scatter_key(d): d for d in annotated
    }
    scatter = [_build_scatter_point(d, ann_lookup.get(_scatter_key(d))) for d in valid_data]
    scatter = _limit_scatter(scatter, max_points=500)

    opportunites = calculer_opportunites_sur_donnees(valid_data)
    opportunites = opportunites[:20] if len(opportunites) > 20 else opportunites

    return {
        'histogram': hist,
        'comparaison': comparaison_villes,
        'distribution_types': distribution_types,
        'distribution_etages': [],
        'ville_etage': [],
        'opportunites': opportunites,
        'scatter': scatter,
    }


def analyser_opportunites(filtres=None):
    if filtres is None:
        filtres = {}
    dashboard = get_analytics_dashboard(filtres)
    return {'opportunites': dashboard.get('opportunites', [])}


# ---- Fonctions utilitaires ----

def _scatter_key(d):
    return (d.get('source'), d.get('titre'), d.get('surface'), d.get('prix'))


def _build_scatter_point(d, ann=None):
    ann = ann or {}
    return {
        'surface': d['surface'],
        'prix': d['prix'],
        'prix_m2': d['prix_m2'],
        'source': d.get('source', ''),
        'titre': d.get('titre') or 'Sans titre',
        'localisation': d.get('localisation') or d.get('ville') or '',
        'url': d.get('url') or '',
        'est_opportunite': bool(ann.get('est_opportunite', False)),
        'ecart_pourcent': ann.get('ecart_pourcent', 0),
    }


def _limit_scatter(points, max_points=500):
    if len(points) <= max_points:
        return points
    opportunites = [p for p in points if p.get('est_opportunite')]
    others = [p for p in points if not p.get('est_opportunite')]
    remaining = max_points - len(opportunites)
    if remaining <= 0:
        return opportunites[:max_points]
    step = max(1, len(others) // remaining)
    sampled = others[::step][:remaining]
    return opportunites + sampled


def _get_histogram(values, bins=10):
    if not values:
        return {'labels': [], 'counts': [], 'seuil_opportunite': 0}
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
    return {'labels': labels, 'counts': counts, 'seuil_opportunite': round(seuil, 2)}


def _groupby_and_avg(data, key):
    grouped = defaultdict(list)
    for item in data:
        if item.get(key):
            grouped[item[key]].append(item['prix_m2'])
    result = []
    for k, v in grouped.items():
        result.append({
            'groupe': k,
            'prix_m2_moyen': round(sum(v) / len(v), 2),
            'nb_produits': len(v),
            'prix_min': min(v),
            'prix_max': max(v),
            'surface_moyenne': 0
        })
    return sorted(result, key=lambda x: x['prix_m2_moyen'])