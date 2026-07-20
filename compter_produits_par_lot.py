# compter_produits_par_lot.py
import sqlite3
from config import DB_PATH

def compter_produits_par_lot():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n📊 Nombre de produits par lot (projets récemment ajoutés)")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            p.titre,
            l.lot_titre,
            COUNT(pr.id) as nb_produits
        FROM lots l
        JOIN projets p ON p.id = l.projet_id
        LEFT JOIN produits pr ON pr.lot_id = l.id
        WHERE p.date_extraction >= datetime('now', '-1 hour')
        GROUP BY l.id
        ORDER BY nb_produits DESC
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        for titre, lot, nb in rows:
            print(f"🏗️ {titre}")
            print(f"   📦 {lot} : {nb} produit(s)")
            print()
    else:
        print("⚠️ Aucun lot trouvé pour les projets récents.")
    
    conn.close()

if __name__ == "__main__":
    compter_produits_par_lot()