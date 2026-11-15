import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, event, String, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
from dotenv import load_dotenv
load_dotenv(ROOT / 'backend/.env', override=False)
DATABASE = Path(os.environ.get('KERNEL_DB_PATH', ROOT / '.vectorheart/kernel.sqlite3')).resolve()
DATABASE.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine('sqlite:///' + str(DATABASE), connect_args={'check_same_thread': False, 'timeout': 30})
@event.listens_for(engine, 'connect')
def configure(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')
Session = sessionmaker(engine, expire_on_commit=False)
def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str]
    description: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]
    settings: Mapped[dict] = mapped_column(JSON)
    question: Mapped[str] = mapped_column(default='')
    last_visited_view: Mapped[str | None]
    schema_version: Mapped[int] = mapped_column(default=1)
    sequence: Mapped[int] = mapped_column(default=0)
class Object(Base):
    __tablename__ = 'objects'
    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    object_type: Mapped[str]
    title: Mapped[str]
    body: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]
    current_revision: Mapped[int] = mapped_column(default=1)
    provenance_type: Mapped[str] = mapped_column(default='human')
    scientific_metadata: Mapped[dict] = mapped_column('metadata', JSON, default=dict)
    schema_version: Mapped[int] = mapped_column(default=1)
    deleted: Mapped[bool] = mapped_column(default=False)
class Revision(Base):
    __tablename__ = 'revisions'
    revision_id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    object_id: Mapped[str] = mapped_column(ForeignKey('objects.id'), index=True)
    revision_number: Mapped[int]
    title_snapshot: Mapped[str]
    body_snapshot: Mapped[str]
    metadata_snapshot: Mapped[dict] = mapped_column(JSON)
    previous_revision_id: Mapped[str | None]
    actor_type: Mapped[str]
    created_at: Mapped[str]
    reason: Mapped[str]
    __table_args__ = (UniqueConstraint('object_id', 'revision_number'),)
class Relationship(Base):
    __tablename__ = 'relationships'
    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    source_object_id: Mapped[str] = mapped_column(ForeignKey('objects.id'))
    target_object_id: Mapped[str] = mapped_column(ForeignKey('objects.id'))
    relationship_type: Mapped[str]
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey('objects.id'))
    created_at: Mapped[str]
    details: Mapped[dict] = mapped_column('metadata', JSON, default=dict)
class Placement(Base):
    __tablename__ = 'placements'
    object_id: Mapped[str] = mapped_column(ForeignKey('objects.id'), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    x: Mapped[float]
    y: Mapped[float]
class Operation(Base):
    __tablename__ = 'operations'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    kind: Mapped[str]
    action_type: Mapped[str]
    target_object_ids: Mapped[list] = mapped_column(JSON)
    proposed_by: Mapped[str] = mapped_column(default='human')
    proposal_payload: Mapped[dict] = mapped_column(JSON)
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]
    status: Mapped[str] = mapped_column(default='draft')
    approval_record: Mapped[dict | None] = mapped_column(JSON)
    execution_id: Mapped[str | None]
    schema_version: Mapped[int] = mapped_column(default=1)
class Specification(Base):
    __tablename__ = 'specifications'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'))
    operation_id: Mapped[str] = mapped_column(ForeignKey('operations.id'), unique=True)
    adapter_id: Mapped[str]
    adapter_version: Mapped[str]
    parameters: Mapped[dict] = mapped_column(JSON)
    predicted_outcomes: Mapped[dict] = mapped_column(JSON)
    measurement_plan: Mapped[str]
    validation_plan: Mapped[list] = mapped_column(JSON)
    execution_limits: Mapped[dict] = mapped_column(JSON)
    environment_type: Mapped[str]
    created_at: Mapped[str]
    approved_at: Mapped[str | None]
    specification_hash: Mapped[str]
    schema_version: Mapped[int] = mapped_column(default=1)
class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    experiment_specification_id: Mapped[str] = mapped_column(ForeignKey('specifications.id'))
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    status: Mapped[str]
    started_at: Mapped[str]
    completed_at: Mapped[str | None]
    actual_parameters: Mapped[dict] = mapped_column(JSON)
    environment_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    code_version: Mapped[str]
    random_seed: Mapped[int]
    measured_outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_references: Mapped[list] = mapped_column(JSON, default=list)
    validation_results: Mapped[dict] = mapped_column(JSON, default=dict)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int] = mapped_column(default=0)
class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(ForeignKey('objects.id'), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'))
    source_run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'))
    source_type: Mapped[str]
    target_hypothesis_ids: Mapped[list] = mapped_column(JSON)
    measured_results: Mapped[dict] = mapped_column(JSON)
    interpretation: Mapped[str]
    verification_status: Mapped[str]
    limitations: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[str]
    provenance: Mapped[dict] = mapped_column(JSON)
class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'))
    project_sequence_number: Mapped[int]
    event_type: Mapped[str]
    actor_type: Mapped[str]
    actor_identifier: Mapped[str] = mapped_column(default='local-user')
    source_operation_id: Mapped[str | None] = mapped_column(ForeignKey('operations.id'))
    affected_object_ids: Mapped[list] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[str]
    schema_version: Mapped[int] = mapped_column(default=1)
    __table_args__ = (UniqueConstraint('project_id', 'project_sequence_number'),)
