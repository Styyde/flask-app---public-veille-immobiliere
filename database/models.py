# database/models.py
"""Modeles SQLAlchemy declaratifs, miroir exact du schema historique cree par
l'ancien init_db() (voir alembic/versions/0001_baseline.py pour la creation)."""
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Projet(Base):
    __tablename__ = 'projets'
    __table_args__ = (
        Index('idx_url', 'url'),
        Index('idx_localisation', 'localisation'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, unique=True, nullable=False)
    region = Column(Text)
    type_bien = Column(Text)
    titre = Column(Text)
    localisation = Column(Text)
    titre_foncier = Column(Text)
    description = Column(Text)
    date_extraction = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    lots = relationship('Lot', back_populates='projet', cascade='all, delete-orphan', order_by='Lot.id')


class Lot(Base):
    __tablename__ = 'lots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    projet_id = Column(Integer, ForeignKey('projets.id', ondelete='CASCADE'), nullable=False)
    lot_titre = Column(Text)
    nb_unites = Column(Text)
    prix_min = Column(Text)
    prix_max = Column(Text)

    projet = relationship('Projet', back_populates='lots')
    produits = relationship('Produit', back_populates='lot', cascade='all, delete-orphan', order_by='Produit.id')


class Produit(Base):
    __tablename__ = 'produits'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lot_id = Column(Integer, ForeignKey('lots.id', ondelete='CASCADE'), nullable=False)
    no_produit = Column(Text)
    surface = Column(Text)
    prix = Column(Text)

    lot = relationship('Lot', back_populates='produits')


class AnnonceSarouty(Base):
    __tablename__ = 'annonces_sarouty'
    __table_args__ = (
        Index('idx_sarouty_ville', 'ville'),
        Index('idx_sarouty_type', 'type_bien'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, unique=True, nullable=False)
    url_annonce = Column(Text)
    titre = Column(Text)
    description = Column(Text)
    prix = Column(Integer)
    superficie = Column(Integer)
    chambres = Column(Integer)
    salles_de_bain = Column(Integer)
    type_bien = Column(Text)
    quartier = Column(Text)
    ville = Column(Text)
    date_extraction = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class AnnonceMubawab(Base):
    __tablename__ = 'annonces_mubawab'
    __table_args__ = (
        Index('idx_mubawab_ville', 'ville'),
        Index('idx_mubawab_type', 'type_bien'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    url_annonce = Column(Text, unique=True, nullable=False)
    titre = Column(Text)
    description = Column(Text)
    prix = Column(Integer)
    superficie = Column(Integer)
    type_bien = Column(Text)
    localisation = Column(Text)
    ville = Column(Text)
    region = Column(Text)
    date_extraction = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Favori(Base):
    """Forme finale (post-migration legacy id_annonce -> annonce_id, voir
    alembic/versions/0002_favoris_legacy_cleanup.py)."""
    __tablename__ = 'favoris'
    __table_args__ = (
        UniqueConstraint('source', 'annonce_id'),
        Index('idx_favoris_source', 'source'),
        Index('idx_favoris_date', 'date_ajout'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    annonce_id = Column(Text, nullable=False)
    url = Column(Text)
    titre = Column(Text)
    localisation = Column(Text)
    type_bien = Column(Text)
    surface = Column(Text)
    prix = Column(Text)
    prix_m2 = Column(Float)
    date_ajout = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Tache(Base):
    __tablename__ = 'taches'

    id = Column(String, primary_key=True)
    source = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    message = Column(Text)
    result = Column(Text)
    date_creation = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    date_fin = Column(DateTime)


class ScrapeRun(Base):
    __tablename__ = 'scrape_runs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)
    started_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    finished_at = Column(DateTime)
    statut = Column(Text, server_default='en_cours')
    nb_annonces = Column(Integer, server_default='0')

    snapshots = relationship('ListingSnapshot', back_populates='scrape_run')


class ListingSnapshot(Base):
    __tablename__ = 'listing_snapshots'
    __table_args__ = (
        Index('idx_snapshots_date', 'scraped_at'),
        Index('idx_snapshots_group', 'type_bien', 'ville'),
        Index('idx_snapshots_key', 'source', 'listing_key'),
        Index('idx_snapshots_run', 'scrape_run_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scrape_run_id = Column(Integer, ForeignKey('scrape_runs.id'))
    source = Column(Text, nullable=False)
    listing_key = Column(Text, nullable=False)
    type_bien = Column(Text)
    ville = Column(Text)
    quartier = Column(Text)
    surface = Column(Float)
    prix = Column(Float)
    prix_m2 = Column(Float)
    scraped_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    scrape_run = relationship('ScrapeRun', back_populates='snapshots')
