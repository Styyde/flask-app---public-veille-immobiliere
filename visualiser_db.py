# visualiser_db.py
import sqlite3
import os
from config import DB_PATH

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def afficher_menu():
    print("\n" + "="*80)
    print("📋 MENU DE VISUALISATION DE LA BASE AL OMRANE")
    print("="*80)
    print("    1. Tableau de bord global")
    print("    2. Liste détaillée des projets")
    print("    3. Liste des produits (avec filtres)")
    print("    4. Statistiques par ville et type")
    print("    5. Produits avec étage/désignation")
    print("    6. Exporter en CSV (rapport complet)")
    print("    7. Tout afficher")
    print("    8. Quitter")
    print("="*80)

def tableau_de_bord():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 TABLEAU DE BORD GLOBAL")
    print("="*80)
    
    # Statistiques générales
    cursor.execute("SELECT COUNT(*) FROM projets")
    nb_projets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM lots")
    nb_lots = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM produits")
    nb_produits = cursor.fetchone()[0]
    
    print(f"📌 Statistiques générales :")
    print(f"   • Projets : {nb_projets}")
    print(f"   • Lots : {nb_lots}")
    print(f"   • Produits : {nb_produits}")
    
    cursor.execute("SELECT DISTINCT localisation FROM projets")
    villes = [row[0] for row in cursor.fetchall()]
    print(f"   • Villes distinctes : {len(villes)}")
    
    cursor.execute("SELECT MAX(date_extraction) FROM projets")
    last_date = cursor.fetchone()[0]
    print(f"   • Dernière extraction : {last_date}")
    
    # Répartition par badge
    print("\n🏅 Répartition par badge")
    print("-"*60)
    cursor.execute("SELECT badge, COUNT(*) FROM projets GROUP BY badge")
    for badge, count in cursor.fetchall():
        print(f"   • {badge}: {count} projet(s)")
    
    # Répartition par type de bien
    print("\n🏷️ Répartition par type de bien (top 5)")
    print("-"*60)
    cursor.execute("""
        SELECT type_bien, COUNT(*) 
        FROM projets 
        GROUP BY type_bien 
        ORDER BY COUNT(*) DESC 
        LIMIT 5
    """)
    for type_bien, count in cursor.fetchall():
        print(f"   • {type_bien}: {count} projet(s)")
    
    # Répartition des étages
    print("\n🏢 Répartition des étages")
    print("-"*60)
    cursor.execute("""
        SELECT 
            CASE 
                WHEN etage IS NULL OR etage = '' THEN 'Inconnu'
                WHEN etage LIKE '%RDC%' THEN 'RDC'
                WHEN etage LIKE '%R+1%' THEN 'R+1'
                WHEN etage LIKE '%R+2%' THEN 'R+2'
                WHEN etage LIKE '%R+3%' THEN 'R+3'
                WHEN etage LIKE '%R+4%' THEN 'R+4'
                ELSE etage
            END as etage_norm,
            COUNT(*) 
        FROM produits 
        GROUP BY etage_norm
        ORDER BY COUNT(*) DESC
    """)
    for etage, count in cursor.fetchall():
        print(f"   • {etage}: {count} produit(s)")
    
    # Prix/m² moyen par type de bien
    print("\n💰 Prix/m² moyen par type de bien")
    print("-"*60)
    cursor.execute("""
        SELECT 
            p.type_bien,
            COUNT(pr.id) as nb,
            ROUND(AVG(
                CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) / 
                CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL)
            ), 2) as prix_m2_moyen
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) > 0
        GROUP BY p.type_bien
        ORDER BY prix_m2_moyen
    """)
    for type_bien, nb, prix_m2 in cursor.fetchall():
        print(f"   • {type_bien:<30} | {nb:>3} prod | {prix_m2:>10,.2f} DH/m²")
    
    conn.close()
    input("\nAppuyez sur Entrée pour continuer...")

def liste_detaille_projets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📋 LISTE DÉTAILLÉE DES PROJETS")
    print("="*80)
    
    cursor.execute("""
        SELECT id, titre, localisation, region, type_bien, badge, date_extraction
        FROM projets
        ORDER BY date_extraction DESC
    """)
    
    projets = cursor.fetchall()
    for p in projets:
        p_id, titre, localisation, region, type_bien, badge, date = p
        print(f"\n🏗️ {titre}")
        print(f"   📍 {localisation} ({region})")
        print(f"   🏷️  {type_bien} | 🏅 {badge}")
        print(f"   📅 {date}")
        
        # Lots associés
        cursor.execute("""
            SELECT id, lot_titre, nb_unites, prix_min, prix_max
            FROM lots
            WHERE projet_id = ?
        """, (p_id,))
        lots = cursor.fetchall()
        if lots:
            print(f"   📦 Lots ({len(lots)}) :")
            for lot in lots:
                lot_id, lot_titre, nb_unites, prix_min, prix_max = lot
                print(f"      • {lot_titre}")
                print(f"        Unités: {nb_unites}")
                print(f"        Prix: {prix_min} - {prix_max}")
                
                # Produits (5 premiers)
                cursor.execute("""
                    SELECT no_produit, surface, prix, etage, designation
                    FROM produits
                    WHERE lot_id = ?
                    LIMIT 5
                """, (lot_id,))
                produits = cursor.fetchall()
                if produits:
                    print(f"        Produits :")
                    for prod in produits:
                        no, surface, prix, etage, designation = prod
                        etage_str = f" | Étage: {etage}" if etage else ""
                        desig_str = f" | {designation}" if designation else ""
                        print(f"          • {no} | {surface} | {prix}{etage_str}{desig_str}")
                cursor.execute("SELECT COUNT(*) FROM produits WHERE lot_id = ?", (lot_id,))
                total_prod = cursor.fetchone()[0]
                if total_prod > 5:
                    print(f"          ... et {total_prod - 5} autres produits")
        else:
            print("   Aucun lot")
    
    conn.close()
    input("\nAppuyez sur Entrée pour continuer...")

def liste_produits_filtres():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📋 LISTE DES PRODUITS")
    print("="*80)
    
    print("Filtres disponibles :")
    print("  [1] Tous les produits")
    print("  [2] Produits avec étage renseigné")
    print("  [3] Produits avec désignation")
    print("  [4] Produits par type de bien")
    
    choix = input("\nVotre choix (1-4) : ")
    
    query = """
        SELECT 
            p.titre,
            p.localisation,
            l.lot_titre,
            pr.no_produit,
            pr.surface,
            pr.prix,
            pr.etage,
            pr.designation,
            ROUND(
                CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) / 
                CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL),
                2
            ) as prix_m2
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE 1=1
    """
    
    if choix == "2":
        query += " AND pr.etage IS NOT NULL AND pr.etage != ''"
    elif choix == "3":
        query += " AND pr.designation IS NOT NULL AND pr.designation != ''"
    elif choix == "4":
        cursor.execute("SELECT DISTINCT type_bien FROM projets ORDER BY type_bien")
        types = [row[0] for row in cursor.fetchall()]
        print("\nTypes disponibles :")
        for i, t in enumerate(types, 1):
            print(f"  {i}. {t}")
        choix_type = input("Choisissez un type : ")
        try:
            type_choisi = types[int(choix_type) - 1]
            query += " AND p.type_bien = ?"
            cursor.execute(query, (type_choisi,))
        except:
            print("Choix invalide.")
            conn.close()
            return
    else:
        cursor.execute(query)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("⚠️ Aucun produit trouvé.")
        conn.close()
        input("Appuyez sur Entrée...")
        return
    
    print(f"\n📊 {len(rows)} produit(s) trouvé(s)")
    print("-"*100)
    print(f"{'Projet':<25} {'Ville':<15} {'Lot':<25} {'N°':<8} {'Surface':<10} {'Prix/m²':<12}")
    print("-"*100)
    
    for row in rows[:30]:  # Limite à 30 pour lisibilité
        titre, ville, lot, no, surface, prix, etage, designation, prix_m2 = row
        desig = f" ({designation})" if designation and designation != 'None' else ""
        print(f"{titre[:24]:<25} {ville[:14]:<15} {lot[:24]:<25} {no:<8} {surface:<10} {prix_m2:<12.2f}")
    
    if len(rows) > 30:
        print(f"\n... et {len(rows) - 30} autres produits")
    
    conn.close()
    input("\nAppuyez sur Entrée pour continuer...")

def produits_avec_etage():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("🏢 PRODUITS AVEC ÉTAGE ET DÉSIGNATION")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            p.titre,
            p.localisation,
            l.lot_titre,
            pr.no_produit,
            pr.surface,
            pr.prix,
            pr.etage,
            pr.designation
        FROM produits pr
        JOIN lots l ON l.id = pr.lot_id
        JOIN projets p ON p.id = l.projet_id
        WHERE pr.etage IS NOT NULL AND pr.etage != ''
        ORDER BY p.titre, pr.etage
        LIMIT 50
    """)
    
    rows = cursor.fetchall()
    if not rows:
        print("⚠️ Aucun produit avec étage renseigné.")
    else:
        for row in rows:
            print(f"\n🏗️ {row[0]} ({row[1]})")
            print(f"   📦 {row[2]}")
            print(f"   🏷️  Produit {row[3]} | Surface: {row[4]} | Prix: {row[5]}")
            print(f"   🏢 Étage: {row[6]}")
            if row[7]:
                print(f"   📝 Désignation: {row[7]}")
    
    conn.close()
    input("\nAppuyez sur Entrée pour continuer...")

def exporter_csv():
    import csv
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n📁 Export en cours...")
    
    with open('rapport_complet.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Projet', 'Localisation', 'Region', 'Type de bien', 'Badge', 'Date extraction',
            'Lot', 'Unités', 'Prix min', 'Prix max',
            'N° Produit', 'Surface', 'Prix', 'Étage', 'Désignation', 'Prix/m²'
        ])
        
        cursor.execute("""
            SELECT 
                p.titre,
                p.localisation,
                p.region,
                p.type_bien,
                p.badge,
                p.date_extraction,
                l.lot_titre,
                l.nb_unites,
                l.prix_min,
                l.prix_max,
                pr.no_produit,
                pr.surface,
                pr.prix,
                pr.etage,
                pr.designation,
                ROUND(
                    CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) / 
                    CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL),
                    2
                ) as prix_m2
            FROM projets p
            LEFT JOIN lots l ON l.projet_id = p.id
            LEFT JOIN produits pr ON pr.lot_id = l.id
            ORDER BY p.date_extraction DESC, p.id, l.id
        """)
        
        for row in cursor.fetchall():
            writer.writerow(row)
    
    print("✅ Rapport exporté vers 'rapport_complet.csv'")
    print("📊 Ouvrez-le avec Excel pour analyse approfondie.")
    conn.close()
    input("Appuyez sur Entrée pour continuer...")

def tout_afficher():
    tableau_de_bord()
    liste_detaille_projets()
    produits_avec_etage()
    exporter_csv()

def main():
    while True:
        clear_screen()
        afficher_menu()
        
        choix = input("Votre choix (1-8) : ")
        
        if choix == "1":
            tableau_de_bord()
        elif choix == "2":
            liste_detaille_projets()
        elif choix == "3":
            liste_produits_filtres()
        elif choix == "4":
            stats_par_ville()  # À ajouter si besoin
        elif choix == "5":
            produits_avec_etage()
        elif choix == "6":
            exporter_csv()
        elif choix == "7":
            tout_afficher()
        elif choix == "8":
            print("👋 Au revoir !")
            break
        else:
            print("❌ Choix invalide.")

if __name__ == "__main__":
    main()