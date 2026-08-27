# services/trends_service.py
"""
Agrégation de l'historique des annonces (table listing_snapshots) pour deux
analyses temporelles du dashboard "Évolution" :

1. Répartition des annonces par type de bien sur une période choisie.
2. Comparaison de plusieurs villes (médiane du prix/m², stock d'annonces)
   entre une période à analyser et une période de référence, elles aussi
   choisies manuellement.

La liste des villes suivies n'est PAS configurée à l'avance : elle est dérivée
dynamiquement des villes réellement présentes dans les données scrapées (colonne
`ville` de listing_snapshots), pour couvrir automatiquement toute nouvelle ville
ajoutée aux scrapers sans toucher au code de ce module.
"""
import datetime
import statistics
from collections import defaultdict

from database.db_manager import get_snapshots

from .type_mapping import get_all_normalized_types, get_normalized_type


def _normaliser_ville(ville):
    """Uniformise la casse (ex: 'casablanca' / 'CASABLANCA' -> 'Casablanca') pour
    éviter que la même ville apparaisse comme plusieurs entrées distinctes selon
    la source qui l'a scrapée."""
    if not ville:
        return None
    return ' '.join(w.capitalize() for w in str(ville).strip().split())


def get_villes_disponibles():
    """Villes distinctes réellement présentes dans l'historique scrapé, triées."""
    rows = get_snapshots()
    villes = {_normaliser_ville(r.get('ville')) for r in rows}
    villes.discard(None)
    return sorted(villes)


def get_types_disponibles():
    return get_all_normalized_types()


def _fetch_normalized_snapshots(date_from=None, date_to=None, types=None):
    rows = get_snapshots(date_from=date_from, date_to=date_to)
    out = []
    for r in rows:
        ville = _normaliser_ville(r.get('ville'))
        if not ville:
            continue
        r = dict(r)
        r['ville'] = ville
        r['type_normalise'] = get_normalized_type(r.get('type_bien')) or 'Autre'
        out.append(r)
    if types:
        types_set = set(types)
        out = [r for r in out if r['type_normalise'] in types_set]
    return out


def _dedupe_dernieres_annonces(rows):
    """Une même annonce vue plusieurs fois dans la période ne doit compter
    qu'une fois (avec sa version la plus récente) -- sinon un simple
    re-scraping gonflerait artificiellement les comptes/stocks."""
    dernier = {}
    for r in rows:
        cle = r.get('listing_key')
        if not cle:
            continue
        date = str(r.get('scraped_at') or '')
        if cle not in dernier or date > str(dernier[cle].get('scraped_at') or ''):
            dernier[cle] = r
    return list(dernier.values())


def _variation_pct(actuel, precedent):
    if not precedent:
        return None
    return round((actuel - precedent) / precedent * 100, 1)


# ============================================================
# Repartition des annonces par type de bien -- "combien pese chaque type
# dans le marche observe sur la periode choisie", en % du total.
# ============================================================

def get_distribution_types(date_from=None, date_to=None):
    """Repartition des annonces par type de bien sur une periode (par defaut
    les 30 derniers jours si aucune date n'est fournie), en nombre et en %
    du total."""
    if not date_from and not date_to:
        date_from = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    rows = _fetch_normalized_snapshots(date_from=date_from, date_to=date_to)
    rows = _dedupe_dernieres_annonces(rows)

    compte = defaultdict(int)
    for r in rows:
        compte[get_normalized_type(r.get('type_bien')) or 'Autre'] += 1

    total = sum(compte.values())
    distribution = [
        {
            'type': type_bien,
            'nb_annonces': n,
            'pourcentage': round(n / total * 100, 1) if total else 0,
        }
        for type_bien, n in sorted(compte.items(), key=lambda item: -item[1])
    ]

    return {
        'date_from': date_from,
        'date_to': date_to,
        'total_annonces': total,
        'distribution': distribution,
    }


# ============================================================
# Comparaison entre villes -- "Rabat vs Casablanca vs Marrakech", filtrable
# par type de bien, sur une periode a analyser vs une periode de reference,
# toutes deux choisies manuellement (pas de notion de "run precedent" ici :
# l'utilisateur decide explicitement ce qu'il compare a quoi).
# ============================================================

def get_comparaison_villes(villes=None, type_bien=None, date_from=None, date_to=None,
                            compare_from=None, compare_to=None):
    """Pour chaque ville (celles fournies, ou toutes si `villes` est vide) :
    mediane du prix/m2 et stock (nombre d'annonces distinctes) sur la periode
    a analyser, avec variation vs la periode de reference si elle est fournie.

    La mediane est utilisee plutot que la moyenne : un petit nombre de biens
    tres au-dessus ou en-dessous du marche (ex: un terrain agricole scrape
    par erreur au milieu d'appartements) ne doit pas a lui seul deplacer
    l'indicateur -- important sur des echantillons parfois petits."""
    types_filtre = [type_bien] if type_bien else None

    def _stats_periode(d_from, d_to):
        if not d_from and not d_to:
            return {}
        rows = _fetch_normalized_snapshots(date_from=d_from, date_to=d_to, types=types_filtre)
        rows = _dedupe_dernieres_annonces(rows)
        rows = [r for r in rows if r.get('prix_m2') and r['prix_m2'] > 0]

        par_ville = defaultdict(list)
        for r in rows:
            par_ville[r['ville']].append(r['prix_m2'])

        return {
            ville: {'mediane': round(statistics.median(valeurs), 2), 'stock': len(valeurs)}
            for ville, valeurs in par_ville.items()
        }

    stats_analyse = _stats_periode(date_from, date_to)
    stats_comparaison = _stats_periode(compare_from, compare_to)

    villes_cibles = villes if villes else sorted(stats_analyse.keys())

    resultats = []
    for ville in villes_cibles:
        actuel = stats_analyse.get(ville)
        precedent = stats_comparaison.get(ville)
        resultats.append({
            'ville': ville,
            'mediane': actuel['mediane'] if actuel else None,
            'stock': actuel['stock'] if actuel else 0,
            'variation_pct': _variation_pct(actuel['mediane'], precedent['mediane']) if (actuel and precedent) else None,
            'variation_stock_pct': _variation_pct(actuel['stock'], precedent['stock']) if (actuel and precedent) else None,
        })
    resultats.sort(key=lambda r: -(r['stock'] or 0))

    return {'villes': resultats}
