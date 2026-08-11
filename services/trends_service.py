# services/trends_service.py
"""
Agrégation de l'historique des annonces (table listing_snapshots) pour visualiser
l'évolution du prix/m² et du nombre d'annonces dans le temps, par type de bien et par zone.

Chaque scrape (manuel, tous les ~2 semaines) écrit un snapshot par annonce vue. La
granularité par défaut ('run') fait donc correspondre un point de courbe à une
campagne de scraping, ce qui colle à la cadence réelle de collecte. Les granularités
calendaires (jour/semaine/mois) sont disponibles pour plus tard si la cadence change.
"""
import datetime
from collections import defaultdict

from config import ZONES_SUIVIES
from database.db_manager import get_snapshots
from .type_mapping import get_normalized_type, get_all_normalized_types

GRANULARITES = ('run', 'jour', 'semaine', 'mois')

_ZONES_AVEC_QUARTIER = [z for z in ZONES_SUIVIES if z.get('quartier')]
_ZONES_VILLE_SEULE = [z for z in ZONES_SUIVIES if not z.get('quartier')]
_QUARTIERS_DEDIES_PAR_VILLE = defaultdict(set)
for _z in _ZONES_AVEC_QUARTIER:
    _QUARTIERS_DEDIES_PAR_VILLE[_z['ville'].strip().lower()].add(_z['quartier'].strip().lower())


def get_zones_disponibles():
    return [z['label'] for z in ZONES_SUIVIES]


def get_types_disponibles():
    return get_all_normalized_types()


def match_zone_label(ville, quartier):
    """Retourne le libellé de zone suivie correspondant à (ville, quartier), ou None."""
    ville_n = (ville or '').strip().lower()
    quartier_n = (quartier or '').strip().lower()
    if not ville_n:
        return None

    for z in _ZONES_AVEC_QUARTIER:
        if ville_n == z['ville'].strip().lower() and quartier_n == z['quartier'].strip().lower():
            return z['label']

    for z in _ZONES_VILLE_SEULE:
        if ville_n == z['ville'].strip().lower():
            if quartier_n in _QUARTIERS_DEDIES_PAR_VILLE.get(ville_n, set()):
                continue  # ce quartier a sa propre zone dédiée, ne pas le compter dans la ville-mère
            return z['label']

    return None


def _villes_a_charger():
    return sorted({z['ville'] for z in ZONES_SUIVIES})


def _bucket_key_and_date(row, granularite):
    raw_date = row.get('scraped_at') or row.get('run_started_at') or ''
    date_part = str(raw_date)[:10]

    if granularite == 'jour':
        return date_part, date_part
    if granularite == 'semaine':
        try:
            d = datetime.date.fromisoformat(date_part)
            monday = d - datetime.timedelta(days=d.weekday())
            return monday.isoformat(), monday.isoformat()
        except ValueError:
            return date_part or 'inconnu', date_part
    if granularite == 'mois':
        return date_part[:7], date_part
    # 'run' (défaut) : un point par campagne de scraping
    run_id = row.get('scrape_run_id')
    key = f"run-{run_id}" if run_id else (date_part or 'inconnu')
    return key, date_part


def _fetch_filtered_snapshots(date_from=None, date_to=None, types=None):
    rows = get_snapshots(date_from=date_from, date_to=date_to, villes=_villes_a_charger())
    for r in rows:
        r['zone'] = match_zone_label(r.get('ville'), r.get('quartier'))
        r['type_normalise'] = get_normalized_type(r.get('type_bien')) or 'Autre'
    rows = [r for r in rows if r['zone']]
    if types:
        types_set = set(types)
        rows = [r for r in rows if r['type_normalise'] in types_set]
    return rows


def _build_series(rows, granularite, aggregate_fn):
    """
    aggregate_fn reçoit la liste des lignes d'un (bucket, serie) et retourne la valeur du point.
    Regroupe par (bucket, type_normalise + zone), trie les buckets chronologiquement.
    """
    buckets = defaultdict(lambda: defaultdict(list))
    bucket_dates = {}

    for r in rows:
        bucket, date_part = _bucket_key_and_date(r, granularite)
        serie_key = f"{r['type_normalise']} — {r['zone']}"
        buckets[bucket][serie_key].append(r)
        if bucket not in bucket_dates or date_part < bucket_dates[bucket]:
            bucket_dates[bucket] = date_part

    sorted_buckets = sorted(buckets.keys(), key=lambda b: bucket_dates.get(b, ''))
    series_keys = sorted({sk for b in buckets.values() for sk in b.keys()})

    series = []
    for sk in series_keys:
        points = []
        for b in sorted_buckets:
            group_rows = buckets[b].get(sk, [])
            points.append({
                'periode': bucket_dates.get(b, b),
                'valeur': aggregate_fn(group_rows) if group_rows else None,
                'nb_annonces': len(group_rows),
            })
        series.append({'serie': sk, 'points': points})

    return {
        'granularite': granularite,
        'periodes': [bucket_dates.get(b, b) for b in sorted_buckets],
        'series': series,
    }


def get_evolution_prix_m2(granularite='run', date_from=None, date_to=None, types=None):
    if granularite not in GRANULARITES:
        granularite = 'run'
    rows = _fetch_filtered_snapshots(date_from, date_to, types)
    rows = [r for r in rows if r.get('prix_m2') and r['prix_m2'] > 0]

    def moyenne_prix_m2(group_rows):
        valeurs = [r['prix_m2'] for r in group_rows]
        return round(sum(valeurs) / len(valeurs), 2)

    return _build_series(rows, granularite, moyenne_prix_m2)


def get_evolution_nb_annonces(granularite='run', date_from=None, date_to=None, types=None):
    if granularite not in GRANULARITES:
        granularite = 'run'
    rows = _fetch_filtered_snapshots(date_from, date_to, types)

    def compte(group_rows):
        return len(group_rows)

    return _build_series(rows, granularite, compte)
