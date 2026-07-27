# services/type_mapping.py

# Mapping exact des types bruts vers les catégories normalisées
# (pour les types déjà identifiés)
TYPE_MAPPING = {
    # Al Omrane
    "Appartements": "Appartement",
    "Ilot pour promotion immobilière": "Terrain",
    "Ilots pour promotion immobilière": "Terrain",
    "Ilot pour habitat": "Terrain",
    "Lots d'activités commerciales": "Commercial",
    "Lots de terrains pour habitat": "Terrain",
    "Magasins et commerces": "Commercial",
    "Lots d'activités industrielles": "Terrain",
    "Lots de terrains artisanales": "Terrain",
    "Lots d'activités artisanales": "Terrain",
    "Villas": "Villa",
    "Villas semi finis": "Villa",
    "Maisons individuels": "Maison",
    
    # Sarouty (API)
    "Appartement": "Appartement",
    "Immeuble": "Immeuble",
    "Villa": "Villa",
    "Villa Commerciale": "Villa",
    "Terrain": "Terrain",
    "Maison": "Maison",
    "Duplex": "Maison",
    "Triplex": "Maison",
    "Restaurant": "Commercial",
    "Hôtels": "Commercial",
    "Maison D'Hôtes": "Commercial",
    "Riad": "Maison",
    "Magasin": "Commercial",
    "Bureau": "Commercial",
    "Local commercial": "Commercial",   # ajouté
    "Boutique": "Commercial",           # ajouté
    "Office": "Commercial",             # ajouté
    "Hôtel": "Commercial",              # ajouté
    
    # Mubawab
    "Terrain": "Terrain",
    "Villa": "Villa",
    "Riad": "Maison",
    "Maison": "Maison",
    "Appartement": "Appartement",
    "Studio": "Appartement",
    "Duplex": "Maison",
    "Triplex": "Maison",
    "Immeuble": "Immeuble",
    "Local commercial": "Commercial",
    "Magasin": "Commercial",
    "Boutique": "Commercial",
    "Office": "Commercial",
    "Hôtel": "Commercial",
    "Restaurant": "Commercial",
    "Ferme": "Terrain",
}

# Catégories normalisées autorisées (pour l'UI et le filtrage)
NORMALIZED_TYPES = sorted(set(TYPE_MAPPING.values()))


def get_normalized_type(type_brut):
    """
    Retourne la catégorie normalisée pour un type brut donné.
    - D'abord recherche exacte dans TYPE_MAPPING.
    - Sinon, détection par mots-clés (pour les types non listés).
    - Fallback : le type lui-même.
    """
    if not type_brut:
        return None

    # 1. Recherche exacte
    if type_brut in TYPE_MAPPING:
        return TYPE_MAPPING[type_brut]

    # 2. Détection par mots-clés (priorité aux commerciaux)
    lower = type_brut.lower()
    commercial_keywords = [
        'commercial', 'magasin', 'bureau', 'restaurant', 'hôtel', 'hotel',
        'local', 'boutique', 'office', 'café', 'bar', 'pharmacie', 'banque'
    ]
    if any(kw in lower for kw in commercial_keywords):
        # Log optionnel pour signaler les types non mappés
        import logging
        logging.getLogger(__name__).warning(
            f"Type non mappé classé en 'Commercial' : {type_brut}"
        )
        return "Commercial"

    # 3. Fallback : garder le type tel quel
    # (mais on peut aussi le logger)
    import logging
    logging.getLogger(__name__).debug(
        f"Type non reconnu, conservé tel quel : {type_brut}"
    )
    return type_brut


def get_brut_types_for_normalized(normalized):
    """
    Retourne la liste de tous les types bruts correspondant à une catégorie normalisée.
    """
    return [brut for brut, norm in TYPE_MAPPING.items() if norm == normalized]


def get_all_normalized_types():
    """Retourne la liste de toutes les catégories normalisées."""
    return NORMALIZED_TYPES