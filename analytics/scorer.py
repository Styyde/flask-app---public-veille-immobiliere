# analytics/scorer.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
import re
from collections import defaultdict

from services.filter_service import filtrer_produits, filtrer_sarouty, filtrer_mubawab
from services.type_mapping import get_normalized_type


def _get_all_listings():
    """Récupère toutes les annonces des trois sources avec prix > 0 et surface > 0."""
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
    
    return all_data


def identifier_opportunites(seuil_ecart=15):
    """
    Retourne la liste des opportunités triées par prix/m² croissant.
    Si aucune opportunité n'est détectée, retourne les 5 biens les moins chers (tous types).
    """
    listings = _get_all_listings()
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

        prix_m2 = prix / surface
        ville = item.get('ville') or item.get('localisation') or 'Inconnu'
        type_bien = item.get('type_bien') or 'Inconnu'

        produits.append({
            'titre': item.get('titre'),
            'localisation': ville,
            'type_bien': type_bien,
            'surface': surface,
            'prix': prix,
            'prix_m2': prix_m2,
            'url': item.get('url'),
            'source': item.get('source'),
            'lot_titre': item.get('lot'),
            'no_produit': item.get('no_produit'),
        })

    if not produits:
        return []

    # 1. Calcul des moyennes globales par type
    global_prix_m2_by_type = defaultdict(list)
    for p in produits:
        global_prix_m2_by_type[p['type_bien']].append(p['prix_m2'])
    global_avg = {
        t: statistics.mean(vals) for t, vals in global_prix_m2_by_type.items() if len(vals) > 0
    }

    # 2. Regroupement par (ville, type_bien)
    groupes = {}
    for p in produits:
        cle = f"{p['localisation']}_{p['type_bien']}"
        if cle not in groupes:
            groupes[cle] = []
        groupes[cle].append(p)

    opportunites = []

    for cle, items in groupes.items():
        prix_m2_liste = [p['prix_m2'] for p in items if p['prix_m2'] > 0]

        if len(prix_m2_liste) >= 2:
            moyenne = statistics.mean(prix_m2_liste)
            ecart_type = statistics.stdev(prix_m2_liste) if len(prix_m2_liste) > 1 else 0
        else:
            type_bien = items[0]['type_bien']
            moyenne = global_avg.get(type_bien, 0)
            ecart_type = 0

        for p in items:
            if p['prix_m2'] > 0 and moyenne > 0:
                ecart = ((p['prix_m2'] - moyenne) / moyenne) * 100
                p['moyenne_groupe'] = round(moyenne, 2)
                p['ecart_type_groupe'] = round(ecart_type, 2)
                p['ecart_pourcent'] = round(ecart, 2)
                p['est_opportunite'] = ecart < -seuil_ecart
                p['score'] = round((moyenne - p['prix_m2']) / (ecart_type + 1), 2) if ecart_type > 0 else 999
                opportunites.append(p)

    # Trier par prix/m² croissant
    opportunites.sort(key=lambda x: x['prix_m2'])

    # Si aucune opportunité n'est détectée, retourner les 5 biens les moins chers
    if not opportunites:
        # On prend les 5 biens les moins chers (tous types confondus)
        sorted_by_price = sorted(produits, key=lambda x: x['prix_m2'])
        top5 = sorted_by_price[:5]
        for p in top5:
            # Ajouter des métadonnées minimales pour l'affichage
            p['moyenne_groupe'] = global_avg.get(p['type_bien'], 0)
            p['ecart_pourcent'] = 0
            p['est_opportunite'] = False
            p['score'] = 0
            opportunites.append(p)

    return opportunites


def get_top_opportunities_for_email(limit=10):
    opportunites = identifier_opportunites()
    return opportunites[:limit] if len(opportunites) >= limit else opportunites


def afficher_top_opportunites(limit=10):
    opportunites = identifier_opportunites()
    if not opportunites:
        print("\n⚠️ Aucune opportunité trouvée.")
        return

    print("\n" + "="*100)
    print(f"🏆 TOP {limit} OPPORTUNITÉS (prix/m² le plus bas)")
    print("="*100)

    top = opportunites[:limit] if len(opportunites) >= limit else opportunites
    for i, p in enumerate(top, 1):
        print(f"\n#{i} {p['titre']} ({p['localisation']})")
        print(f"   📦 Lot: {p['lot_titre']}")
        print(f"   🏷️  Produit: {p['no_produit']}")
        print(f"   📐 Surface: {p['surface']:.0f} m²")
        print(f"   💰 Prix: {p['prix']:,.0f} DH")
        print(f"   📊 Prix/m²: {p['prix_m2']:,.2f} DH/m²")
        if 'moyenne_groupe' in p and p['moyenne_groupe']:
            print(f"   📈 Moyenne de référence ({p['type_bien']}): {p['moyenne_groupe']:,.2f} DH/m²")
        if 'ecart_pourcent' in p and p['ecart_pourcent']:
            print(f"   🎯 Écart: {p['ecart_pourcent']:.1f}%")
        if p.get('est_opportunite'):
            print("   🔥 **OPPORTUNITÉ !** Moins cher que la moyenne de sa catégorie")
    print("\n" + "="*100)


if __name__ == "__main__":
    afficher_top_opportunites(10)