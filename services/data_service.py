# services/data_service.py
import pandas as pd
import re
from .filter_service import filtrer_produits, filtrer_sarouty, filtrer_mubawab
from utils.text_parser import extraire_etage_depuis_texte


def get_all_listings():
    """Récupère toutes les annonces des trois sources avec prix > 0."""
    produits = filtrer_produits(limit=None)
    sarouty = filtrer_sarouty()
    mubawab = filtrer_mubawab()
    
    all_data = []
    # Al Omrane
    for p in produits:
        surface_str = p.get('surface')
        if isinstance(surface_str, str):
            surf = re.sub(r'[^\d.]', '', surface_str)
            try:
                surface = float(surf)
            except ValueError:
                surface = 0
        else:
            surface = float(surface_str) if surface_str else 0
            
        prix = p.get('prix')
        if prix is None:
            continue
        try:
            prix = float(prix)
        except (TypeError, ValueError):
            continue
        if surface <= 0 or prix <= 0:
            continue
            
        etage = p.get('etage')
        if not etage or etage == 'Inconnu':
            designation = p.get('designation') or ''
            etage = extraire_etage_depuis_texte(designation) if designation else 'Inconnu'
            
        all_data.append({
            'source': 'Al Omrane',
            'titre': p.get('projet'),
            'ville': p.get('ville'),
            'localisation': p.get('ville'),
            'type_bien': p.get('type_bien'),
            'surface': surface,
            'prix': prix,
            'prix_m2': round(prix / surface, 2) if surface > 0 else 0,
            'url': p.get('url_projet'),
            'etage': etage,
            'lot': p.get('lot'),
            'no_produit': p.get('produit'),
            'designation': p.get('designation'),
        })
    
    # Sarouty
    for s in sarouty:
        surface = float(s.get('surface')) if s.get('surface') else 0
        prix = s.get('prix')
        if prix is None:
            continue
        try:
            prix = float(prix)
        except (TypeError, ValueError):
            continue
        if surface <= 0 or prix <= 0:
            continue
            
        all_data.append({
            'source': 'Sarouty',
            'titre': s.get('projet'),
            'ville': s.get('localisation'),
            'localisation': s.get('localisation'),
            'type_bien': s.get('type'),
            'surface': surface,
            'prix': prix,
            'prix_m2': s.get('prix_m2') or round(prix / surface, 2),
            'url': s.get('url_annonce'),
            'etage': None,
            'lot': None,
            'no_produit': None,
            'designation': None,
        })
    
    # Mubawab
    for m in mubawab:
        surface = float(m.get('surface')) if m.get('surface') else 0
        prix = m.get('prix')
        if prix is None:
            continue
        try:
            prix = float(prix)
        except (TypeError, ValueError):
            continue
        if surface <= 0 or prix <= 0:
            continue
            
        all_data.append({
            'source': 'Mubawab',
            'titre': m.get('projet'),
            'ville': m.get('localisation'),
            'localisation': m.get('localisation'),
            'type_bien': m.get('type'),
            'surface': surface,
            'prix': prix,
            'prix_m2': m.get('prix_m2') or round(prix / surface, 2),
            'url': m.get('url_annonce'),
            'etage': None,
            'lot': None,
            'no_produit': None,
            'designation': None,
        })
    
    return all_data