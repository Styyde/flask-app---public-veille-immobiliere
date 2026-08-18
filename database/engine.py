# database/engine.py
"""Creation paresseuse du moteur SQLAlchemy.

config.DB_PATH peut etre mute apres l'import de ce module (voir
tests/conftest.py, qui pointe la base vers un fichier temporaire avant le
premier appel reel a init_db()). Le moteur ne doit donc jamais etre construit
au niveau module : get_engine() ne lit config.DB_PATH/DATABASE_URL qu'au
premier appel et met le resultat en cache.

Version desktop (SQLite) : aucune variable a definir, DB_PATH suffit.
Version web (Postgres/MySQL) : definir DATABASE_URL, ex.
  postgresql+psycopg2://user:pass@host:5432/dbname
  mysql+pymysql://user:pass@host:3306/dbname
"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import config

_engine = None
_sessionmaker = None


def get_database_url():
    return os.environ.get('DATABASE_URL') or f"sqlite:///{config.DB_PATH}"


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url())

        if _engine.dialect.name == 'sqlite':
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.close()

    return _engine


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(bind=get_engine())
    return _sessionmaker


def reset_engine():
    """Reinitialise le moteur/sessionmaker mis en cache.

    Utile si config.DB_PATH change apres qu'un premier appel a deja cree le
    moteur (ex: tests qui changent de base de donnees en cours de session).
    """
    global _engine, _sessionmaker
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _sessionmaker = None
