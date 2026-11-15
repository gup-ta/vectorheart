"""Bibliographic identities/snapshots complement, never replace, the scientific graph."""
from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base, uid, now


class ScholarlySource(Base):
    __tablename__ = 'scholarly_sources'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    title: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)


class SourceIdentifier(Base):
    __tablename__ = 'source_identifiers'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(ForeignKey('scholarly_sources.id'), index=True)
    kind: Mapped[str]
    value: Mapped[str]
    __table_args__ = (UniqueConstraint('kind', 'value'),)


class SourceSnapshot(Base):
    __tablename__ = 'source_snapshots'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(ForeignKey('scholarly_sources.id'), index=True)
    provider: Mapped[str]
    retrieved_at: Mapped[str]
    content_hash: Mapped[str]
    record: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint('source_id', 'provider', 'content_hash'),)


class LiteratureHit(Base):
    __tablename__ = 'literature_hits'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id'), index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey('source_snapshots.id'))
    query: Mapped[str]
    strategy: Mapped[str]
    rank: Mapped[int]
    created_at: Mapped[str] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint('run_id', 'snapshot_id', 'query'),)


class ProjectSource(Base):
    __tablename__ = 'project_sources'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('scholarly_sources.id'))
    object_id: Mapped[str] = mapped_column(ForeignKey('objects.id'))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey('source_snapshots.id'))
    __table_args__ = (UniqueConstraint('project_id', 'source_id'),)


class LiteratureCache(Base):
    __tablename__ = 'literature_cache'
    key: Mapped[str] = mapped_column(primary_key=True)
    provider: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)
    expires_at: Mapped[str]
