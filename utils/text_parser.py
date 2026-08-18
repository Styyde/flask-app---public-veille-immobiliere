# utils/text_parser.py
# Module d'extraction et de nettoyage de texte
# Version améliorée : priorité aux R+ (étages supérieurs) avant RDC

import re
import unicodedata


def nettoyer_accents(texte):
    """
    Supprime les accents d'une chaîne de caractères (ex: É -> E, ô -> o).
    Utile pour normaliser les textes avant recherche de motifs.
    """
    if not texte:
        return ""
    return "".join(
        c for c in unicodedata.normalize('NFD', texte)
        if unicodedata.category(c) != 'Mn'
    )

def extraire_etage_depuis_texte(texte):
    """
    Extrait l'information d'étage depuis une chaîne de caractères (designation ou titre de lot).
    PRIORITÉ : R+ (R+1, R+2, etc.) > RDC > Villa/Maison > Inconnu.
    Cela permet de gérer correctement les cas comme "R+2 RDC Commercial" -> R+2.
    """
    if not texte or not isinstance(texte, str):
        return "Inconnu"
    
    # Nettoyage et mise en majuscules
    txt = nettoyer_accents(texte.upper())
    
    # 1. RECHERCHE PRIORITAIRE : R+ / R- / R suivi d'un nombre (ex: R+2, R-1, R2, R 3, R+12)
    # On fait cette recherche AVANT le RDC pour ne pas se faire piéger par
    # des phrases comme "R+2 avec RDC commercial" si l'étage du lot est le R+2.
    match_etage = re.search(r"\bR\s*[+-]?\s*(\d+)\b", txt)
    if match_etage:
        numero_etage = match_etage.group(1)
        return f"R+{numero_etage}"
    
    # 2. Recherche des RDC / Rez-de-chaussée (si aucun R+ trouvé)
    if "RDC" in txt or "REZ" in txt:
        return "RDC"
    
    # 3. Détection des villas et maisons (pas d'étage standard)
    if "VILLA" in txt:
        return "Villa"
    if "MAISON" in txt:
        return "Maison"
    
    # 4. Cas où le texte contient "Etage 4" ou "Niveau 2" sans le R+
    match_chiffre_seul = re.search(r"(?:ETAGE|NIVEAU)\s*(\d+)", txt)
    if match_chiffre_seul:
        return f"R+{match_chiffre_seul.group(1)}"
    
    # 5. Cas par défaut
    return "Inconnu"