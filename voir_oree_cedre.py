# voir_oree_cedre.py
import sqlite3
from config import DB_PATH

def voir_oree_cedre():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("🏗️ PROJETS LOTISSEMENT OREE & CEDRE TRANCHE 2")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            p.id,
            p.titre,
            p.type_bien,
            p.localisation,
            p.badge,
            l.lot_titre,
            l.nb_unites,
            COUNT(pr.id) as nb_produits,
            GROUP_CONCAT(pr.no_produit, ', ') as produits
        FROM projets p
        JOIN lots l ON l.projet_id = p.id
        LEFT JOIN produits pr ON pr.lot_id = l.id
        WHERE p.titre IN ('LOTISSEMENT OREE', 'CEDRE TRANCHE 2')
        GROUP BY l.id
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"\n🏗️ {row[1]} (ID: {row[0]})")
            print(f"   🏷️  Type: {row[2]}")
            print(f"   📍 Localisation: {row[3]}")
            print(f"   🏅 Badge: {row[4]}")
            print(f"\n   📦 {row[5]}")
            print(f"      📊 Unités: {row[6]}")
            print(f"      📝 Produits extraits: {row[7]}")
            if row[7] > 5:
                print("      ✅ PAGINATION OK ! (plus de 5 produits)")
            else:
                print("      ⚠️ Pagination limitée à 5 produits")
            if row[8]:
                print(f"      🏷️  N° produits: {row[8]}")
    else:
        print("⚠️ Projets non trouvés dans la base.")
    
    conn.close()

if __name__ == "__main__":
    voir_oree_cedre()