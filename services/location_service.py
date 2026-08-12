# services/location_service.py
from sqlalchemy import select

from database.models import AnnonceMubawab, AnnonceSarouty, Projet
from database.session import session_scope

def get_location_hierarchy():
    """
    Extrait dynamiquement la hiérarchie des régions/villes et quartiers
    à partir des 3 tables (projets, annonces_sarouty, annonces_mubawab).
    """
    hierarchy = {}

    def add_to_hierarchy(parent, child):
        if not parent or not child:
            return
        parent = parent.strip()
        child = child.strip()
        if parent == child:
            return
        if parent not in hierarchy:
            hierarchy[parent] = set()
        hierarchy[parent].add(child)

    with session_scope() as session:
        # 1. Al Omrane (region -> localisation)
        rows = session.execute(
            select(Projet.region, Projet.localisation)
            .where(Projet.region.isnot(None), Projet.localisation.isnot(None))
        )
        for region, loc in rows:
            add_to_hierarchy(region, loc)

        # 2. Mubawab (region -> ville, ville -> localisation)
        rows = session.execute(
            select(AnnonceMubawab.region, AnnonceMubawab.ville, AnnonceMubawab.localisation)
        )
        for region, ville, loc in rows:
            add_to_hierarchy(region, ville)
            if loc and ville and loc != ville:
                # loc is often 'Quartier' or 'Quartier à Ville', but we cleaned 'à Ville' already
                add_to_hierarchy(ville, loc)

        # 3. Sarouty (ville -> quartier)
        rows = session.execute(
            select(AnnonceSarouty.ville, AnnonceSarouty.quartier)
            .where(AnnonceSarouty.ville.isnot(None), AnnonceSarouty.quartier.isnot(None))
        )
        for ville, quartier in rows:
            add_to_hierarchy(ville, quartier)

    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in hierarchy.items() if v}

def get_all_sublocations_for(location_name):
    """
    Retourne de manière récursive toutes les sous-localisations pour un nom donné.
    Par exemple, si on demande 'Rabat-Salé-Kénitra', ça retourne 'Rabat', 'Kénitra', 'Agdal', 'Souissi', etc.
    Si on demande 'Rabat', ça retourne 'Agdal', 'Souissi', etc.
    """
    if not location_name:
        return []

    hierarchy = get_location_hierarchy()
    sub_locations = set()

    def traverse(node):
        if node in hierarchy:
            for child in hierarchy[node]:
                if child not in sub_locations:
                    sub_locations.add(child)
                    traverse(child)

    traverse(location_name)
    return list(sub_locations)
