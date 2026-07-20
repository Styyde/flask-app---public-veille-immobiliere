# services/analysis_service.py
from .filter_service import filtrer_produits
from .stats_service import (
    get_distribution_prix_m2,
    get_distribution_etages,
    get_prix_m2_par_ville_et_etage
)

def analyser_opportunites(filtres=None):
    """
    Retourne un rapport complet d'analyse basé sur les filtres.
    Combine filtrage + statistiques.
    """
    if filtres is None:
        filtres = {}
    
    # 1. Récupérer les produits filtrés
    produits = filtrer_produits(**filtres)
    
    # 2. Statistiques globales sur les produits filtrés
    if not produits:
        return {
            "produits": [],
            "stats": {
                "total": 0,
                "prix_m2_moyen": 0,
                "prix_m2_min": 0,
                "prix_m2_max": 0,
                "distribution_etages": []
            }
        }
    
    prix_m2_list = [p['prix_m2'] for p in produits if p.get('prix_m2')]
    prix_list = [p['prix'] for p in produits if p.get('prix')]
    
    # 3. Statistiques avancées par catégorie
    stats = {
        "total": len(produits),
        "prix_m2_moyen": round(sum(prix_m2_list) / len(prix_m2_list), 2) if prix_m2_list else 0,
        "prix_m2_min": min(prix_m2_list) if prix_m2_list else 0,
        "prix_m2_max": max(prix_m2_list) if prix_m2_list else 0,
        "prix_moyen": round(sum(prix_list) / len(prix_list), 2) if prix_list else 0,
        "prix_min": min(prix_list) if prix_list else 0,
        "prix_max": max(prix_list) if prix_list else 0,
        "distribution_etages": get_distribution_etages(),
        "distribution_types": get_distribution_prix_m2(group_by="type_bien"),
        "distribution_villes": get_distribution_prix_m2(group_by="localisation")
    }
    
    return {
        "produits": produits,
        "stats": stats
    }