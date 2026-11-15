"""Durable orchestration/review records. Scientific content remains in objects/relationships."""
from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base, uid, now


class ResearchRun(Base):
    __tablename__ = 'research_runs'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    kind: Mapped[str]
    status: Mapped[str] = mapped_column(default='queued')
    objective: Mapped[str]
    request_key: Mapped[str]
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    steps_used: Mapped[int] = mapped_column(default=0)
    tool_executions: Mapped[int] = mapped_column(default=0)
    model_requests: Mapped[int] = mapped_column(default=0)
    active_seconds: Mapped[float] = mapped_column(default=0)
    tokens_used: Mapped[int] = mapped_column(default=0)
    lease_owner: Mapped[str | None]
    lease_until: Mapped[str | None]
    error: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint('project_id', 'kind', 'request_key'),)


class ResearchStep(Base):
    __tablename__ = 'research_steps'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id'), index=True)
    number: Mapped[int]
    kind: Mapped[str]
    status: Mapped[str]
    operation_id: Mapped[str | None] = mapped_column(ForeignKey('operations.id'))
    message_id: Mapped[str | None] = mapped_column(ForeignKey('research_messages.id'))
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)
    completed_at: Mapped[str | None]
    __table_args__ = (UniqueConstraint('run_id', 'number'),)


class GraphCorrection(Base):
    __tablename__ = 'graph_corrections'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    kind: Mapped[str]
    object_id: Mapped[str | None] = mapped_column(ForeignKey('objects.id'))
    source_id: Mapped[str | None] = mapped_column(ForeignKey('objects.id'))
    target_id: Mapped[str | None] = mapped_column(ForeignKey('objects.id'))
    relationship_type: Mapped[str | None]
    rationale: Mapped[str]
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    source_revisions: Mapped[dict] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(default='human')
    created_at: Mapped[str] = mapped_column(default=now)
