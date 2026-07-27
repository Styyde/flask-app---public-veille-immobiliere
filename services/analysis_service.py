# services/analysis_service.py
import sqlite3
import pandas as pd
import statistics
import re
from config import DB_PATH
from .filter_service import filtrer_sarouty, filtrer_mubawab
from .type_mapping import get_normalized_type, get_brut_types_for_normalized
from analytics.scorer import identifier_opportunites


def get_analytics_dashboard(filtres=None):
    if filtres is None:
        filtres = {}

    type_filter = filtres.get('type_bien')
    ville_filter = filtres.get('ville')

    # ---- RÉCUPÉRATION AL OMRANE PAR SQL DIRECT ----
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    brut_types = []
    if type_filter:
        brut_types = get_brut_types_for_normalized(type_filter)
        if not brut_types:
            brut_types = ['__NO_MATCH__']

    query = """
        SELECT
            p.titre AS projet,
            p.localisation AS ville,
            p.type_bien,
            l.lot_titre AS lot,
            pr.no_produit AS produit,
            pr.surface,
            pr.prix,
            p.url AS url_projet,
            pr.url AS url_produit
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE 1=1
    """
    params = []
    if brut_types:
        placeholders = ','.join(['?'] * len(brut_types))
        query += f" AND p.type_bien IN ({placeholders})"
        params.extend(brut_types)
    if ville_filter:
        query += " AND p.localisation = ?"
        params.append(ville_filter)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # ---- CONSTRUCTION DE LA LISTE UNIFIÉE ----
    all_data = []

    # Al Omrane
    for row in rows:
        surface_str = row[5]
        if isinstance(surface_str, str):
            surf = re.sub(r'[^\d.]', '', surface_str)
            try:
                surface = float(surf)
            except ValueError:
                surface = 0
        else:
            surface = float(surface_str) if surface_str else 0

        prix_str = row[6]
        if isinstance(prix_str, str):
            prix = float(re.sub(r'[^\d.]', '', prix_str))
        else:
            prix = float(prix_str) if prix_str else 0

        if surface <= 0 or prix <= 0:
            continue

        prix_m2 = round(prix / surface, 2)
        type_norm = get_normalized_type(row[2])

        all_data.append({
            'source': 'Al Omrane',
            'titre': row[0],
            'ville': row[1],
            'localisation': row[1],
            'type_bien': type_norm,
            'surface': surface,
            'prix': prix,
            'prix_m2': prix_m2,
            'url': row[7] or row[8],
            'lot': row[3],
            'no_produit': row[4],
        })

    # ---- SAROUTY ----
    sarouty_data = filtrer_sarouty(**filtres)
    for s in sarouty_data:
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
        type_norm = get_normalized_type(s.get('type'))
        all_data.append({
            'source': 'Sarouty',
            'titre': s.get('projet'),
            'ville': s.get('localisation'),
            'localisation': s.get('localisation'),
            'type_bien': type_norm,
            'surface': surface,
            'prix': prix,
            'prix_m2': s.get('prix_m2') or round(prix / surface, 2),
            'url': s.get('url_annonce'),
            'lot': None,
            'no_produit': None,
        })

    # ---- MUBAWAB ----
    mubawab_data = filtrer_mubawab(**filtres)
    for m in mubawab_data:
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
        type_norm = get_normalized_type(m.get('type'))
        all_data.append({
            'source': 'Mubawab',
            'titre': m.get('projet'),
            'ville': m.get('localisation'),
            'localisation': m.get('localisation'),
            'type_bien': type_norm,
            'surface': surface,
            'prix': prix,
            'prix_m2': m.get('prix_m2') or round(prix / surface, 2),
            'url': m.get('url_annonce'),
            'lot': None,
            'no_produit': None,
        })

    # ---- FILTRAGE SUPPLÉMENTAIRE (ville) ----
    if ville_filter:
        all_data = [d for d in all_data if ville_filter.lower() in (d.get('ville') or '').lower()
                    or ville_filter.lower() in (d.get('localisation') or '').lower()]

    # ---- GARDER UNIQUEMENT LES DONNÉES VALIDES ----
    valid = [d for d in all_data if d.get('prix_m2') and d['prix_m2'] > 0]

    if not valid:
        return {
            'histogram': {'labels': [], 'counts': [], 'seuil_opportunite': 0},
            'comparaison': [],
            'distribution_types': [],
            'distribution_etages': [],
            'ville_etage': [],
            'opportunites': []
        }

    # ---- HISTOGRAMME ----
    prix_m2_values = [d['prix_m2'] for d in valid]
    hist = _get_histogram(prix_m2_values)

    # ---- COMPARAISON PAR VILLE ----
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

    # ---- DISTRIBUTION PAR TYPE ----
    if 'type_bien' in df.columns:
        type_dist = df.groupby('type_bien')['prix_m2'].agg(['mean', 'count']).reset_index()
        type_dist.columns = ['groupe', 'prix_m2_moyen', 'nb_produits']
        type_dist = type_dist.sort_values('prix_m2_moyen').to_dict(orient='records')
    else:
        type_dist = []

    # ---- OPPORTUNITÉS ----
    opportunites = identifier_opportunites()

    # Filtrer les opportunités par type et ville
    if ville_filter:
        opportunites = [o for o in opportunites if ville_filter.lower() in (o.get('localisation') or '').lower()]
    if type_filter:
        opportunites = [o for o in opportunites if o.get('type_bien') == type_filter]

    # Si aucune opportunité n'est trouvée, on retourne les 5 biens les moins chers (tous types) en les transformant au format attendu
    if not opportunites and valid:
        # Trier les biens valides par prix/m² croissant
        sorted_valid = sorted(valid, key=lambda x: x['prix_m2'])
        top5 = sorted_valid[:5]
        # Transformer en opportunités factices avec est_opportunite = False
        opportunites = []
        for item in top5:
            opportunites.append({
                'titre': item.get('titre'),
                'localisation': item.get('localisation'),
                'type_bien': item.get('type_bien'),
                'surface': item.get('surface'),
                'prix': item.get('prix'),
                'prix_m2': item.get('prix_m2'),
                'url': item.get('url'),
                'lot_titre': item.get('lot'),
                'no_produit': item.get('no_produit'),
                'est_opportunite': False,
                'ecart_pourcent': 0,
                'moyenne_groupe': 0,
            })

    return {
        'histogram': hist,
        'comparaison': comparaison[:15],
        'distribution_types': type_dist,
        'distribution_etages': [],
        'ville_etage': [],
        'opportunites': opportunites[:10]
    }


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


def analyser_opportunites(filtres=None):
    if filtres is None:
        filtres = {}
    opportunites = identifier_opportunites()
    if filtres.get('ville'):
        opportunites = [o for o in opportunites if filtres['ville'].lower() in (o.get('localisation') or '').lower()]
    if filtres.get('type_bien'):
        opportunites = [o for o in opportunites if o.get('type_bien') == filtres['type_bien']]
    return {'opportunites': opportunites[:10]}