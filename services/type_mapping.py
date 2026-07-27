# services/type_mapping.py

# Mapping des types bruts vers les catégories normalisées
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
    "Villa Commerciale": "Commercial",   # Ajusté vers Commercial
    "Terrain": "Terrain",
    "Maison": "Maison",
    "Duplex": "Appartement",            # Ajusté vers Appartement
    "Triplex": "Appartement",           # Ajusté vers Appartement
    "Restaurant": "Commercial",
    "Hôtels": "Commercial",
    "Maison D'Hôtes": "Commercial",
    "Riad": "Maison",
    "Magasin": "Commercial",
    "Bureau": "Commercial",

    # Mubawab
    "Studio": "Appartement",
    "Local commercial": "Commercial",
    "Boutique": "Commercial",
    "Office": "Commercial",
    "Hôtel": "Commercial",
    "Ferme": "Terrain",
}

# Catégories normalisées uniques autorisées
NORMALIZED_TYPES = sorted(set(TYPE_MAPPING.values()))


def _clean_str(val: str) -> str:
    """Nettoie les espaces insécables (\xa0) et les espaces aux extrémités."""
    if not val:
        return ""
    return val.replace("\xa0", " ").strip()


def get_normalized_type(type_brut: str) -> str | None:
    """Retourne la catégorie normalisée pour un type brut donné."""
    if not type_brut:
        return None

    cleaned = _clean_str(type_brut)
    return TYPE_MAPPING.get(cleaned, cleaned)  # Fallback : retourne le type nettoyé


def get_brut_types_for_normalized(normalized: str) -> list[str]:
    """Retourne la liste de tous les types bruts correspondant à une catégorie normalisée."""
    cleaned_norm = _clean_str(normalized)
    return [brut for brut, norm in TYPE_MAPPING.items() if norm == cleaned_norm]


def get_all_normalized_types() -> list[str]:
    """Retourne la liste de toutes les catégories normalisées."""
    return NORMALIZED_TYPES