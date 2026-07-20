# migrer_etages.py
# Script one-shot pour mettre à jour tous les produits existants
# avec l'étage détecté depuis leur designation ou le titre du lot.

import sqlite3
from config import DB_PATH
from utils.text_parser import extraire_etage_depuis_texte

def migrer_etages():
    """
    Parcourt tous les produits de la base.
    Si l'étage est manquant ou vide, il tente de l'extraire
    depuis la designation ou le titre du lot.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Récupérer tous les produits avec leur designation, le titre du lot et l'étage actuel
    cursor.execute("""
        SELECT p.id, p.designation, l.lot_titre, p.etage
        FROM produits p
        JOIN lots l ON l.id = p.lot_id
    """)
    
    produits = cursor.fetchall()
    count_updated = 0
    count_already_done = 0
    count_unknown = 0
    
    for prod_id, designation, lot_titre, etage_actuel in produits:
        # Si l'étage est déjà renseigné et non vide, on le conserve
        # (mais on pourrait aussi le forcer pour corriger les anciennes erreurs)
        # Pour le moment, on ne met à jour que les NULL/vides.
        if etage_actuel and etage_actuel.strip() != "":
            count_already_done += 1
            continue
        
        # Priorité à la designation, sinon au titre du lot
        texte_source = designation if designation and designation.strip() != "" else lot_titre
        nouvel_etage = extraire_etage_depuis_texte(texte_source)
        
        if nouvel_etage != "Inconnu":
            cursor.execute("UPDATE produits SET etage = ? WHERE id = ?", (nouvel_etage, prod_id))
            count_updated += 1
        else:
            count_unknown += 1
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("📊 RÉSULTAT DE LA MIGRATION DES ÉTAGES (VERSION 2)")
    print("="*50)
    print(f"✅ Produits mis à jour avec un étage détecté : {count_updated}")
    print(f"ℹ️  Produits qui avaient déjà un étage : {count_already_done}")
    print(f"⚠️  Produits sans indication d'étage (restent 'Inconnu') : {count_unknown}")
    print("="*50)

if __name__ == "__main__":
    migrer_etages()