"""Small Gemini-compatible transport; application checks retain scientific authority."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.intelligence_schemas import RelationshipType


class SourcePassage(BaseModel):
    object_id: str
    revision: int
    excerpt: str


class ExtractedNode(BaseModel):
    key: str
    existing_object_id: str | None
    object_type: Literal['note', 'question', 'hypothesis', 'observation', 'concept', 'prediction']
    title: str
    body: str
    rationale: str
    uncertainty: Literal['explicit', 'inferred', 'uncertain']
    sources: list[SourcePassage]


class ExtractedEdge(BaseModel):
    source: str
    target: str
    relationship_type: RelationshipType
    rationale: str
    uncertainty: Literal['explicit', 'inferred', 'uncertain']
    sources: list[SourcePassage]


class GraphExtraction(BaseModel):
    summary: str
    nodes: list[ExtractedNode]
    edges: list[ExtractedEdge]
    limitations: list[str]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class JournalInput(Input):
    id: str | None = None
    title: str = Field(default='', max_length=120)
    body: str = Field(default='', max_length=1000000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    linked_object_ids: list[str] = Field(default_factory=list, max_length=30)


class JournalPatch(JournalInput):
    base_revision: int = Field(ge=1)


class StartRun(Input):
    kind: Literal['graph', 'accelerate', 'investigate']
    objective: str = Field(default='', max_length=10000)
    idempotency_key: str = Field(min_length=8, max_length=100)
    max_steps: int = Field(default=3, ge=1, le=5)


class CorrectionInput(Input):
    correction_id: str | None = Field(default=None, min_length=1, max_length=200)
    kind: Literal['add_relationship', 'remove_relationship', 'edit_object']
    object_id: str | None = None
    source_id: str | None = None
    target_id: str | None = None
    relationship_id: str | None = None
    relationship_type: RelationshipType = 'related_to'
    rationale: str = Field(default='', max_length=4000)
    base_revision: int | None = None
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=10000)
    object_type: Literal['note', 'question', 'hypothesis', 'observation', 'concept', 'prediction'] | None = None


class Review(Input):
    rationale: str = Field(default='', max_length=4000)
