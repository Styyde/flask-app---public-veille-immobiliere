# logging_config.py
"""Configuration centrale du logging applicatif.

A appeler une seule fois, au point d'entree du process (voir api/app.py pour
le mode web, servi par gunicorn). Idempotent : un second appel ne duplique
pas les handlers. Niveau ajustable via la variable d'environnement LOG_LEVEL
(INFO par defaut), sans toucher au code.
"""
import logging
import os

_configured = False


def configure_logging():
    global _configured
    if _configured:
        return
    level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )
    _configured = True
