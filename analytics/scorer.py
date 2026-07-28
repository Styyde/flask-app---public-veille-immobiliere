# analytics/scorer.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
import re
from collections import defaultdict

from services.filter_service import filtrer_produits, filtrer_sarouty, filtrer_mubawab
from services.type_mapping import get_normalized_type


def _get_filtered_listings(filtres=None):
    """
    Récupère les annonces des trois sources en appliquant les filtres.
    Retourne une liste de dictionnaires avec les champs normalisés.
    """
    if filtres is None:
        filtres = {}

    source = filtres.get('source', 'all')
    produits_data = []
    sarouty_data = []
    mubawab_data = []

    if source in ('all', 'alomrane'):
        produits_data = filtrer_produits(**filtres)
    if source in ('all', 'sarouty'):
        sarouty_data = filtrer_sarouty(**filtres)
    if source in ('all', 'mubawab'):
        mubawab_data = filtrer_mubawab(**filtres)

    all_data = []

    # Al Omrane
    for p in produits_data:
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

        type_norm = get_normalized_type(p.get('type_bien'))

        all_data.append({
            'source': 'Al Omrane',
            'titre': p.get('projet'),
            'ville': p.get('ville'),
            'localisation': p.get('ville'),
            'type_bien': type_norm,
            'surface': surface,
            'prix': prix,
            'prix_m2': round(prix / surface, 2) if surface > 0 else 0,
            'url': p.get('url_projet'),
            'lot': p.get('lot'),
            'lot_titre': p.get('lot'),
            'no_produit': p.get('produit'),
        })

    # Sarouty
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
            'lot_titre': None,
            'no_produit': None,
        })

    # Mubawab
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
            'lot_titre': None,
            'no_produit': None,
        })

    return all_data


def calculer_opportunites_sur_donnees(produits_valides, seuil_ecart=15, max_resultats=20):
    """
    Calcule les opportunités à partir d'une liste de biens DÉJÀ filtrés.
    Une opportunité = bien dont le prix/m² est significativement inférieur
    à la moyenne de son groupe (ville + type_bien).
    - Exclut automatiquement les biens avec prix_m2 < 100 (valeur aberrante).
    - Si des opportunités existent (écart < -seuil), on les retourne triées par écart négatif.
    - Sinon, on retourne les 5 biens les moins chers du sous-ensemble, avec un indicateur est_opportunite=False.
    - Cela garantit que la liste n'est jamais vide quand il y a des données.
    """
    if not produits_valides:
        return []

    # === EXCLUSION DES PRIX/M² ABERRANTS (< 100 DH/m²) ===
    produits_valides = [
        p for p in produits_valides
        if p.get('prix_m2', 0) >= 100
    ]
    if not produits_valides:
        return []

    # 1. Moyennes globales par type (fallback si le groupe est trop petit)
    global_prix_m2_by_type = defaultdict(list)
    for p in produits_valides:
        prix_m2 = p.get('prix_m2', 0)
        if prix_m2 and prix_m2 > 0:
            type_bien = p.get('type_bien') or 'Inconnu'
            global_prix_m2_by_type[type_bien].append(prix_m2)

    global_avg = {
        t: statistics.mean(vals)
        for t, vals in global_prix_m2_by_type.items() if len(vals) > 0
    }

    # 2. Regroupement par (ville, type_bien)
    groupes = defaultdict(list)
    for p in produits_valides:
        ville = p.get('ville') or p.get('localisation') or 'Inconnue'
        type_bien = p.get('type_bien') or 'Inconnu'
        cle = f"{ville}_{type_bien}"
        groupes[cle].append(p)

    opportunites = []

    for cle, items in groupes.items():
        prix_m2_liste = [p['prix_m2'] for p in items if p.get('prix_m2', 0) > 0]
        if not prix_m2_liste:
            continue

        if len(prix_m2_liste) >= 2:
            moyenne = statistics.mean(prix_m2_liste)
            ecart_type = statistics.stdev(prix_m2_liste) if len(prix_m2_liste) > 1 else 0
        else:
            # Groupe trop petit → on utilise la moyenne globale du même type
            type_bien = items[0].get('type_bien', 'Inconnu')
            moyenne = global_avg.get(type_bien, 0)
            ecart_type = 0

        if moyenne <= 0:
            continue

        for p in items:
            p_m2 = p.get('prix_m2', 0)
            if p_m2 <= 0:
                continue

            ecart = ((p_m2 - moyenne) / moyenne) * 100

            # === On ne garde QUE les opportunités (sous le seuil) ===
            if ecart < -seuil_ecart:
                p_out = p.copy()
                p_out['moyenne_groupe'] = round(moyenne, 2)
                p_out['ecart_type_groupe'] = round(ecart_type, 2)
                p_out['ecart_pourcent'] = round(ecart, 2)
                p_out['est_opportunite'] = True
                p_out['score'] = round((moyenne - p_m2) / (ecart_type + 1), 2) if ecart_type > 0 else 999

                # Normalisation des champs pour l'affichage
                p_out['titre'] = p_out.get('titre') or p_out.get('projet') or 'Sans titre'
                p_out['localisation'] = p_out.get('ville') or p_out.get('localisation') or 'Inconnue'
                p_out['lot_titre'] = p_out.get('lot_titre') or p_out.get('lot')

                opportunites.append(p_out)

    # Tri : les plus sous-évaluées en premier (écart le plus négatif)
    opportunites.sort(key=lambda x: x['ecart_pourcent'])

    # 3. Fallback : si aucune opportunité, retourner les biens les moins chers
    if not opportunites and produits_valides:
        # Trier par prix/m² croissant
        sorted_by_price = sorted(produits_valides, key=lambda x: x.get('prix_m2', 999999))
        # Prendre les 5 premiers ou moins
        top_cheap = sorted_by_price[:min(5, len(sorted_by_price))]
        for p in top_cheap:
            p_out = p.copy()
            p_out['est_opportunite'] = False
            p_out['ecart_pourcent'] = 0
            p_out['moyenne_groupe'] = 0
            p_out['score'] = 0
            # Normalisation
            p_out['titre'] = p_out.get('titre') or p_out.get('projet') or 'Sans titre'
            p_out['localisation'] = p_out.get('ville') or p_out.get('localisation') or 'Inconnue'
            p_out['lot_titre'] = p_out.get('lot_titre') or p_out.get('lot')
            opportunites.append(p_out)

    # Limiter le nombre de résultats retournés
    return opportunites[:max_resultats]


def identifier_opportunites(filtres=None, seuil_ecart=15, max_resultats=20):
    """
    Identifie les opportunités en comparant chaque bien à la moyenne de son groupe
    (ville + type_bien), en utilisant les filtres fournis.
    Conservé pour la rétrocompatibilité (emails, CLI).
    """
    if filtres is None:
        filtres = {}

    listings = _get_filtered_listings(filtres)

    produits = []
    for item in listings:
        surface = item.get('surface')
        if not surface or surface <= 0:
            continue

        prix = item.get('prix')
        if not prix or prix <= 0:
            continue

        if isinstance(prix, str):
            prix = float(re.sub(r'[^\d.]', '', prix))
        else:
            prix = float(prix)

        if isinstance(surface, str):
            surface = float(re.sub(r'[^\d.]', '', surface))
        else:
            surface = float(surface)

        if surface <= 0 or prix <= 0:
            continue

        prix_m2 = round(prix / surface, 2)
        ville = item.get('ville') or item.get('localisation') or 'Inconnu'
        type_bien = item.get('type_bien') or 'Inconnu'

        produits.append({
            'titre': item.get('titre'),
            'ville': ville,
            'localisation': ville,
            'type_bien': type_bien,
            'surface': surface,
            'prix': prix,
            'prix_m2': prix_m2,
            'url': item.get('url'),
            'source': item.get('source'),
            'lot': item.get('lot'),
            'lot_titre': item.get('lot'),
            'no_produit': item.get('no_produit'),
        })

    return calculer_opportunites_sur_donnees(produits, seuil_ecart=seuil_ecart, max_resultats=max_resultats)


def get_top_opportunities_for_email(limit=10, filtres=None):
    if filtres is None:
        filtres = {}
    opportunites = identifier_opportunites(filtres, max_resultats=limit)
    return opportunites[:limit] if len(opportunites) >= limit else opportunites


def afficher_top_opportunites(limit=10, filtres=None):
    if filtres is None:
        filtres = {}

    opportunites = identifier_opportunites(filtres, max_resultats=limit)

    if not opportunites:
        print("\n⚠️ Aucune donnée ne correspond à ces filtres.")
        return

    print("\n" + "=" * 100)
    print(f"🏆 TOP {limit} OPPORTUNITÉS (prix/m² significativement sous la moyenne)")
    print("=" * 100)

    top = opportunites[:limit] if len(opportunites) >= limit else opportunites

    for i, p in enumerate(top, 1):
        print(f"\n#{i} {p['titre']} ({p['localisation']})")
        print(f" 📦 Lot        : {p.get('lot_titre') or p.get('lot')}")
        print(f" 🏷️  Produit    : {p.get('no_produit')}")
        print(f" 📐 Surface    : {p['surface']:.0f} m²")
        print(f" 💰 Prix       : {p['prix']:,.0f} DH")
        print(f" 📊 Prix/m²    : {p['prix_m2']:,.2f} DH/m²")
        if 'moyenne_groupe' in p and p['moyenne_groupe']:
            print(f" 📈 Moyenne réf.: {p['moyenne_groupe']:,.2f} DH/m²  ({p['type_bien']})")
        if 'ecart_pourcent' in p and p['ecart_pourcent'] != 0:
            print(f" 🎯 Écart      : {p['ecart_pourcent']:.1f}%")
        if p.get('est_opportunite'):
            print(" 🔥 **OPPORTUNITÉ**")
        else:
            print(" ℹ️  Meilleur prix du sous‑ensemble (pas d'opportunité forte)")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    # Exemple de test
    afficher_top_opportunites(
        limit=15,
        filtres={
            'source': 'alomrane',
            'type_bien': 'Commercial',
            'ville': 'Rabat'
        }
    )