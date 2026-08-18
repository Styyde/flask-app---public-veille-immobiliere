"""baseline

Revision ID: a759e0536c7a
Revises:
Create Date: 2026-08-11 05:29:59.971154

Cree l'integralite du schema (tables + index) tel que defini par
database/models.py. Utilise checkfirst=True partout plutot que
op.create_table()/op.create_index() : cette migration doit etre un no-op sur
les bases existantes (alomrane.db, data/alomrane.db) que l'ancien init_db()
avait deja creees en SQL brut, et une creation complete sur une base neuve.
"""
from collections.abc import Sequence

from alembic import op
from database.models import Base

# revision identifiers, used by Alembic.
revision: str = 'a759e0536c7a'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Ordre respectant les dependances de FK (parents avant enfants).
_TABLE_ORDER = [
    'projets', 'lots', 'produits',
    'annonces_sarouty', 'annonces_mubawab',
    'favoris', 'taches',
    'scrape_runs', 'listing_snapshots',
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in _TABLE_ORDER:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(_TABLE_ORDER):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
