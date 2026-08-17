# database/compat.py
"""Upsert (INSERT ... ON CONFLICT) portable entre SQLite, PostgreSQL et MySQL.

SQLite et PostgreSQL partagent la meme API SQLAlchemy (on_conflict_do_update/
on_conflict_do_nothing avec index_elements), mais MySQL n'a pas de clause
ON CONFLICT : il utilise ON DUPLICATE KEY UPDATE, avec une API differente
(pas d'index_elements, le conflit est detecte via la contrainte unique/PK).
Ces deux helpers cachent cette difference aux appelants de db_manager.py.
"""
from database.engine import get_engine


def upsert_update(model, values, index_elements, update_columns=None):
    """INSERT ... ON CONFLICT/DUPLICATE KEY UPDATE (met a jour les lignes existantes)."""
    dialect = get_engine().dialect.name
    update_columns = update_columns if update_columns is not None else [
        k for k in values if k not in index_elements
    ]
    set_values = {k: values[k] for k in update_columns}

    if dialect == 'mysql':
        from sqlalchemy.dialects.mysql import insert as mysql_insert
        stmt = mysql_insert(model).values(**values)
        return stmt.on_duplicate_key_update(**set_values)

    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(model).values(**values)
        return stmt.on_conflict_do_update(index_elements=index_elements, set_=set_values)

    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    stmt = sqlite_insert(model).values(**values)
    return stmt.on_conflict_do_update(index_elements=index_elements, set_=set_values)


def upsert_ignore(model, values, index_elements):
    """INSERT IGNORE / ON CONFLICT DO NOTHING (ignore si la ligne existe deja)."""
    dialect = get_engine().dialect.name

    if dialect == 'mysql':
        from sqlalchemy.dialects.mysql import insert as mysql_insert
        stmt = mysql_insert(model).values(**values)
        return stmt.prefix_with('IGNORE')

    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(model).values(**values)
        return stmt.on_conflict_do_nothing(index_elements=index_elements)

    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    stmt = sqlite_insert(model).values(**values)
    return stmt.on_conflict_do_nothing(index_elements=index_elements)
