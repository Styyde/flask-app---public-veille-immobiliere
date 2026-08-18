"""favoris legacy cleanup

Revision ID: b108b85eae0b
Revises: a759e0536c7a
Create Date: 2026-08-11 05:30:01.234156

Porte vers Alembic la migration ad-hoc qui vivait auparavant dans
db_manager.py::init_db() (PRAGMA table_info + ALTER TABLE executes a chaque
demarrage) : renomme l'ancienne colonne id_annonce en annonce_id en
preservant les donnees, puis ajoute les colonnes qui manqueraient encore.
Idempotente : no-op sur une base deja a jour (nouvelle base creee par
0001_baseline, ou base ayant deja subi cette migration en code avant ce
cutover vers Alembic).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b108b85eae0b'
down_revision: str | Sequence[str] | None = 'a759e0536c7a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS_TO_ADD = {
    'annonce_id': 'TEXT NOT NULL DEFAULT ""',
    'url': 'TEXT',
    'titre': 'TEXT',
    'localisation': 'TEXT',
    'type_bien': 'TEXT',
    'surface': 'TEXT',
    'prix': 'TEXT',
    'prix_m2': 'REAL',
    'date_ajout': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('favoris')}

    if 'id_annonce' in existing_columns:
        op.execute("""
            CREATE TABLE IF NOT EXISTS favoris_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                annonce_id TEXT NOT NULL,
                url TEXT,
                titre TEXT,
                localisation TEXT,
                type_bien TEXT,
                surface TEXT,
                prix TEXT,
                prix_m2 REAL,
                date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, annonce_id)
            )
        """)
        op.execute("""
            INSERT INTO favoris_new
                (source, annonce_id, url, titre, localisation, type_bien, surface, prix, prix_m2, date_ajout)
            SELECT
                source,
                COALESCE(NULLIF(annonce_id, ''), id_annonce),
                url, titre, localisation, type_bien, surface, prix, prix_m2, date_ajout
            FROM favoris
            WHERE COALESCE(NULLIF(annonce_id, ''), id_annonce) IS NOT NULL
              AND COALESCE(NULLIF(annonce_id, ''), id_annonce) != ''
        """)
        op.execute("DROP TABLE favoris")
        op.execute("ALTER TABLE favoris_new RENAME TO favoris")
        inspector = sa.inspect(bind)
        existing_columns = {col['name'] for col in inspector.get_columns('favoris')}

    for col, col_type in _COLUMNS_TO_ADD.items():
        if col not in existing_columns:
            op.execute(f"ALTER TABLE favoris ADD COLUMN {col} {col_type}")

    op.execute("CREATE INDEX IF NOT EXISTS idx_favoris_source ON favoris (source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_favoris_date ON favoris (date_ajout)")


def downgrade() -> None:
    # Migration de nettoyage de donnees legacy : pas de chemin de retour
    # significatif (on ne va pas re-perdre annonce_id pour id_annonce).
    pass
