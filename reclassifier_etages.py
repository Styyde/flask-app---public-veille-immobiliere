# reclassifier_etages.py
# Script FORCE pour réappliquer la nouvelle logique d'extraction des étages
# à TOUS les produits (écrase les anciennes classifications).

import sqlite3
from config import DB_PATH
from utils.text_parser import extraire_etage_depuis_texte

def reclassifier_tous_les_etages():
    """
    Parcourt TOUS les produits de la base.
    Ré-extrait l'étage depuis la designation ou le titre du lot
    avec la nouvelle logique (priorité aux R+).
    Écrase les anciennes valeurs.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Récupérer tous les produits avec leur designation et le titre du lot
    cursor.execute("""
        SELECT p.id, p.designation, l.lot_titre
        FROM produits p
        JOIN lots l ON l.id = p.lot_id
    """)
    
    produits = cursor.fetchall()
    total = len(produits)
    count_updated = 0
    count_unchanged = 0
    
    for prod_id, designation, lot_titre in produits:
        # Priorité à la designation, sinon au titre du lot
        texte_source = designation if designation and designation.strip() != "" else lot_titre
        
        # Nouvel étage avec la logique améliorée (R+ prioritaire)
        nouvel_etage = extraire_etage_depuis_texte(texte_source)
        
        # Mise à jour forcée (même si l'étage est identique, on le remet)
        cursor.execute("UPDATE produits SET etage = ? WHERE id = ?", (nouvel_etage, prod_id))
        count_updated += 1
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print("🔄 RECLASSIFICATION FORCÉE DES ÉTAGES (Nouvelle logique)")
    print("="*60)
    print(f"✅ {count_updated} produits reclassifiés avec la nouvelle logique.")
    print("="*60)
    print("\n💡 Nouvelle logique : Priorité aux R+ (R+1, R+2...) avant RDC.")
    print("   Exemple: 'Lot promotionnel r+2 rdc commercial' -> R+2 (et plus RDC)")

if __name__ == "__main__":
    reclassifier_tous_les_etages()