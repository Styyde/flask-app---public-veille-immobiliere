# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# L'image de base est figée au moment de son build par Microsoft : ses paquets
# apt accumulent des CVE corrigés en amont mais jamais réappliqués ici. On
# repart des derniers paquets Jammy avant d'installer le reste, pour que le
# scan Trivy (severity CRITICAL,HIGH, exit-code 1) ne bloque pas sur des CVE
# déjà patchés upstream.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Cache de wheels embarqué par l'outil `virtualenv` de l'image de base, pour
# amorcer de futurs venvs. On utilise le Python système directement dans ce
# conteneur, jamais virtualenv : ce cache est mort et ne fait que traîner des
# CVE (setuptools/wheel/jaraco.context) sans jamais être utilisé.
RUN rm -rf /root/.local/share/virtualenv

# setuptools/wheel/jaraco.context système livrés par l'image de base (via pip)
# sont figés à une version vulnérable (path traversal / RCE via wheel/tar
# malveillants). On les met à jour explicitement.
RUN pip install --no-cache-dir --upgrade "setuptools>=78.1.1" "wheel>=0.46.2" "jaraco.context>=6.1.0"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=api.app

# Installer les dépendances Python (sans nodriver, sans le mode desktop PyQt6 inutile en conteneur)
COPY requirements.txt .
RUN grep -viE '^\s*PyQt6' requirements.txt > requirements.web.txt \
    && pip install --no-cache-dir -r requirements.web.txt

# Installer nodriver depuis GitHub (car absent de PyPI)
RUN pip install --no-cache-dir git+https://github.com/ultrafunkamsterdam/nodriver.git

# Installer Chromium
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 5000

# --preload : importe l'app (donc exécute init_db()/alembic upgrade head) une seule fois
# dans le process maître avant le fork des workers, pour éviter des migrations concurrentes.
CMD ["gunicorn", "--preload", "--workers=4", "--bind=0.0.0.0:5000", "api.app:app"]