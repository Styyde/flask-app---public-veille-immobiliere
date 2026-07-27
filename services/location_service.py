# services/location_service.py
import sqlite3
from config import DB_PATH

def get_location_hierarchy():
    """
    Extrait dynamiquement la hiérarchie des régions/villes et quartiers 
    à partir des 3 tables (projets, annonces_sarouty, annonces_mubawab).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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

    # 1. Al Omrane (region -> localisation)
    try:
        cursor.execute("SELECT region, localisation FROM projets WHERE region IS NOT NULL AND localisation IS NOT NULL")
        for region, loc in cursor.fetchall():
            add_to_hierarchy(region, loc)
    except sqlite3.OperationalError:
        pass

    # 2. Mubawab (region -> ville, ville -> localisation)
    try:
        cursor.execute("SELECT region, ville, localisation FROM annonces_mubawab")
        for region, ville, loc in cursor.fetchall():
            add_to_hierarchy(region, ville)
            if loc and ville and loc != ville:
                # loc is often 'Quartier' or 'Quartier à Ville', but we cleaned 'à Ville' already
                add_to_hierarchy(ville, loc)
    except sqlite3.OperationalError:
        pass

    # 3. Sarouty (ville -> quartier)
    try:
        cursor.execute("SELECT ville, quartier FROM annonces_sarouty WHERE ville IS NOT NULL AND quartier IS NOT NULL")
        for ville, quartier in cursor.fetchall():
            add_to_hierarchy(ville, quartier)
    except sqlite3.OperationalError:
        pass

    conn.close()

    # Convert sets to sorted lists
    result = {k: sorted(list(v)) for k, v in hierarchy.items() if v}
    return result

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
