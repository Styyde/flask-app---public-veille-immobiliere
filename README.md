# Veille Immobilière — Maroc

Application de veille sur le marché immobilier marocain : agrégation, filtrage et analyse d'annonces issues d'Al Omrane, Sarouty et Mubawab, avec suivi de l'évolution des prix dans le temps.

Disponible sous deux formes : application de bureau autonome pour Windows, ou service web classique déployable en conteneur.

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Sources de données](#sources-de-données)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Déploiement web](#déploiement-web-docker)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)

## Fonctionnalités

- **Recherche multi-sources** — filtrage combiné par ville, budget, type de bien, surface et prix au m², sur les trois sources ou une seule à la fois.
- **Scraping à la demande** — lancement du scraping par région ou par ville directement depuis l'interface, avec suivi de progression en tâche de fond.
- **Favoris** — mise de côté d'annonces pour suivi ultérieur, toutes sources confondues.
- **Analyse des opportunités** — distribution des prix au m², comparaison par ville, surface vs prix, score d'opportunité par annonce (écart au prix médian du marché comparable).
- **Suivi temporel** — historisation des annonces scrapées et comparaison de l'évolution du prix médian et du stock entre deux périodes, ville par ville et type de bien par type de bien.

## Sources de données

| Source | Contenu | Méthode de collecte |
|---|---|---|
| [Al Omrane](https://www.alomrane.gov.ma) | Projets, lots et produits du groupe public Al Omrane | Automatisation navigateur (nodriver) + parsing HTML |
| [Sarouty](https://www.sarouty.ma) | Annonces résidentielles et commerciales | Appels directs à l'API publique du site |
| [Mubawab](https://www.mubawab.ma) | Annonces résidentielles et terrains | Automatisation navigateur (Playwright) |

## Architecture

- **Backend** : Flask, exposant une API REST consommée par une interface web en HTML/CSS/JavaScript (sans framework front).
- **Base de données** : SQLAlchemy avec migrations Alembic. SQLite en local par défaut — un seul fichier, aucune configuration nécessaire — ou PostgreSQL/MySQL en définissant `DATABASE_URL`, pour un déploiement web à plusieurs instances.
- **Client desktop** : PyQt6 + QtWebEngine. Encapsule l'interface web dans une fenêtre native ; le serveur Flask tourne en arrière-plan dans le même processus, sur un port local.
- **Observabilité** : endpoint `/health` et exposition de métriques Prometheus (`prometheus-flask-exporter`).

## Installation

### Application desktop (utilisateurs finaux, Windows)

1. Récupérer `VeilleImmobiliere-Setup.exe`.
2. Lancer l'installeur — aucun droit administrateur requis.
3. Au premier lancement, une base de données vide est créée dans `%LOCALAPPDATA%\VeilleImmobiliere\`. Lancer un scraping depuis le panneau latéral pour la peupler.

La désinstallation ne supprime pas les données locales (annonces collectées, favoris), afin de permettre une réinstallation ou une mise à jour sans perte.

### Environnement de développement

Prérequis : Python 3.12+.

```bash
git clone https://github.com/Styyde/flask-app---public-veille-immobiliere.git
cd flask-app---public-veille-immobiliere

python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS

pip install -r requirements.txt

# nodriver n'est pas distribué sur PyPI (requis pour le scraping Al Omrane)
pip install git+https://github.com/ultrafunkamsterdam/nodriver.git

# Navigateur headless requis par Playwright (scraping Mubawab)
playwright install chromium

python main.py --mode web        # API + interface sur http://localhost:8000
# ou
python main.py --mode desktop    # fenêtre native (nécessite PyQt6-WebEngine)
```

Les migrations Alembic s'appliquent automatiquement au démarrage. Pour les exécuter manuellement :

```bash
alembic upgrade head
```

## Configuration

Variables d'environnement, toutes optionnelles :

| Variable | Valeur par défaut | Usage |
|---|---|---|
| `DB_PATH` | `./alomrane.db` | Chemin du fichier SQLite (mode desktop ou développement local) |
| `DATABASE_URL` | — | Chaîne de connexion SQLAlchemy complète, prioritaire sur `DB_PATH` (ex. `postgresql+psycopg2://user:pass@host:5432/dbname`) |

## Utilisation

1. **Scraper** — ouvrir le panneau "Outils de scraping" (icône ☰), choisir une région ou une ville par source, lancer la collecte.
2. **Filtrer** — renseigner les critères (ville, budget, type de bien, surface, prix/m²) et lancer la recherche ; les résultats s'affichent par onglet (Al Omrane, Sarouty, Mubawab).
3. **Favoris** — ajouter une annonce depuis son onglet, la retrouver dans l'onglet "Favoris".
4. **Analyse** — le panneau "Analyse des opportunités" se met à jour selon les filtres actifs.
5. **Évolution** — comparer le prix médian et le stock entre deux périodes, ville par ville, depuis l'onglet dédié.


## Structure du projet

```
api/            Routes Flask (REST)
core/           Scrapers (Al Omrane, Sarouty, Mubawab)
database/       Modèles SQLAlchemy, migrations, accès aux données
services/       Logique métier (filtres, favoris, statistiques, tendances)
analytics/      Score d'opportunité
static/         CSS et JavaScript de l'interface
templates/      Page HTML
alembic/        Migrations de schéma
tests/          Suite de tests (pytest)
desktop.py      Point d'entrée du mode desktop (PyQt6)
main.py         Point d'entrée commun (--mode web|desktop)
```

## Tests

```bash
pytest tests/ -v
```
