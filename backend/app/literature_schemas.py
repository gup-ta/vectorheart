"""Typed external records and grounded review contracts; no model-assigned citations."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

PROPOSAL_ACTION = 'propose_literature_relationship'
Classification = Literal['supports', 'challenges', 'qualifies', 'alternative_explanation', 'method', 'background', 'insufficient_information', 'cites']


class Paper(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    title: str = Field(min_length=1, max_length=2000)
    authors: list[str] = Field(default_factory=list, max_length=100)
    year: int | None = None
    publication_date: str | None = None
    venue: str = ''
    identifiers: dict[str, str]
    publisher_url: str | None = None
    open_access_url: str | None = None
    abstract: str = Field(default='', max_length=16000)
    publication_type: str = ''
    provider: Literal['OpenAlex', 'Europe PMC', 'Crossref']
    retrieved_at: str
    provider_url: str
    references: list[str] = Field(default_factory=list, max_length=50)
    retraction_status: str = 'unknown'
    corrections: list[str] = Field(default_factory=list, max_length=20)
    license: str | None = None
    access_level: Literal['metadata', 'abstract']
    bibliographic_status: Literal['provider_verified'] = 'provider_verified'


class QueryPlanItem(BaseModel):
    strategy: Literal['confirmatory', 'contradictory', 'alternative', 'methodological', 'foundational']
    query: str
    rationale: str


class SearchPlan(BaseModel):
    queries: list[QueryPlanItem]
    limitations: list[str]


class Finding(BaseModel):
    snapshot_id: str
    target_object_id: str | None
    classification: Classification
    claim: str
    rationale: str
    # Exact anchor is validated, but only offsets/short excerpts are persisted.
    passage: str
    limitations: list[str]
    method_notes: list[str]
    missing_information: list[str]


class LiteratureAnalysis(BaseModel):
    summary: str
    findings: list[Finding]
    disagreements: list[str]
    limitations: list[str]


class LiteratureAssociation(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    source_id: str
    snapshot_id: str
    target_object_id: str | None
    classification: Classification
    claim: str = Field(min_length=1, max_length=6000)
    rationale: str = Field(min_length=1, max_length=4000)
    access_level: Literal['metadata', 'abstract']
    passage_start: int = Field(ge=0)
    passage_end: int = Field(ge=0)
    limitations: list[str] = Field(max_length=12)
    method_notes: list[str] = Field(max_length=12)
    missing_information: list[str] = Field(max_length=12)


class LiteratureRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['ground', 'challenge', 'explore'] = 'ground'
    object_ids: list[str] = Field(default_factory=list, max_length=8)
    relationship_id: str | None = None
    query: str = Field(default='', max_length=500)
    use_model: bool = True
    idempotency_key: str = Field(min_length=8, max_length=100)


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identifier: str = Field(min_length=1, max_length=250)


class LiteratureToolRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool: Literal['literature.search', 'literature.resolve_identifier', 'literature.inspect_source', 'literature.find_related']
    query: str | None
    identifier: str | None
    source_id: str | None
    rationale: str = Field(min_length=1, max_length=2000)
