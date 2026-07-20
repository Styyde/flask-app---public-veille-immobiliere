# test_backend.py
# Test des services de filtrage et statistiques

from services import filtrer_produits, get_filtres_disponibles, get_stats_distribution

def test_filtres():
    print("="*80)
    print("🔍 TEST DES FILTRES DISPONIBLES")
    print("="*80)
    filtres = get_filtres_disponibles()
    for key, values in filtres.items():
        print(f"{key}: {values}")

def test_filtrage():
    print("\n" + "="*80)
    print("🔍 TEST FILTRAGE (R+2 à Mohammedia)")
    print("="*80)
    produits = filtrer_produits(
        etage="R+2",
        localisation="Mohammedia",
        limit=5
    )
    for p in produits:
        print(f"{p['no_produit']} | {p['surface']} | {p['prix']} | {p['prix_m2']} DH/m² | {p['etage']}")

def test_stats():
    print("\n" + "="*80)
    print("📊 TEST STATISTIQUES PAR TYPE DE BIEN")
    print("="*80)
    stats = get_stats_distribution(grouper="type_bien")
    for s in stats:
        print(f"{s['groupe']:30} | nb: {s['nb_produits']:2} | prix/m²: {s['prix_m2_moyen']:8.2f} | surface: {s['surface_moyenne']:6.1f} m²")

if __name__ == "__main__":
    test_filtres()
    test_filtrage()
    test_stats()