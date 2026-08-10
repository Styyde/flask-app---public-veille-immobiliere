# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=api.app

# Installer les dépendances Python (sans nodriver pour l'instant)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer nodriver depuis GitHub (car absent de PyPI)
RUN pip install --no-cache-dir git+https://github.com/ultrafunkamsterdam/nodriver.git

# Installer Chromium
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "api.app:app"]