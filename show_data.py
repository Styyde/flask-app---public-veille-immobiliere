# show_data.py
import sqlite3
from config import DB_PATH

def show_all_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 DONNÉES DE LA BASE AL OMRANE")
    print("="*80)
    
    # 1. Afficher tous les projets
    print("\n🏗️ PROJETS :")
    print("-" * 80)
    cursor.execute("""
        SELECT id, titre, localisation, region, type_bien, badge, date_extraction 
        FROM projets 
        ORDER BY date_extraction DESC
    """)
    projets = cursor.fetchall()
    
    if projets:
        for p in projets:
            print(f"ID: {p[0]} | {p[1]}")
            print(f"   📍 {p[2]} ({p[3]}) | 🏷️ {p[4]} | 🏅 {p[5]}")
            print(f"   📅 {p[6]}")
            print()
    else:
        print("⚠️ Aucun projet trouvé dans la base.")
    
    # 2. Compter par région
    print("\n📊 STATISTIQUES :")
    print("-" * 40)
    cursor.execute("SELECT region, COUNT(*) FROM projets GROUP BY region")
    for region, count in cursor.fetchall():
        print(f"   {region}: {count} projet(s)")
    
    # 3. Compter par type
    print("\n🏷️ PAR TYPE :")
    print("-" * 40)
    cursor.execute("SELECT type_bien, COUNT(*) FROM projets GROUP BY type_bien")
    for type_bien, count in cursor.fetchall():
        print(f"   {type_bien}: {count} projet(s)")
    
    # 4. Compter par badge
    print("\n🏅 PAR BADGE :")
    print("-" * 40)
    cursor.execute("SELECT badge, COUNT(*) FROM projets GROUP BY badge")
    for badge, count in cursor.fetchall():
        print(f"   {badge}: {count} projet(s)")
    
    # 5. Afficher un exemple détaillé
    print("\n" + "="*80)
    print("📋 EXEMPLE DÉTAILLÉ (1er projet) :")
    print("="*80)
    
    cursor.execute("SELECT * FROM projets LIMIT 1")
    projet = cursor.fetchone()
    if projet:
        # Récupérer les colonnes
        columns = [description[0] for description in cursor.description]
        print("\n🏗️ Projet:")
        for i, col in enumerate(columns):
            print(f"   {col}: {projet[i]}")
        
        # Récupérer les lots
        projet_id = projet[0]
        cursor.execute("SELECT * FROM lots WHERE projet_id = ?", (projet_id,))
        lots = cursor.fetchall()
        if lots:
            print(f"\n📦 Lots ({len(lots)}):")
            for lot in lots:
                print(f"   • {lot[2]}")
                print(f"     Unités: {lot[3]}")
                print(f"     Prix: {lot[4]} - {lot[5]}")
                
                # Récupérer les produits
                lot_id = lot[0]
                cursor.execute("SELECT * FROM produits WHERE lot_id = ?", (lot_id,))
                produits = cursor.fetchall()
                if produits:
                    print("     Produits:")
                    for prod in produits[:3]:  # Affiche les 3 premiers
                        print(f"       • {prod[2]} | Surface: {prod[3]} | Prix: {prod[4]}")
    
    conn.close()

def show_lots_with_prices():
    """Affiche les lots avec leurs prix formatés."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("💰 LOTS AVEC PRIX")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            p.titre,
            p.localisation,
            l.lot_titre,
            l.prix_min,
            l.prix_max,
            COUNT(pr.id) as nb_produits
        FROM projets p
        JOIN lots l ON p.id = l.projet_id
        LEFT JOIN produits pr ON l.id = pr.lot_id
        GROUP BY l.id
        ORDER BY p.date_extraction DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"\n🏗️ {row[0]}")
            print(f"   📍 {row[1]}")
            print(f"   📦 {row[2]}")
            print(f"   💰 Prix: {row[3]} - {row[4]}")
            print(f"   📝 {row[5]} produit(s)")
    else:
        print("⚠️ Aucun lot trouvé.")
    
    conn.close()

if __name__ == "__main__":
    show_all_data()
    show_lots_with_prices()