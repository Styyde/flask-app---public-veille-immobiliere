# analytics/scorer.py
# Module d'analyse des opportunités immobilières
# Utilise le parser central pour enrichir les données avec l'étage

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import statistics
from config import DB_PATH
from utils.text_parser import extraire_etage_depuis_texte

def calculer_prix_m2_tous_produits():
    """
    Calcule le prix/m² pour chaque produit en base.
    Enrichit chaque produit avec l'étage (extrait de la designation ou du titre du lot si non renseigné).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # On récupère aussi l'étage stocké en base (s'il a été rempli par deep_scrape)
    cursor.execute("""
        SELECT 
            pr.id,
            p.id as projet_id,
            p.titre,
            p.localisation,
            p.region,
            p.type_bien,
            p.badge,
            pr.surface,
            pr.prix,
            l.lot_titre,
            pr.no_produit,
            p.url,
            pr.etage,
            pr.designation
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
    """)
    
    produits = []
    for row in cursor.fetchall():
        try:
            surface = float(row[7].replace('m²', '').replace(' ', '').strip())
            prix = float(row[8].replace('DH', '').replace(' ', '').strip())
            if surface > 0:
                prix_m2 = prix / surface
                
                # Récupération de l'étage :
                # 1. Si déjà stocké en base (via deep_scrape), on le garde.
                # 2. Sinon, on l'extrait depuis la designation ou le titre du lot.
                etage = row[12]  # colonne etage
                if not etage or etage == "":
                    designation = row[13] if row[13] else ""
                    texte_source = designation if designation else row[9]  # lot_titre
                    etage = extraire_etage_depuis_texte(texte_source)
                
                produits.append({
                    'id': row[0],
                    'projet_id': row[1],
                    'titre': row[2],
                    'localisation': row[3],
                    'region': row[4],
                    'type_bien': row[5],
                    'badge': row[6],
                    'surface': surface,
                    'prix': prix,
                    'prix_m2': round(prix_m2, 2),
                    'lot_titre': row[9],
                    'no_produit': row[10],
                    'url': row[11],
                    'etage': etage  # Champ enrichi
                })
        except Exception as e:
            # Ignorer les lignes mal formatées
            pass
    
    conn.close()
    return produits

def identifier_opportunites(seuil_ecart=15):
    """
    Identifie les meilleures opportunités en comparant chaque produit
    à la moyenne de sa catégorie (ville + type + étage).
    
    Args:
        seuil_ecart (int): Pourcentage d'écart pour considérer une opportunité (défaut: 15%)
    
    Returns:
        list: Produits triés par prix/m² avec indicateurs d'opportunité
    """
    produits = calculer_prix_m2_tous_produits()
    
    if not produits:
        return []
    
    # Grouper par (localisation, type_bien, etage) pour des comparaisons pertinentes
    groupes = {}
    for p in produits:
        cle = f"{p['localisation']}_{p['type_bien']}_{p['etage']}"
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
    
    # Trier par prix/m² croissant (les meilleures affaires d'abord)
    opportunites.sort(key=lambda x: x['prix_m2'])
    
    return opportunites

def get_top_opportunities_for_email(limit=10):
    """Récupère les top opportunités formatées pour l'email."""
    opportunites = identifier_opportunites()
    return opportunites[:limit] if len(opportunites) >= limit else opportunites

def afficher_top_opportunites(limit=10):
    """Affiche le Top N des opportunités dans la console."""
    opportunites = identifier_opportunites()
    
    if not opportunites:
        print("\n⚠️ Aucune opportunité trouvée.")
        return
    
    print("\n" + "="*100)
    print(f"🏆 TOP {limit} OPPORTUNITÉS (prix/m² le plus bas) - AVEC ÉTAGE")
    print("="*100)
    
    top = opportunites[:limit] if len(opportunites) >= limit else opportunites
    
    for i, p in enumerate(top, 1):
        print(f"\n#{i} {p['titre']} ({p['localisation']})")
        print(f"   📦 Lot: {p['lot_titre']}")
        print(f"   🏷️  Produit: {p['no_produit']}")
        print(f"   📐 Surface: {p['surface']:.0f} m²")
        print(f"   💰 Prix: {p['prix']:,.0f} DH")
        print(f"   📊 Prix/m²: {p['prix_m2']:,.2f} DH/m²")
        print(f"   📈 Moyenne {p['type_bien']} à {p['localisation']} ({p['etage']}): {p['moyenne_groupe']:,.2f} DH/m²")
        print(f"   🎯 Écart: {p['ecart_pourcent']:.1f}%")
        if p['est_opportunite']:
            print("   🔥 **OPPORTUNITÉ !** Moins cher que la moyenne de sa catégorie")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    afficher_top_opportunites(10)