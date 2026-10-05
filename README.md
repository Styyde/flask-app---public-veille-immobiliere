# Veille Immobilière — Maroc

Application de veille sur le marché immobilier marocain : collecte automatisée des annonces **Al Omrane**, **Sarouty** et **Mubawab**, recherche multicritère, détection d'opportunités et suivi de l'évolution des prix dans le temps.

Un même code, deux formes de distribution :

- **Application web** conteneurisée, déployée sur AWS (Kubernetes EKS) sous `amandal.kolynois.com` ;
- **Application de bureau Windows** autonome (installeur `.exe`, base SQLite locale).

> Ce dépôt est le **point d'entrée du projet** : il contient le code applicatif et présente l'architecture d'ensemble. Le déploiement et l'infrastructure sont décrits dans deux dépôts dédiés.

## Sommaire

- [Le projet en trois dépôts](#le-projet-en-trois-dépôts)
- [Architecture d'ensemble](#architecture-densemble)
- [Fonctionnalités](#fonctionnalités)
- [Architecture applicative](#architecture-applicative)
- [Chaîne CI/CD](#chaîne-cicd)
- [Sécurité](#sécurité)
- [Haute disponibilité](#haute-disponibilité)
- [Observabilité](#observabilité)
- [Démarrage rapide](#démarrage-rapide)
- [Configuration](#configuration)
- [Tests et qualité](#tests-et-qualité)
- [Limites connues](#limites-connues)

## Le projet en trois dépôts

| Dépôt | Rôle | Contenu | Rythme de modification |
|---|---|---|---|
| **flask-app** *(ce dépôt)* | Application | Code Flask, scrapers, modèle de données, tests, `Dockerfile`, pipeline CI/CD | À chaque évolution du code |
| [**flask-gitops**](https://github.com/Styyde/flask-gitops---public-veille-immobiliere) | Ce qui tourne dans le cluster | Charts Helm (application, supervision, logs), Applications Argo CD | À chaque livraison (commit automatique de la CI) |
| [**aws-infra**](https://github.com/Styyde/aws-infra---public-Veillle-immobiliere) | Infrastructure AWS | Terraform : réseau, EKS, RDS, ECR, IAM, DNS/TLS, bastion | Ponctuellement (`terraform apply` manuel) |

Cette séparation suit trois principes :

- **Un cycle de vie par dépôt** : le code change souvent, la configuration de déploiement à chaque livraison, l'infrastructure rarement.
- **Déploiement en mode *pull*** : la CI n'a aucun accès au cluster. Elle pousse une image dans ECR et un commit dans `flask-gitops` ; c'est Argo CD, depuis l'intérieur du cluster, qui applique le changement.
- **Git comme source de vérité** : l'état de la production se lit dans `flask-gitops`, et un retour arrière se fait par `git revert`, sans reconstruire d'image.

## Architecture d'ensemble

```mermaid
flowchart LR
    dev(["Développeur"])
    user(["Utilisateur"])
    slack(["Slack"])

    subgraph GH["GitHub"]
        app["flask-app<br/>code · Dockerfile · CI"]
        gitops["flask-gitops<br/>Helm · Argo CD"]
        infra["aws-infra<br/>Terraform"]
    end

    subgraph AWS["AWS eu-west-3"]
        ecr[("ECR")]
        alb["ALB HTTPS"]
        rds[("RDS PostgreSQL")]
        sm["Secrets Manager"]
        subgraph EKS["Cluster EKS privé"]
            argo["Argo CD"]
            pods["flask-app<br/>2 à 5 pods"]
            obs["Prometheus · Grafana · Loki"]
        end
    end

    dev -->|push| app
    app -->|"CI : image scannée"| ecr
    app -->|"CI : nouveau tag"| gitops
    argo -->|surveille| gitops
    argo -->|déploie| pods
    ecr -.->|image| pods
    sm -.->|secrets| pods
    user -->|HTTPS| alb
    alb --> pods
    pods --> rds
    obs -.->|alertes| slack
    infra ==>|terraform apply| AWS
```

## Fonctionnalités

- **Recherche multi-sources** : filtres par ville, budget, type de bien, surface et prix au m², sur une source ou les trois.
- **Scraping à la demande** par région ou par ville, lancé depuis l'interface, avec suivi de progression.
- **Favoris** communs aux trois sources.
- **Analyse** : distribution des prix au m², comparaison entre villes, surface vs prix, score d'opportunité par annonce.
- **Évolution** : prix médian au m² et volume d'annonces par ville et par type de bien, entre deux périodes au choix.

## Architecture applicative

### Organisation du code

| Couche | Dossiers | Responsabilité |
|---|---|---|
| Interface | `templates/`, `static/` | Page unique en HTML/CSS/JavaScript natif, graphiques Chart.js ; consomme l'API REST |
| API | `api/` | Routes Flask (JSON), validation des entrées, `/health`, `/metrics` |
| Métier | `services/`, `analytics/` | Filtres multi-sources, normalisation des types de bien, nettoyage des données, score d'opportunité, tendances, tâches de fond |
| Collecte | `core/` | Un scraper par source |
| Données | `database/`, `alembic/` | Modèles SQLAlchemy, sessions, compatibilité multi-SGBD, migrations |

Points d'entrée : `main.py --mode web|desktop` en développement et pour le desktop ; `gunicorn api.app:app` en production.

### Collecte des données

| Source | Technique | Remarque |
|---|---|---|
| [Al Omrane](https://www.alomrane.gov.ma) | Navigateur piloté par `nodriver` (Chrome headless, asynchrone) + BeautifulSoup | Parcours région × type de bien, puis lots et produits de chaque projet |
| [Sarouty](https://www.sarouty.ma) | Appels HTTP directs à l'API JSON du site (`requests`) | Aucun navigateur : collecte rapide et légère |
| [Mubawab](https://www.mubawab.ma) | Playwright (Chromium headless) | Délais aléatoires entre les pages |

Un `POST /api/scraper…` crée une tâche et répond immédiatement ; la collecte s'exécute dans un thread de fond. L'état de la tâche est **enregistré en base** (table `taches`) plutôt qu'en mémoire : n'importe quelle réplique de l'application peut répondre à `GET /api/scraper/status/<task_id>`.

### Données

- **SQLAlchemy 2 et Alembic** : le schéma est versionné, et `init_db()` applique `alembic upgrade head` au démarrage. En production, `gunicorn --preload` exécute cette migration une seule fois par pod, avant de créer les workers.
- **Un seul code pour trois moteurs** : SQLite par défaut (desktop, développement), PostgreSQL en production (RDS) via `DATABASE_URL`, MySQL également supporté. Les écarts entre dialectes (upsert `ON CONFLICT` / `ON DUPLICATE KEY`, arrondis) sont isolés dans `database/compat.py` et `database/expressions.py`.
- **Historisation** : chaque collecte crée un `scrape_run` et, pour chaque annonce, un `listing_snapshot` (prix, surface, prix au m² à cet instant). Le module *Évolution* s'appuie sur ces instantanés.

### Analyse

- Les types de bien, hétérogènes d'une source à l'autre, sont ramenés à des catégories communes (`services/type_mapping.py`) ; des règles de nettoyage écartent les valeurs aberrantes (`services/data_sanitizer.py`).
- **Score d'opportunité** (`analytics/scorer.py`) : le prix au m² de chaque bien est comparé à la moyenne de son groupe *ville × type de bien* ; un écart inférieur à −15 % signale une opportunité.

### API REST

| Domaine | Routes principales |
|---|---|
| Santé et supervision | `GET /health`, `GET /metrics` |
| Recherche | `GET /api/alomrane/projets`, `/api/alomrane/produits`, `/api/sarouty/annonces`, `/api/mubawab/annonces` |
| Analyse | `GET /api/analytics`, `/api/moyennes`, `/api/stats`, `/api/options` |
| Évolution | `GET /api/trends/meta`, `/api/trends/distribution-types`, `/api/trends/comparaison-villes` |
| Scraping | `POST /api/scraper`, `/api/scraper_sarouty`, `/api/scraper_mubawab` ; `GET /api/scraper/status/<task_id>` |
| Favoris | `GET`, `POST`, `DELETE /api/favoris` |

### Version desktop

`desktop.py` affiche l'interface web dans une fenêtre native **PyQt6 / QtWebEngine** ; le serveur Flask tourne dans un thread du même processus, sur `127.0.0.1` et un port libre. L'exécutable est construit par **PyInstaller** (`VeilleImmobiliere.spec`), puis empaqueté avec le navigateur headless de Playwright par **Inno Setup** (`installer.iss`). Base de données et logs sont placés dans `%LOCALAPPDATA%\VeilleImmobiliere\` et conservés lors d'une désinstallation.

## Chaîne CI/CD

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Développeur
    participant CI as GitHub Actions
    participant ECR as Amazon ECR
    participant Git as flask-gitops
    participant Argo as Argo CD
    participant Prod as Production

    Dev->>CI: push sur main
    CI->>CI: tests, lint, scans Trivy, build de l'image
    CI->>ECR: push de l'image taguée par le SHA du commit
    CI->>Git: commit de image.tag = SHA
    Argo->>Git: détecte le nouveau commit
    Argo->>Prod: rolling update (namespace production)
    CI->>Prod: smoke test sur /health jusqu'à image_tag = SHA
```

Le workflow `.github/workflows/ci.yml` comporte trois jobs :

| Job | Déclenchement | Étapes |
|---|---|---|
| `build-test-scan` | push et pull request | pytest, Ruff, Trivy sur les sources, build de l'image, **Trivy sur l'image (bloquant sur les CVE CRITICAL/HIGH corrigeables)**, image conservée en artefact |
| `deploy` | push sur `main` | Rechargement de l'image **déjà scannée** (pas de rebuild), push dans ECR (`:<sha>` et `:latest`) via OIDC, commit du nouveau tag dans `flask-gitops` |
| `smoke-test` | après `deploy` | Interroge `/health` en production jusqu'à ce que `image_tag` corresponde au SHA déployé et que `status` vaille `healthy` (7 minutes au plus) |

L'image est taguée avec le SHA du commit : chaque version en production remonte à son code source, et `/health` expose ce tag.

Secrets GitHub du dépôt : `AWS_ROLE_ARN`, `AWS_REGION`, `ECR_REPOSITORY`, `GITOPS_REPO`, `GITOPS_PUSH_TOKEN`.

## Sécurité

- **Aucun secret dans le code ni dans l'image** : la connexion à la base arrive par `DATABASE_URL`, injectée à l'exécution (en production, un Secret Kubernetes alimenté depuis AWS Secrets Manager). `.gitignore` et `.dockerignore` excluent `.env`, clés, certificats et bases locales.
- **CI sans clé AWS permanente** : la CI obtient par OIDC des identifiants temporaires pour un rôle IAM qui ne peut que pousser dans le dépôt ECR de l'application. L'écriture dans `flask-gitops` passe par un jeton *fine-grained* limité à ce seul dépôt.
- **Chaîne d'approvisionnement** : scan Trivy des sources et de l'image ; image de base mise à jour au build (paquets système, `setuptools`/`wheel` vulnérables) ; scan ECR à chaque push ; l'image déployée est exactement celle qui a été scannée.
- **Accès aux données** uniquement via l'ORM SQLAlchemy (requêtes paramétrées) ; listes blanches pour les régions et villes passées aux scrapers.

La sécurité de la plateforme (réseau privé, IAM, TLS, gestion des secrets) est détaillée dans [aws-infra](https://github.com/Styyde/aws-infra---public-Veillle-immobiliere#sécurité) et [flask-gitops](https://github.com/Styyde/flask-gitops---public-veille-immobiliere#sécurité).

## Haute disponibilité

L'application est **sans état** : annonces, favoris et état des tâches sont en base, aucune session n'est gardée en mémoire. Elle peut donc tourner en plusieurs répliques derrière un load balancer. La disponibilité est traitée à chaque couche :

| Couche | Mécanisme | Défini dans |
|---|---|---|
| Processus | gunicorn, 4 workers par pod | `Dockerfile` (ce dépôt) |
| Pods | 2 répliques minimum, autoscaling jusqu'à 5, PodDisruptionBudget, répartition sur 2 zones, probes sur `/health` | [flask-gitops](https://github.com/Styyde/flask-gitops---public-veille-immobiliere#haute-disponibilité) |
| Nœuds | 2 à 4 nœuds EKS sur 2 zones, Cluster Autoscaler | [aws-infra](https://github.com/Styyde/aws-infra---public-Veillle-immobiliere#haute-disponibilité) |
| Réseau | ALB multi-zones, une NAT Gateway par zone | aws-infra |
| Base de données | RDS PostgreSQL Multi-AZ, sauvegardes conservées 7 jours | aws-infra |

## Observabilité

- `GET /health` teste la base (`SELECT 1`) et renvoie `503` en cas d'échec. Il sert aux probes Kubernetes, au health check de l'ALB et au smoke test.
- `GET /metrics` expose les métriques Prometheus par endpoint (`prometheus-flask-exporter`) : nombre de requêtes, latence, codes HTTP.
- Les logs partent sur la sortie standard (collectée par Loki en production) et dans un fichier tournant (5 × 5 Mo). Les exceptions non interceptées, y compris dans les threads de scraping, sont journalisées. Niveau réglable par `LOG_LEVEL`.

Tableaux de bord et alertes : voir [flask-gitops](https://github.com/Styyde/flask-gitops---public-veille-immobiliere#observabilité).

## Démarrage rapide

**Développement** (Python 3.12) :

```bash
git clone https://github.com/Styyde/flask-app---public-veille-immobiliere.git
cd flask-app---public-veille-immobiliere
python -m venv venv
venv\Scripts\activate                       # Linux/macOS : source venv/bin/activate
pip install -r requirements.txt
pip install git+https://github.com/ultrafunkamsterdam/nodriver.git   # même version qu'en CI et dans l'image
playwright install chromium

python main.py --mode web        # http://localhost:8000 (serveur de développement)
python main.py --mode desktop    # fenêtre native
```

**Conteneur** :

```bash
docker compose up --build        # http://localhost:5000, base SQLite persistée dans ./data
```

**Desktop (utilisateurs finaux)** : lancer `VeilleImmobiliere-Setup.exe` (aucun droit administrateur requis), puis remplir la base depuis le panneau de scraping. Pour reconstruire l'installeur : `pyinstaller VeilleImmobiliere.spec`, puis compiler `installer.iss` avec Inno Setup 6.

## Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `DATABASE_URL` | — | Chaîne de connexion SQLAlchemy (ex. `postgresql+psycopg2://user:pass@host:5432/db`), prioritaire sur `DB_PATH` |
| `DB_PATH` | `./alomrane.db` | Fichier SQLite (desktop, développement) |
| `LOG_LEVEL` | `INFO` | Niveau de journalisation |
| `IMAGE_TAG` | `unknown` | Version exposée par `/health`, injectée par le chart Helm |

Les périmètres de collecte (régions, villes, URLs, nombre de pages) se règlent dans `config.py`.

## Tests et qualité

```bash
pytest tests/ -v      # base SQLite temporaire, isolée de la base de travail
ruff check .
```

Les tests couvrent les routes de l'API, les services de filtrage, la couche de données et `/health`, y compris en cas de panne de la base.


