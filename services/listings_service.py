# services/listings_service.py
import re

from utils.text_parser import extraire_etage_depuis_texte

from .filter_service import filtrer_mubawab, filtrer_produits, filtrer_sarouty


def _clean_number(text):
    """
    Extrait un nombre depuis une chaîne avec unités (ex: '720 000 DH' -> 720000.0)
    ou '120 m²' -> 120.0.
    """
    if not text:
        return 0.0
    cleaned = re.sub(r'[^\d.,]', '', str(text).replace(' ', ''))
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def get_all_listings():
    """Récupère toutes les annonces des trois sources avec prix > 0."""
    produits = filtrer_produits(limit=None)
    sarouty = filtrer_sarouty()
    mubawab = filtrer_mubawab()
    
    all_data = []

    # ---- Al Omrane ----
    for p in produits:
        surface = _clean_number(p.get('surface'))
        prix = _clean_number(p.get('prix'))
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

    # ---- Sarouty ----
    for s in sarouty:
        surface = _clean_number(s.get('surface'))
        prix = _clean_number(s.get('prix'))
        if surface <= 0 or prix <= 0:
            continue
        prix_m2 = s.get('prix_m2')
        if not prix_m2:
            prix_m2 = round(prix / surface, 2) if surface > 0 else 0

        all_data.append({
            'source': 'Sarouty',
            'titre': s.get('projet'),
            'ville': s.get('localisation'),
            'localisation': s.get('localisation'),
            'type_bien': s.get('type'),
            'surface': surface,
            'prix': prix,
            'prix_m2': prix_m2,
            'url': s.get('url_annonce'),
            'etage': None,
            'lot': None,
            'no_produit': None,
            'designation': None,
        })

    # ---- Mubawab ----
    for m in mubawab:
        surface = _clean_number(m.get('surface'))
        prix = _clean_number(m.get('prix'))
        if surface <= 0 or prix <= 0:
            continue
        prix_m2 = m.get('prix_m2')
        if not prix_m2:
            prix_m2 = round(prix / surface, 2) if surface > 0 else 0

        all_data.append({
            'source': 'Mubawab',
            'titre': m.get('projet'),
            'ville': m.get('localisation'),
            'localisation': m.get('localisation'),
            'type_bien': m.get('type'),
            'surface': surface,
            'prix': prix,
            'prix_m2': prix_m2,
            'url': m.get('url_annonce'),
            'etage': None,
            'lot': None,
            'no_produit': None,
            'designation': None,
        })

    return all_data