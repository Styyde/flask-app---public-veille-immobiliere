# database/session.py
from contextlib import contextmanager

from database.engine import get_sessionmaker


@contextmanager
def session_scope():
    """Une Session par appel, meme granularite que l'ancien
    connect()/commit()/close() par fonction : commit si le bloc reussit,
    rollback puis re-raise sinon, close dans tous les cas."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
