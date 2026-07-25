# services/analysis_service.py
from analytics.scorer import identifier_opportunites
from .filter_service import filtrer_produits, filtrer_sarouty
from .stats_service import (
    get_distribution_prix_m2,
    get_distribution_etages,
    get_prix_m2_par_ville_et_etage,
    get_histogram_prix_m2,
    get_stats_distribution,
)


def get_analytics_dashboard(filtres=None):
    """Tableau de bord analytics pour l'UI."""
    if filtres is None:
        filtres = {}

    ville = filtres.get('ville')
    type_bien = filtres.get('type_bien')

    opportunites = identifier_opportunites()[:10]
    if ville:
        opportunites = [o for o in opportunites if o.get('localisation') == ville][:10]

    return {
        'histogram': get_histogram_prix_m2(filtre_ville=ville, filtre_type=type_bien),
        'comparaison': get_stats_distribution(
            grouper='localisation',
            filtre_ville=ville,
            filtre_etage=filtres.get('etage'),
        )[:15],
        'distribution_types': get_distribution_prix_m2(
            group_by='type_bien',
            filtre_ville=ville,
            filtre_etage=filtres.get('etage'),
        ),
        'distribution_etages': get_distribution_etages(filtre_ville=ville),
        'ville_etage': get_prix_m2_par_ville_et_etage(filtre_ville=ville),
        'opportunites': [{
            'titre': o.get('titre'),
            'localisation': o.get('localisation'),
            'type_bien': o.get('type_bien'),
            'lot_titre': o.get('lot_titre'),
            'no_produit': o.get('no_produit'),
            'surface': o.get('surface'),
            'prix': o.get('prix'),
            'prix_m2': o.get('prix_m2'),
            'moyenne_groupe': o.get('moyenne_groupe'),
            'ecart_pourcent': o.get('ecart_pourcent'),
            'est_opportunite': o.get('est_opportunite'),
            'url': o.get('url'),
            'etage': o.get('etage'),
        } for o in opportunites],
    }


def analyser_opportunites(filtres=None):
    """Rapport complet filtrage + stats (pour scripts/tests)."""
    if filtres is None:
        filtres = {}
    produits = filtrer_produits(**filtres)
    sarouty = filtrer_sarouty(**filtres)

    prix_m2_list = [p['prix_m2'] for p in produits if p.get('prix_m2')]
    prix_m2_list += [s['prix_m2'] for s in sarouty if s.get('prix_m2')]

    stats = {
        'total': len(produits) + len(sarouty),
        'prix_m2_moyen': round(sum(prix_m2_list) / len(prix_m2_list), 2) if prix_m2_list else 0,
        'prix_m2_min': min(prix_m2_list) if prix_m2_list else 0,
        'prix_m2_max': max(prix_m2_list) if prix_m2_list else 0,
        'distribution_etages': get_distribution_etages(filtre_ville=filtres.get('ville')),
        'distribution_types': get_distribution_prix_m2(
            group_by='type_bien',
            filtre_ville=filtres.get('ville'),
        ),
        'distribution_villes': get_distribution_prix_m2(
            group_by='localisation',
            filtre_ville=filtres.get('ville'),
        ),
    }
    return {'produits': produits, 'sarouty': sarouty, 'stats': stats}
