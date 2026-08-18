# scheduler_task.py
# Script à exécuter automatiquement toutes les 5 jours
import asyncio
import os
import sys
from datetime import datetime

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.runner import run_full_scraping

from database.db_manager import init_db
from email_sender.sender import envoyer_rapport_email


def log_message(msg):
    """Affiche un message avec timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def main():
    log_message("🚀 Lancement du scraping automatique...")
    
    try:
        # 1. Initialiser la base de données
        init_db()
        
        # 2. Lancer le scraping complet
        log_message("📡 Début du scraping...")
        asyncio.run(run_full_scraping(headless=True, limit_pages=None))
        
        # 3. Envoyer le rapport par email
        log_message("📧 Envoi du rapport...")
        envoyer_rapport_email(limit=10)
        
        log_message("✅ Tâche automatisée terminée avec succès.")
        
    except Exception as e:
        log_message(f"❌ Erreur lors de l'exécution : {e}")
        # Optionnel : envoyer un email d'erreur
        # envoyer_alerte_erreur(str(e))

if __name__ == "__main__":
    main()