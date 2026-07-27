# services/analysis_service.py
import pandas as pd
import statistics
import re
from .filter_service import filtrer_produits, filtrer_sarouty, filtrer_mubawab
from .type_mapping import get_normalized_type


def get_all_listings():
    """Récupère toutes les annonces des trois sources avec prix > 0 et types normalisés."""
    produits = filtrer_produits(limit=None)
    sarouty = filtrer_sarouty()
    mubawab = filtrer_mubawab()
    
    all_data = []
    
    # Al Omrane
    for p in produits:
        surface_str = p.get('surface')
        if isinstance(surface_str, str):
            surf = re.sub(r'[^\d.]', '', surface_str)
            try:
                surface = float(surf)
            except ValueError:
                surface = 0
        else:
            surface = float(surface_str) if surface_str else 0
            
        prix = p.get('prix')
        if prix is None:
            continue
        try:
            prix = float(prix)
        except (TypeError, ValueError):
            continue
        if surface <= 0 or prix <= 0:
            continue
            
        type_brut = p.get('type_bien')
        type_norm = get_normalized_type(type_brut)
        if not type_norm:
            type_norm = type_brut or "Inconnu"
            
        all_data.append({
            'source': 'Al Omrane',
            'titre': p.get('projet'),
            'ville': p.get('ville'),
            'localisation': p.get('ville'),
            'type_bien': type_norm,
            'type_brut': type_brut,
            'surface': surface,
            'prix': prix,
            'prix_m2': round(prix / surface, 2) if surface > 0 else 0,
            'url': p.get('url_projet'),
            'lot': p.get('lot'),
            'no_produit': p.get('produit'),
        })
    
    # Sarouty
    for s in sarouty:
        surface = float(s.get('surface')) if s.get('surface') else 0
        prix = s.get('prix')
        if prix is None:
            continue
        try:
            prix = float(prix)
        except (TypeError, ValueError):
            continue
        if surface <= 0 or prix <= 0:
            continue
            
        type_brut = s.get('type')
        type_norm = get_normalized_type(type_brut)
        if not type_norm:
            type_norm = type_brut or "Inconnu"
            
        all_data.append({
            'source': 'Sarouty',
            'titre': s.get('projet'),
            'ville': s.get('localisation'),
            'localisation': s.get('localisation'),
            'type_bien': type_norm,
            'type_brut': type_brut,
            'surface': surface,
            'prix': prix,
            'prix_m2': s.get('prix_m2') or round(prix / surface, 2),
            'url': s.get('url_annonce'),
            'lot': None,
            'no_produit': None,
        })
    
    # Mubawab
    for m in mubawab:
        surface = float(m.get('surface')) if m.get('surface') else 0
        prix = m.get('prix')
        if prix is None:
            continue
        try:
            prix = float(prix)
        except (TypeError, ValueError):
            continue
        if surface <= 0 or prix <= 0:
            continue
            
        type_brut = m.get('type')
        type_norm = get_normalized_type(type_brut)
        if not type_norm:
            type_norm = type_brut or "Inconnu"
            
        all_data.append({
            'source': 'Mubawab',
            'titre': m.get('projet'),
            'ville': m.get('localisation'),
            'localisation': m.get('localisation'),
            'type_bien': type_norm,
            'type_brut': type_brut,
            'surface': surface,
            'prix': prix,
            'prix_m2': m.get('prix_m2') or round(prix / surface, 2),
            'url': m.get('url_annonce'),
            'lot': None,
            'no_produit': None,
        })
    
    return all_data


def get_histogram_from_values(values, bins=10):
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


def get_analytics_dashboard(filtres=None):
    if filtres is None:
        filtres = {}
    ville_filter = filtres.get('ville')
    type_filter = filtres.get('type_bien')  # normalisé

    data = get_all_listings()
    if ville_filter:
        data = [d for d in data if ville_filter.lower() in (d.get('ville') or '').lower()
                or ville_filter.lower() in (d.get('localisation') or '').lower()]
    if type_filter:
        data = [d for d in data if d.get('type_bien') == type_filter]

    valid = [d for d in data if d.get('prix_m2') and d['prix_m2'] > 0]
    if not valid:
        return {
            'histogram': {'labels': [], 'counts': [], 'seuil_opportunite': 0},
            'comparaison': [],
            'distribution_types': [],
            'distribution_etages': [],
            'ville_etage': [],
            'opportunites': []
        }

    prix_m2_values = [d['prix_m2'] for d in valid]
    hist = get_histogram_from_values(prix_m2_values)

    df = pd.DataFrame(valid)
    if 'ville' in df.columns:
        grouped = df.groupby('ville').agg({
            'prix_m2': ['mean', 'count', 'min', 'max'],
            'surface': 'mean'
        }).reset_index()
        grouped.columns = ['groupe', 'prix_m2_moyen', 'nb_produits', 'prix_min', 'prix_max', 'surface_moyenne']
        grouped = grouped.sort_values('prix_m2_moyen')
        comparaison = grouped.to_dict(orient='records')
    else:
        comparaison = []

    if 'type_bien' in df.columns:
        type_dist = df.groupby('type_bien')['prix_m2'].agg(['mean', 'count']).reset_index()
        type_dist.columns = ['groupe', 'prix_m2_moyen', 'nb_produits']
        type_dist = type_dist.sort_values('prix_m2_moyen').to_dict(orient='records')
    else:
        type_dist = []

    from analytics.scorer import identifier_opportunites
    opportunites = identifier_opportunites()
    if ville_filter:
        opportunites = [o for o in opportunites if ville_filter.lower() in (o.get('localisation') or '').lower()]
    if type_filter:
        opportunites = [o for o in opportunites if o.get('type_bien') == type_filter]

    return {
        'histogram': hist,
        'comparaison': comparaison[:15],
        'distribution_types': type_dist,
        'distribution_etages': [],
        'ville_etage': [],
        'opportunites': opportunites[:10]
    }


def analyser_opportunites(filtres=None):
    if filtres is None:
        filtres = {}
    data = get_all_listings()
    # (retour simplifié pour compatibilité)
    return {'produits': data, 'stats': {}}