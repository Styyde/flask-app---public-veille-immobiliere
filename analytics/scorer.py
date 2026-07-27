# analytics/scorer.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
import re
from services.analysis_service import get_all_listings


def identifier_opportunites(seuil_ecart=15):
    listings = get_all_listings()
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
        type_bien = item.get('type_bien') or 'Inconnu'  # déjà normalisé

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

    # Grouper par (localisation, type_bien) – type_bien est déjà normalisé
    groupes = {}
    for p in produits:
        cle = f"{p['localisation']}_{p['type_bien']}"
        if cle not in groupes:
            groupes[cle] = []
        groupes[cle].append(p)

    opportunites = []
    for cle, items in groupes.items():
        prix_m2_liste = [p['prix_m2'] for p in items if p['prix_m2'] > 0]
        if len(prix_m2_liste) > 1:
            moyenne = statistics.mean(prix_m2_liste)
            ecart_type = statistics.stdev(prix_m2_liste) if len(prix_m2_liste) > 1 else 0
        else:
            moyenne = prix_m2_liste[0] if prix_m2_liste else 0
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

    opportunites.sort(key=lambda x: x['prix_m2'])
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
    print(f"🏆 TOP {limit} OPPORTUNITÉS (prix/m² le plus bas) - TYPES NORMALISÉS")
    print("="*100)
    top = opportunites[:limit] if len(opportunites) >= limit else opportunites
    for i, p in enumerate(top, 1):
        print(f"\n#{i} {p['titre']} ({p['localisation']})")
        print(f"   📦 Lot: {p['lot_titre']}")
        print(f"   🏷️  Produit: {p['no_produit']}")
        print(f"   📐 Surface: {p['surface']:.0f} m²")
        print(f"   💰 Prix: {p['prix']:,.0f} DH")
        print(f"   📊 Prix/m²: {p['prix_m2']:,.2f} DH/m²")
        print(f"   📈 Moyenne {p['type_bien']} à {p['localisation']}: {p['moyenne_groupe']:,.2f} DH/m²")
        print(f"   🎯 Écart: {p['ecart_pourcent']:.1f}%")
        if p['est_opportunite']:
            print("   🔥 **OPPORTUNITÉ !** Moins cher que la moyenne de sa catégorie")
    print("\n" + "="*100)

if __name__ == "__main__":
    afficher_top_opportunites(10)