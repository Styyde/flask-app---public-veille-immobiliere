# diagnostic.py
import sqlite3
from config import DB_PATH
from services.type_mapping import get_normalized_type

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 60)
print("🔍 DIAGNOSTIC DES DONNÉES COMMERCIALES")
print("=" * 60)

# 1. Al Omrane
print("\n📊 AL OMRANE")
query_ao = """
SELECT 
    p.localisation,
    COUNT(pr.id) AS nb_total,
    SUM(CASE WHEN CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL) > 0 
              AND CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL) > 0 THEN 1 ELSE 0 END) AS nb_valides,
    MIN(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL)) AS prix_min,
    MAX(CAST(REPLACE(REPLACE(pr.prix, 'DH', ''), ' ', '') AS REAL)) AS prix_max,
    MIN(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL)) AS surf_min,
    MAX(CAST(REPLACE(REPLACE(pr.surface, 'm²', ''), ' ', '') AS REAL)) AS surf_max
FROM produits pr
JOIN lots l ON l.id = pr.lot_id
JOIN projets p ON p.id = l.projet_id
WHERE p.type_bien IN ('Lots d''activités commerciales', 'Magasins et commerces')
GROUP BY p.localisation
"""
cursor.execute(query_ao)
rows_ao = cursor.fetchall()

if rows_ao:
    print("Biens commerciaux trouvés par ville :")
    for row in rows_ao:
        loc, total, valides, pmin, pmax, smin, smax = row
        print(f"  {loc} : {total} biens, {valides} valides, prix [{pmin}–{pmax}], surface [{smin}–{smax}]")
else:
    print("❌ Aucun bien commercial trouvé dans Al Omrane.")

# 2. Sarouty
print("\n📊 SAROUTY")
cursor.execute("""
SELECT 
    ville,
    COUNT(*) AS total,
    SUM(CASE WHEN prix > 0 AND superficie > 0 THEN 1 ELSE 0 END) AS valides,
    MIN(prix) AS prix_min,
    MAX(prix) AS prix_max,
    MIN(superficie) AS surf_min,
    MAX(superficie) AS surf_max
FROM annonces_sarouty
WHERE type_bien IN ('Restaurant', 'Hôtels', 'Maison D''Hôtes', 'Magasin', 'Bureau', 'Local commercial', 'Boutique', 'Office', 'Hôtel')
GROUP BY ville
""")
rows_sar = cursor.fetchall()

if rows_sar:
    for row in rows_sar:
        ville, total, valides, pmin, pmax, smin, smax = row
        print(f"  {ville} : {total} biens, {valides} valides, prix [{pmin}–{pmax}], surface [{smin}–{smax}]")
else:
    print("❌ Aucun bien commercial trouvé dans Sarouty.")

# 3. Mubawab
print("\n📊 MUBAWAB")
cursor.execute("""
SELECT 
    ville,
    COUNT(*) AS total,
    SUM(CASE WHEN prix > 0 AND superficie > 0 THEN 1 ELSE 0 END) AS valides,
    MIN(prix) AS prix_min,
    MAX(prix) AS prix_max,
    MIN(superficie) AS surf_min,
    MAX(superficie) AS surf_max
FROM annonces_mubawab
WHERE type_bien IN ('Local commercial', 'Magasin', 'Boutique', 'Office', 'Hôtel', 'Restaurant')
GROUP BY ville
""")
rows_mub = cursor.fetchall()

if rows_mub:
    for row in rows_mub:
        ville, total, valides, pmin, pmax, smin, smax = row
        print(f"  {ville} : {total} biens, {valides} valides, prix [{pmin}–{pmax}], surface [{smin}–{smax}]")
else:
    print("❌ Aucun bien commercial trouvé dans Mubawab.")

# 4. Vérification des types exacts dans projets
print("\n📌 TYPES EXACTS DANS 'projets' (Al Omrane)")
cursor.execute("SELECT DISTINCT type_bien FROM projets ORDER BY type_bien")
for (t,) in cursor.fetchall():
    norm = get_normalized_type(t)
    print(f"  {t} -> {norm}")

conn.close()