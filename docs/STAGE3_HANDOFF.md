# VECTORHEART — Stage 3 technical handoff

> Historical baseline before Stage 3 implementation. Stage 3 has since been added;
> see [STAGE3.md](STAGE3.md) for its actual code, migration 0003, endpoints,
> startup, recovery rules and limitations. Future-design sections below preserve
> the original implementation brief rather than claiming those APIs already existed.

Prepared from repository inspection on 2026-11-15. This document describes the
working baseline and recommends the **next product stage**. “Stage 3” below means
the journal/Research Graph/AI Accelerate direction requested for the next session;
it does not mean that the earlier Scientific Kernel “Phase 3” is unimplemented.

**Do not rebuild the app or replace the kernel. Do not implement future sections
merely because they are described here. Preserve existing research data.**

## 1. Snapshot and quick orientation

- Inspected branch: `main`; baseline commit: `8de59c1`
  (`Gemini-API Integration and Successful Use Case for Analysis and Recommendation`).
- Working tree was clean before this handoff was added. Recheck `git status` in a
  fresh session; do not overwrite later work or commit/push without authorization.
- Frontend: Next.js App Router, React/TypeScript, Tailwind 4, Lucide,
  `@xyflow/react` 12. No permanent sidebar. Warm paper palette:
  background `#FAF8F4`, ink `#302A24`, accent `#A2674B`, borders `#DED6CB`.
- Backend: Python/FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite, NumPy.
- Scientific authority is the Python kernel/SQLite. React state is an optimistic
  projection; localStorage research data is a legacy backup/import source.
- Source migration head **and configured database's applied head are `0002`**.
  The database was inspected through a read-only SQLite connection; research
  contents and secrets were not copied into this document.
- Existing functionality includes projects, structured Notebook entries, manually
  arranged Canvas, scientific operations, real causal simulation, evidence,
  immutable content revisions, event trail, real model adapters, conversations,
  and human-reviewed proposals.
- Not implemented: primary free-form journal, automatic reconstruction of the
  researcher's understanding, graph-correction rationale workflow, AI Accelerate,
  or durable/resumable autonomous investigations.

Start reading in this order:

1. `src/components/workspace-provider.tsx`, `src/lib/kernel-repository.ts`.
2. `backend/app/db.py`, `backend/app/main.py`.
3. `backend/app/intelligence_schemas.py`, `intelligence.py`, `proposal_correction.py`.
4. `research_context.py`, `model_providers.py`, `gemini_transport.py`.
5. `src/components/research-canvas.tsx`, `research-intelligence.tsx`.
6. Tests and the future architecture/acceptance sections below.

## 2. Existing architecture and source map

```text
Browser: WorkspaceProvider optimistic project state / mutation queue
  ├─ Notebook / ResearchEntry / ResearchActions
  ├─ Canvas (React Flow; same objects and scientific relationships)
  └─ ResearchIntelligence drawer (separate conversation/review state)
       ↓ same-origin HTTP
Next /api/kernel/[...path] proxy
       ↓ fixed server-configured loopback destination
FastAPI app.main:app
  ├─ project/object/relationship/placement APIs and scientific services
  ├─ operation registry → explicit approval → trusted subprocess → validation
  └─ intelligence router → context builder → model adapter → proposal validation
       ↓ SQLAlchemy transactions
SQLite: scientific records + revisions/events + conversation/proposal records
```

| Source | Concrete responsibility |
| --- | --- |
| `src/app/layout.tsx` | Global styles, React Flow styles, WorkspaceProvider, workspace preferences control |
| `src/app/page.tsx` | Project list/search/create/rename/delete; creation routes to settings |
| `src/app/projects/[id]/page.tsx` | Entry route via ProjectWorkspace |
| `src/app/projects/[id]/{settings,notebook,canvas}/page.tsx` | Existing project screens |
| `src/components/project-workspace.tsx` | Shared header, two research tabs, settings, Intelligence, last-view routing, save indicator |
| `src/components/project-overview.tsx` | Explicit-save project settings and provider availability |
| `src/components/workspace-provider.tsx` | `useWorkspace`, buffered mutations, import gate, backend synchronization |
| `src/lib/projects.ts` | UI types, factories, pure `applyMutation`, legacy validation/migration/adapter |
| `src/lib/kernel-repository.ts` | `kernel<T>` HTTP helper and `kernelRepository.load/apply` |
| `src/components/project-notebook.tsx` | Central question and structured entry document |
| `src/components/research-entry.tsx` | Shared object editor, stable focused draft, type icons, metadata, Discuss action |
| `src/components/research-canvas.tsx` | React Flow graph, placement, editing, Select/Connect/Disconnect |
| `src/components/research-actions.tsx` | Manual scientific operations, First Heartbeat, runs, Research Trail |
| `src/components/research-intelligence.tsx` | Drawer, modes, context selection, messages, proposals, provider availability |
| `src/components/settings.tsx` | Browser-local serif-note/compact-list preferences |
| `src/app/globals.css` | Existing visual tokens and component styling |
| `src/app/api/kernel/[...path]/route.ts` | Same-origin proxy; no provider SDK implementation |
| `backend/app/db.py` | Scientific ORM models, engine, Session, IDs, timestamps, dotenv |
| `backend/app/main.py` | Core APIs, transactions, services, action schemas/registry, execution, imports; includes Intelligence router at end |
| `backend/app/science.py` | Registered causal adapter constants, Parameters, predictions, simulation, numerical validation |
| `backend/workers/causal_intervention.py` | Fixed JSON-stdin worker; no arbitrary code/path input |
| `backend/app/providers.py` | Older **manual** ProposalProvider interface and ManualProvider; not live SDK routing |
| `backend/app/model_providers.py` | Live ResearchModelProvider protocol, SDK adapters, routing, retries, safe errors |
| `backend/app/intelligence_models.py` | Conversation/message/proposal ORM models |
| `backend/app/intelligence_schemas.py` | Canonical typed response/proposals, mode mapping, prompt/contract |
| `backend/app/gemini_transport.py` | Gemini-compatible wire schema and per-proposal normalization |
| `backend/app/proposal_correction.py` | Single targeted formatting correction with content-preservation checks |
| `backend/app/research_context.py` | Bounded authoritative scientific context |
| `backend/app/intelligence.py` | Conversation/turn/review APIs and transactional acceptance |

`main.py` is currently a function-based service/API module. There is no separate
OperationEngine class, general job scheduler, repository package, or adapter plugin
loader to discover. Reuse the actual functions; extract narrowly scoped services
if needed instead of creating a parallel kernel. `intelligence.services()` lazily
imports `app.main` to reuse its helpers; be careful with circular imports.

## 3. Scientific persistence and model relationships

### Database mechanics

- `db.ROOT` is the repository root. `load_dotenv(ROOT / 'backend/.env', override=False)`
  runs before engine configuration; process environment wins.
- `KERNEL_DB_PATH` overrides `.vectorheart/kernel.sqlite3`. The directory is created
  on module import. A relative override resolves relative to process working directory.
- SQLite connections enable `foreign_keys=ON` and WAL; timeout is 30 seconds.
- `Session` uses `expire_on_commit=False`.
- `main.transaction()` uses an in-process RLock and `BEGIN IMMEDIATE`, commits on
  success and rolls back on failure. Do not hold it across model/network/worker calls.
- New IDs use `db.uid()` (UUID strings); imported stable non-UUID IDs are allowed.
  `db.now()` returns timezone-aware ISO timestamps stored as strings.
- JSON is used for metadata, settings and bounded structured payloads. Object IDs,
  project ownership, operation state and core references are explicit columns.

### Actual tables (13 application tables plus Alembic)

| Table / ORM class | Columns and important constraints |
| --- | --- |
| `projects` / Project | `id` PK, title, description, created_at, updated_at, settings JSON, question, last_visited_view, schema_version, sequence |
| `objects` / Object | `id` PK, project_id FK, object_type, title, body, created_at, updated_at, current_revision, provenance_type, SQL `metadata` JSON mapped as `scientific_metadata`, schema_version, deleted |
| `revisions` / Revision | revision_id PK, object_id FK, revision_number, title_snapshot, body_snapshot, metadata_snapshot JSON, previous_revision_id, actor_type, created_at, reason; unique (object_id, revision_number) |
| `relationships` / Relationship | id PK, project_id FK, source_object_id FK, target_object_id FK, relationship_type, evidence_id nullable FK to **objects**, created_at, SQL metadata JSON mapped as `details` |
| `placements` / Placement | object_id PK/FK, project_id FK, x, y; one placement per object |
| `operations` / Operation | id PK, project_id FK, kind, action_type, target_object_ids JSON, proposed_by, proposal_payload JSON, assumptions JSON, rationale, created_at, updated_at, status, approval_record JSON nullable, execution_id nullable, schema_version |
| `specifications` / Specification | id PK, project_id FK, operation_id unique FK, adapter_id, adapter_version, parameters JSON, predicted_outcomes JSON, measurement_plan, validation_plan JSON, execution_limits JSON, environment_type, created_at, approved_at nullable, specification_hash, schema_version |
| `runs` / Run | id PK, experiment_specification_id FK, project_id FK, status, started_at, completed_at nullable, actual_parameters JSON, environment_metadata JSON, code_version, random_seed, measured_outputs JSON, artifact_references JSON, validation_results JSON, errors JSON, duration_ms |
| `evidence` / Evidence | id PK/FK to its evidence **Object**, project_id FK, source_run_id FK, source_type, target_hypothesis_ids JSON, measured_results JSON, interpretation, verification_status, limitations JSON, created_at, provenance JSON |
| `events` / Event | id PK, project_id FK, project_sequence_number, event_type, actor_type, actor_identifier, source_operation_id nullable FK, affected_object_ids JSON, payload JSON, timestamp, schema_version; unique (project_id, project_sequence_number) |
| `research_conversations` / ResearchConversation | id PK, project_id unique FK, created_at, updated_at; one conversation per project |
| `research_messages` / ResearchMessage | id PK, conversation_id FK, role, content, mode, provenance JSON, context JSON, response_details JSON, created_at, status, request_key, request_hash; unique (conversation_id, request_key, role) |
| `research_proposals` / ResearchProposal | id PK, project_id FK, source_message_id FK, action_type, payload JSON, source_references JSON, provenance JSON, status, result_ids JSON, created_at, updated_at |
| `alembic_version` | `version_num`; inspected applied revision `0002` |

Not every conceptual reference is a database FK: previous_revision_id and
operations.execution_id are strings; current_revision is an integer; target/source
lists and result_ids are JSON. Same-project ownership and relation deduplication
are enforced by service validation, not composite ownership constraints or a
database unique constraint on edge endpoints/type. Do not advertise stronger DB
guarantees than these definitions provide.

### Migrations

- `0001_kernel.py`: initial scientific tables via `Base.metadata.create_all`.
- `0002_research_intelligence.py`: adds the three Intelligence tables; down_revision
  `0001`, explicit table creation with checkfirst; no scientific column replacement.
- `migrations/env.py` configures the imported Base/engine and batch rendering.
- For Stage 3 add a new forward migration. Do not rewrite old revisions, delete
  SQLite, or call create_all during request handling. The old initial migration
  refers to live ORM metadata, so take particular care not to rely on autogeneration
  or implicit model imports to define a new durable schema.

### Objects, revisions, events and deletion

Object types: `note`, `question`, `hypothesis`, `observation`, `prediction`,
`experiment`, `evidence`, `concept` in the DB; title-case strings in workspace JSON.
`add_object()` creates an initial revision and event. Hypotheses get statement,
assumptions, predicted_outcomes, limitations and epistemic_status metadata.
Allowed hypothesis statuses at creation are proposed, unresolved,
conditionally_supported, challenged, rejected_within_scope; they are not truth
probabilities. Accepted hypothesis modifications mark the claim unresolved.

`revise()` saves a new title/body/metadata snapshot and links the previous revision
when these values meaningfully differ. `current_revision` is a projection, not the
history itself. Experiment/Evidence content patches are rejected. Ordinary editable
object patches preserve revisions; type changes are limited by existing code.

`event()` increments Project.sequence and writes an Event in the caller's write
transaction. Existing events include object_created/revised/removed,
project_created/updated/archived, relationship_created/removed, legacy_import,
operation_proposed/approved/rejected/running/completed/failed, retry_proposed,
experiment_completed, evidence_recorded, revision_accepted,
first_heartbeat_created and intelligence_proposal_accepted/rejected.

The event and revision APIs are append-only by convention: no ordinary update
endpoints exist, but there are no SQL immutability triggers or cryptographic journal
guarantees. Revisions snapshot content, not all layout/type/graph changes. This is
not complete historical graph reconstruction or scientific time travel.

Project DELETE sets `settings.archived=true`; the frontend filters archived projects.
Object DELETE tombstones `deleted=true`, removes active placements and incident
relationships, and journals removal. It does not erase content history or runs.
The ordinary object/revision lookup rejects tombstoned objects, so archival recovery
currently needs developer-level access. Relationship deletion physically removes
the active row; there is no relationship revision/rationale editing API yet.

## 4. Existing operation engine and real experiments

Three different vocabularies must stay separate:

1. Research objects (scientific entities).
2. Kernel operations (validated intentions, approval and execution state).
3. Intelligence proposals (model suggestions pending human review).

Kernel registry `main.REGISTRY` is an actual dictionary:

| Action | Target | Pydantic input |
| --- | --- | --- |
| `construct.hypothesis_from_note` | note or question | Construct: statement 1–10000 chars; assumptions, predicted_outcomes, limitations default [] |
| `destroy.test_hypothesis` | hypothesis with causal_demo metadata | TestHypothesis: adapter_id fixed to toy.causal_intervention.v1, parameters default Parameters(), rationale string default |
| `modify.propose_hypothesis_revision` | hypothesis | Modify: original_statement, proposed_statement 1–10000, evidence_ids (at least one), scope, remaining_uncertainties, rationale; assumptions_changed defaults [] |

These action inputs forbid extra fields. The operation request wrapper `Proposal`
has action_type, target_object_ids (exactly one) and proposal_payload. `propose()`
validates through ManualProvider, target type/project, registered adapter scope and
linked evidence for modifications. It records base_revision and creates a
Specification for Destroy. There is no arbitrary natural-language action executor.

States: draft → approved/rejected; approved → running; running → completed/failed.
`approve()` only accepts draft and checks stale modification bases. `reject()` only
accepts draft. Approval and execution are separate endpoints. `execute()` guards
one runner slot; `execute_locked()` returns an existing completed operation on a
duplicate execute request and refuses unapproved execution.

For Destroy, a first transaction records running operation/run; then a fixed
subprocess executes outside the transaction. A second transaction atomically saves
validated results, creates Experiment/Evidence objects, EvidenceRecord, graph links,
and events. Failures persist errors and produce no fake evidence. `retry()` creates
a new draft operation linked in a retry event; it is not automatic execution.

Reusable services: `apply_hypothesis_construction()` and
`apply_hypothesis_revision()` are shared by manual operations and Intelligence
acceptance. The latter verifies the base revision again before changing content.

### First Heartbeat adapter

Only `toy.causal_intervention.v1` exists. In `science.py`:

- Parameters: world A/B (default A), intervention_value [-5,5] (2), sample_count
  strict integer [100,5000] (1000), seed strict uint32 (42). Invalid values are rejected.
- Observational models: A has X=epsilon_x, Y=.8X+.6epsilon_y; B has
  Y=epsilon_y, X=.8Y+.6epsilon_x. Both imply covariance [[1,.8],[.8,1]].
- Under do(X=x), A predicts Y mean .8x, variance .36; B predicts mean 0, variance 1.
- `simulate()` uses seeded NumPy default_rng, records every sample, sample SD with
  ddof=1, SE and approximate mean ± 1.96 SE interval, and candidate-mean compatibility.
- `validate_result()` validates NumericalResult, finite outputs, count, independently
  recomputed statistics, interval, predictions, checksum, compatibility and simulation label.
- Samples are embedded in Run.measured_outputs, with canonical JSON SHA-256,
  Python/NumPy versions, seed, parameters and artifact metadata. There is no arbitrary
  file artifact download system; the artifacts endpoint returns references/metadata.

Specification approval records approved_at; execution verifies the hash over its
adapter/parameters/predictions/plans/limits/environment. Worker invocation is
`[sys.executable, fixed worker path]`, validated JSON stdin, capture_output,
timeout=15, shell=False. This is a trusted-code subprocess, **not** a secure sandbox.

Graph direction produced by execution is exact:

```text
Experiment --tests--> Hypothesis
Experiment --produces--> Evidence
Evidence --supports or challenges--> Hypothesis
```

Evidence status is execution_checked after numerical checks; no method review or
independent replication is implied. Synthetic results are never real-world causal
proof. Candidate mean inside the approximate CI is the implemented comparison rule.

`POST .../demo` is user-invoked, not automatic. It creates the observational question,
two hypotheses with causal_demo/candidate_world metadata, and a draft challenge for
Hypothesis A. Repetition is refused if causal_demo objects already exist in project.

## 5. Notebook, Canvas and frontend persistence

### Workspace state and wire shapes

`WorkspaceProvider` exposes projects, ready, error, pending, create, update, remove,
mutate, `flush(): boolean`, and **`sync(): Promise<void>`**.

- `applyMutation()` updates React state immediately and avoids no-ops.
- Queued adjacent object-edit patches are merged; consecutive position mutations
  for the same object are coalesced while not saving.
- A fixed 10-second interval flushes; it is not an inactivity debounce. Creation,
  project deletion and explicit settings/Research Actions can request immediate saving.
- `kernelRepository.apply()` sends field mutations to existing APIs; it does not PUT
  a whole local project over the backend. `sync()` serializes saves, drains the queue,
  loads projects again, and rebases any newer queued changes into the UI projection.
- **Await sync() for dependent actions.** flush() starts asynchronous work and returns
  false while work is pending; it is not an awaitable save-completion guarantee.
- Header links/workspace or Canvas unmount/pagehide/hidden visibility/beforeunload
  request a flush. `kernel()` uses fetch keepalive on writes. Network persistence
  cannot finish synchronously at browser exit; forced closure can lose buffered work.
- No current polling/subscription provides multi-tab or background-job updates.
  Science views explicitly call sync/load or use the refresh event. No revision-based
  multi-user optimistic concurrency applies to ordinary content patches.

Project payloads use camelCase: createdAt, updatedAt, lastVisitedView; objects use
projectId, type, metadata, currentRevision, provenanceType; relationships in project
payload use sourceId, targetId, type; placements use objectId and position {x,y}.
Raw relationship/operation/run/event/revision APIs mostly expose snake_case ORM
attributes. In particular project_view omits relationship details/provenance/evidence_id
while GET relationships exposes them (`details` is the ORM attribute). Stage 3 must
deliberately extend DTOs to show graph provenance/rationales, not guess those fields
already reach React Flow. TypeScript Project/ResearchObject types are narrower than
some actual returned JSON; `kernel<T>` asserts types without runtime response parsing.

### Legacy migration and preferences

Legacy keys are `vectorheart.projects.v1` and `vectorheart.projects.v2`.
`vectorheart.kernel.imported.v1` is the browser marker that bypasses the import gate.
The gate exports both raw strings as a JSON backup, imports validated data, awaits
backend reload, then marks migration complete. Original research keys are untouched.
`migrateLegacy()` converts a v1 notes string into a structured Note and preserves the
central question. `/v1/import` skips existing project IDs rather than overwriting
newer backend data, preserves unknown/raw legacy data in import metadata/events,
and reports skipped missing/foreign references. Invalid imports roll back.

Do not switch the app back to the legacy `localProjectRepository.save()` merely
because it remains in projects.ts. Its retained role is migration/testing. The
separate `vectorheart.preferences.v1` key still stores serif-note/compact-list UI
preferences; this is not a scientific data source.

### Notebook

ProjectNotebook renders project.question (“Central research direction”) and every
project.objects entry. ResearchEntry supports inline title, plain multiline body,
type selection, deletion confirmation, metadata details, and Discuss this research
object. WritingField retains focused drafts and resizes textareas, preventing
ordinary saves from remounting the editor/moving the cursor. Experiment/Evidence
text is read-only; normal creation controls exclude those two types.

This is currently a structured-entry notebook, **not a continuous research journal**.
It also displays accepted model objects and execution findings alongside human
entries. A source-journal-only view is future work and must not hide/destroy legacy
objects. Existing manual Research Actions and First Heartbeat stay accessible.

### Canvas rendering and spatial state

ResearchCanvas wraps CanvasSurface in ReactFlowProvider. Nodes are derived from
placements joined to project.objects by ID; they do not duplicate content. Edges
come from project.relationships and render only when both endpoints are placed.
The custom ResearchNodeView uses one restrained style with type icon/title/preview.
Edges are directed smoothstep lines with arrow markers. There is no automatic
semantic graph generation, automatic graph layout, persisted viewport, separate
projection layer, proposal overlay, or origin-dependent novelty styling yet.

- New entry creates one shared object and a placement at the current viewport center.
- Place existing entry places an unplaced shared object, including Experiment/Evidence.
- React Flow onNodesChange sends immediate optimistic positions; backend writes use
  the shared buffer. Zoom bounds .15–2.5; fitView and zoom controls exist.
- Double-click or edit opens ObjectDialog with the same ResearchEntry editor.
- Select is default; normal drag/pan/selection/editing and handle connections work.
- Connect selects source, then target; attempts a directed relationship; exits to
  Select on success. Self-loop clicks do nothing destructive.
- Disconnect selects two endpoints, checks both directions; one match is removed,
  multiple matches show a specific direction/type picker. Objects are not deleted.
- Escape returns to Select and clears endpoints; switching modes clears unfinished
  state; clicking the empty pane clears endpoint/candidates. Drag/edit/handles and
  delete keys are disabled during Connect/Disconnect. A short double-click guard
  prevents a tool click from immediately opening the editor.
- Explicit “Remove from canvas” unplaces objects but leaves graph/content. React Flow
  keyboard node deletion also runs its edge-deletion callback for edges in the
  deletion set, so that path can remove relationships as well as placements.
- Selected-edge deletion removes that relationship. Full object deletion in its
  editor tombstones the object and removes its placements/incident graph edges.

**Existing caveat:** Canvas duplicate checks treat untyped edges as `!r.type`, while
the backend normalizes absent type to related_to. The authoritative relationship
service deduplicates source/target/type, but a repeated manual connection can show
an optimistic duplicate until sync. Do not assume the current UI has a typed-edge
creation editor or that changing a relation type/rationale is already supported.

## 6. Research Intelligence and the repaired proposal contract

### Provider boundaries and routing

`ResearchModelProvider.generate_structured_response(ModelRequest) -> ModelResponse`
lives in model_providers.py, distinct from the older manual ProposalProvider.
ModelRequest carries model/system/message/context/history, output limit, timeout,
generation_parameters, canonical schema and correction_attempt. The current adapters
primarily use the limits/schema; generation_parameters is not a general user-facing
sampling-controls implementation.

| Adapter | Official SDK call |
| --- | --- |
| OpenAIProvider | OpenAI.responses.parse with instructions, text_format, max_output_tokens, store=False |
| AnthropicProvider | Anthropic.messages.parse with system, messages, output_format, max_tokens |
| GeminiProvider | genai.Client.models.generate_content with JSON MIME type and GeminiScientificResponse transport |

All SDK imports/inference are server-side. No tools are supplied to model SDKs.
ModelResponse carries canonical output, optional reported usage, rejected_proposals,
original proposal_indices, and correction diagnostics. Costs are not invented:
provenance estimated_cost is null. API response/provider logs never intentionally
include credentials; ModelRequest.payload and context scrub known credential values.

`route(settings, role)` reads existing settings.modelAssignments. Automatic selects
the first configured key + server default model in VECTORHEART_PROVIDER_PRIORITY
(default OpenAI,Google Gemini,Anthropic). It ignores a project model ID in Automatic.
Explicit provider uses project modelId, else its server default, and never falls
back. Custom is unimplemented. Capability “available” means configuration, not a
successful live request; explicit project models can work without a server default.

Modes map exactly: Explore → General Reasoning; Formalize → Hypothesis Construction;
Challenge → Critical Review / Verification; Design Experiment → Experiment Coding;
Synthesize → Conceptual Synthesis. Literature Analysis remains a stored preference.

Provider SDK retries are disabled. bounded_retry allows up to two initial attempts
for timeout/provider_failure within its deadline/half-timeout allocation, not
authentication/schema/rate-limit errors. A formatting correction has one attempt.
Two in-process inference slots and one running turn per conversation bound concurrency.
Gemini has separate sanitized status/stage diagnostics and error categories;
OpenAI/Anthropic retain the broader safe_error mapping.

### Context builder

ResearchContextBuilder.build(session, pid, selected_id, conversation_id, question)
queries authoritative active objects, relationships, Revision, Evidence/Run, Event,
and completed ResearchMessages. It prioritizes selected object, one-hop neighbors,
important/relevant types and word overlap, with recent source order as a tie-break.
It fetches all active objects before budgeting; this is not a scalable vector search.

Project context defaults to 24000 characters (clamp 4000–48000). It includes the
registered adapter schema/scope; project title/description/question/field; object
IDs, revision IDs/numbers, body excerpts (3000 chars), metadata allowlist,
provenance/verification labels; relationships with included endpoints; up to six
recent Evidence summaries with actual run parameters/checks; eight recent event
labels; and separate history of at most eight completed messages, 1500 chars each.
Oversized records are omitted or excerpted without cutting JSON; truncation/omitted
counts are saved. Raw sample arrays and import backup event payloads are excluded.

The system prompt identifies project/history content as untrusted data, limits
scientific claims, forbids invented references/measurements, and preserves human
authority. This is an instruction boundary, not a proof against prompt injection
or scientifically incorrect generated prose. Current stored message context retains
object revision references/truncation, not the entire exact prompt/context snapshot.

### Exact canonical schemas

Source of truth: intelligence_schemas.py. `Strict` forbids extra keys and nonfinite
floats; it does not globally enable Pydantic strict scalar typing.

```text
Text = string, max 4000 chars
Items = list[Text], max 12
References = list[string], max 30

ProposalAction = create_question | create_hypothesis | create_observation |
                 propose_relationship | propose_experiment | propose_revision
RelationshipType = supports | challenges | derived_from | tests | produces | related_to

AdapterParameters:
  data_generating_world: A | B
  intervention_value: float
  sample_count: int
  seed: int
  (numeric bounds are applied by the registered science.Parameters validator)

ScientificProposal:
  action_type: ProposalAction
  title: string, 1..120
  content: string, 1..10000
  rationale: Text
  assumptions: Items
  predictions: Items
  limitations: Items
  referenced_object_ids: References
  target_object_id: string | null          [required key]
  adapter_id: string | null                [required key]
  adapter_parameters: AdapterParameters | null [required key]
  evidence_ids: References
  source_object_id: string | null = null
  relationship_type: RelationshipType | null = null

ResearchIntelligenceResponse:
  answer: string, 1..20000
  uncertainties: Items
  context_references: References
  proposals: list[ScientificProposal], 0..3
  limitations: Items

TurnRequest:
  message: string, 1..10000
  mode: Explore | Formalize | Challenge | Design Experiment | Synthesize = Explore
  selected_object_id: string | null = null
  idempotency_key: string, 8..100
```

All fields above without defaults are required, including nullable keys and arrays.
The provider must not assign proposal ID, status, timestamp, provenance, or new
object IDs. `proposal_contract()` embeds the actual canonical schema and action
rules into the system instructions, version `research-intelligence.v2`.

### Two repaired Gemini pitfalls — do not regress

1. Sending the strict canonical Pydantic model as Gemini response_schema caused
   HTTP 400 “Unknown name additional_properties.” The installed SDK translates
   extra='forbid' into an unsupported wire keyword. gemini_transport.py omits
   additionalProperties on the transport, then strictly validates the **raw JSON**
   against canonical schemas. Never accept the looser transport model as authority.
2. An unrestricted transport action string and omitted contract let Gemini output
   `formalize_hypothesis` or `Design Experiment` instead of canonical actions. The
   transport now shares ProposalAction/RelationshipType literals; the prompt derives
   constraints from the canonical schema. Modes, proposals and kernel action names
   are separate vocabularies. Do not “fix” this by accepting arbitrary strings.

### Generation, correction, validation and review

1. `turn()` checks project/conversation ownership and idempotency key+request hash.
   It persists the user message and running assistant placeholder in a transaction.
2. It assembles context, routes the provider and calls it outside the DB lock.
3. Gemini normalization validates the envelope, then each proposal independently.
   Malformed proposals carry field/type diagnostics and an in-memory `_candidate`.
   Zero proposals is valid. A malformed overall envelope is a failed turn.
4. `correct_proposals()` permits at most one targeted correction for eligible
   formatting/action-name errors. Missing scientific reasoning is ineligible.
   `same_science()` requires exact scientific content, title, reasoning, reference
   lists and parameters; only inapplicable optional empty/null representations may
   change. Valid siblings and original answer remain. Correction output gets the
   same canonical checks. No reference guessing or numeric clamping is allowed.
5. `validated_proposal()` checks all source/target/evidence references are supplied,
   current, active, and in-project; appropriate target types; distinct relationship
   endpoints; registered parameters; and linked measured Evidence for revisions.
   It records original_statement/base_revision for a revision. A wrong reference
   in top-level context_references fails the entire turn; a bad proposal is withheld.
6. Valid suggestions become pending ResearchProposal rows, not research objects.
   Rejected diagnostics remain on the assistant response. `_candidate` and
   `_corrected` never reach persistence. Provider/model/prompt/time/usage/context
   revision information is preserved. No scientific execution occurs here.
7. Human accept/reject uses the existing transactional acceptance endpoint, validates
   again, and returns stored result_ids for repeated acceptance. Rejected proposals
   cannot be accepted. Rejected history/messages are retained.

Acceptance dispatch is exact:

| Proposal | Current accepted result |
| --- | --- |
| create_hypothesis with a referenced Note/Question | Registered Construct operation; human acceptance records approval, running, construction and completion atomically through shared kernel helper |
| create_hypothesis without that source precondition | Normal add_object Hypothesis + initial revision/event/source derived_from links |
| create_question | Normal Question object with provenance and source links |
| create_observation | Observation with source_type=model_suggestion, verification_status=unverified; no measured evidence |
| propose_relationship | Existing relationship service; source/target/type revalidated; new edge gets rationale, limitations, model provenance, unverified status in details; pre-existing edge metadata is not overwritten |
| propose_experiment, registered causal adapter + valid parameters + causal_demo target | Draft Destroy operation + Specification; **still needs separate approve and execute** |
| propose_experiment otherwise | Conceptual Note, model provenance, conceptual_experiment=true; no run/evidence/completed experiment |
| propose_revision | Linked measured evidence and unchanged base revision required; shared Modify proposal/revision service, approval/running/completion events and new content revision atomically applied by explicit human acceptance |

Accepting a content/revision proposal authorizes that content change. It is never
approval to execute an experiment. Source records are not silently rewritten.
The current conceptual-experiment semantic path still requires a Hypothesis target;
it does not accept a Question target even though future product flows might want it.

The drawer persists one conversation per project, shows complete replies (no fake
streaming), modes, context revisions, token usage when supplied, uncertainties,
proposal rationale/constraints and review buttons. After review it awaits sync(),
reloads conversation and dispatches `vectorheart-research-refresh` for ResearchActions.
`vectorheart-discuss` carries projectId/objectId and opens contextual Intelligence;
normal Canvas selection emits `vectorheart-object-focus` to preselect context.

Failed inference is stored as a failed assistant message, often returned as HTTP
200 with status=failed and response_details.error_code. Check status, not only HTTP.
Repeated identical turns return the same persisted record; altered payload with
the same key conflicts. Conversations reject another turn while one is running.
`recover_interrupted()` marks running messages older than 180 seconds failed when
history/turn endpoints are read. Closing the drawer does not cancel server work.
This is conversation recovery, not a durable resumable scientific investigation.

## 7. Current API inventory

Backend prefix `/v1`; browser prefix `/api/kernel/v1`. `{pid}`, `{oid}`, `{rid}`,
`{cid}` denote the actual scoped route parameters; oid is object/operation as shown.

| Method | Backend path | Purpose |
| --- | --- | --- |
| GET | /v1/health | Service/schema/capabilities; no credential values |
| GET, POST | /v1/projects | Workspace projections / create |
| GET, PATCH, DELETE | /v1/projects/{pid} | Read/update/archive |
| POST | /v1/import | Validated idempotent legacy import |
| GET, POST | /v1/projects/{pid}/objects | List/create |
| GET, PATCH, DELETE | /v1/projects/{pid}/objects/{oid} | Read/content update/tombstone |
| GET | /v1/projects/{pid}/objects/{oid}/revisions | Ordered content history |
| GET, POST | /v1/projects/{pid}/relationships | List/create |
| DELETE | /v1/projects/{pid}/relationships/{rid} | Remove active edge |
| GET | /v1/projects/{pid}/canvas | Raw placement records |
| PUT, DELETE | /v1/projects/{pid}/canvas/{oid} | Set x/y / unplace |
| GET, POST | /v1/projects/{pid}/operations | List/propose kernel operation |
| GET | /v1/projects/{pid}/operations/{oid} | Operation plus Specification |
| POST | /v1/projects/{pid}/operations/{oid}/approve | Human approval |
| POST | /v1/projects/{pid}/operations/{oid}/reject | Reject draft |
| POST | /v1/projects/{pid}/operations/{oid}/execute | Execute approved operation |
| POST | /v1/projects/{pid}/operations/{oid}/retry | Create linked new draft after failure |
| GET | /v1/adapters | Single registered adapter and parameter schema |
| GET | /v1/projects/{pid}/runs | Runs with recorded measurements |
| GET | /v1/projects/{pid}/runs/{rid} | Specific run |
| GET | /v1/projects/{pid}/runs/{rid}/artifacts | Embedded-artifact metadata |
| GET | /v1/projects/{pid}/evidence | Evidence records |
| GET | /v1/projects/{pid}/events?after=0&limit=100 | Ordered journal, limit clamped 1–500 |
| POST | /v1/projects/{pid}/demo | User-invoked First Heartbeat setup |
| GET | /v1/intelligence/providers | Safe configuration/capability flags |
| GET, POST | /v1/projects/{pid}/intelligence/conversations | List / get-or-create one conversation |
| GET | /v1/projects/{pid}/intelligence/conversations/{cid} | Messages/proposals/history |
| POST | /v1/projects/{pid}/intelligence/conversations/{cid}/turns | Model request and persisted response |
| POST | /v1/projects/{pid}/intelligence/proposals/{proposal_id}/accept | Validated human acceptance |
| POST | /v1/projects/{pid}/intelligence/proposals/{proposal_id}/reject | Review rejection |

FastAPI also exposes /docs and /openapi.json directly on the local backend. The
Next proxy only forwards `/v1/...`, validates path segments, checks Origin when
present, limits request text to 5M characters, and requires a server-configured
loopback KERNEL_API_URL. Timeouts: 95s for paths including intelligence, 25s otherwise.
It forwards JSON and HTTP status; there is no arbitrary user-supplied destination.
Backend ordinary errors use `{error:{message}}`; schema/DB/service validations vary
in strictness by endpoint. Some lists/raw payloads are not fully response-model typed.

## 8. Startup, environment, backups and tests

### Existing Windows PowerShell startup

From the repository root, Python 3.11+ and Node 22.13+ (the JSDOM test requirement):

```powershell
# First setup only; do not recreate an existing working environment unnecessarily.
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
# Edit backend/.env locally. Never paste credentials into source or a Codex log.
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Second terminal:

```powershell
npm install
npm run dev
```

Open http://localhost:3000. Production preview: `npm run build`, then `npm start`
while the kernel is running. The usual backend command has no --reload: restart
Python after changing its code/configuration. `.vscode/settings.json` only enables
python.terminal.useEnvFile; it does not define a combined service/task launcher.
Read example env files, not real secrets, when preparing automation.

| Variable | Owner/default |
| --- | --- |
| KERNEL_API_URL | Next server; http://127.0.0.1:8000; optional .env.local |
| KERNEL_DB_PATH | Python migration and server; repository .vectorheart/kernel.sqlite3 |
| OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY | Python environment/backend .env; never NEXT_PUBLIC_ |
| OPENAI_DEFAULT_MODEL, ANTHROPIC_DEFAULT_MODEL, GEMINI_DEFAULT_MODEL | Account-supported server default; no general hardcoded model fallback |
| VECTORHEART_PROVIDER_PRIORITY | OpenAI,Google Gemini,Anthropic |
| VECTORHEART_CONTEXT_CHARS | 24000, clamp 4000–48000 |
| VECTORHEART_MAX_OUTPUT_TOKENS | 3000, clamp 256–8000 |
| VECTORHEART_MODEL_TIMEOUT | 30 seconds, clamp 5–40 |

Direct Python browser-Origin requests are restricted to localhost/127.0.0.1:3000;
the Next proxy handles the ordinary browser path. These checks are not authentication.
Bind Python to 127.0.0.1; do not publicly deploy either unauthenticated service.
Git ignores backend/.venv, .vectorheart, .env files, .next, node_modules and caches.
Back up SQLite with the server stopped (or use a proper SQLite backup mechanism
that accounts for WAL); do not copy only the main file during writes and assume it
is complete. Do not reset user data to run tests. Keep KERNEL_DB_PATH consistent
between migrations and service startup.

### Automated checks (unpaid)

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm test
npm run lint
npm run typecheck
npm run build
backend/.venv/Scripts/python -m compileall -q backend/app backend/workers
backend/.venv/Scripts/python -m pip check
```

Pinned direct dependencies are in backend/requirements.txt; the full reproducible
environment is requirements-lock.txt. Key SDK pins are openai 3.51.0, google-genai
3.3.0, anthropic 2.8.0, Pydantic 2.14.3. Frontend scripts are defined in package.json.

| Tests | Coverage / operational notes |
| --- | --- |
| backend/tests/conftest.py | Sets temporary KERNEL_DB_PATH before importing app models; applies migrations |
| test_kernel.py | Real worker cycle, approval, revisions/events, imports, integrity/failure, numerical validation, process persistence |
| test_intelligence.py | Routing/configuration, context bounds/isolation, proposals, evidence/revision checks, idempotency/history, mocked SDK invocation |
| test_gemini_repair.py | Original wire keyword, actual installed SDK schema conversion, strict normalization, error redaction/categories, partial invalid proposals |
| test_proposal_pipeline.py | Action enum mismatch, one correction, unchanged science/refs, relationships/observations/conceptual acceptance, provenance |
| tests/projects.test.mjs | Pure legacy adapter/mutation tests; not proof of current browser-local scientific authority |
| tests/workspace.test.mjs | JSDOM components + real temporary kernel + real First Heartbeat computation; drawer send/review/reload/Canvas availability |
| backend/tests/ui_server.py | Explicit test-only entry point with deterministic provider; no normal-server test-provider toggle |

Frontend tests expect `backend/.venv/Scripts/python.exe` and free port **8002**;
they spawn ui_server.py with temporary SQLite and redirect test fetches directly
to it. They do not exercise browser pointer geometry, visual responsiveness or
the actual Next proxy. Native dialog/ResizeObserver behavior is stubbed in JSDOM.
Backend tests use temporary storage and fake model providers; no paid inference.
Tests currently have one known Starlette/AnyIO deprecation warning.

### Opt-in live verification (costs API quota)

```powershell
backend/.venv/Scripts/python backend/tests/live_gemini_repair.py --diagnose
backend/.venv/Scripts/python backend/tests/live_gemini_repair.py --verify
backend/.venv/Scripts/python backend/tests/live_proposal_pipeline.py --diagnose
backend/.venv/Scripts/python backend/tests/live_proposal_pipeline.py --verify
```

The older Gemini-repair script explicitly uses gemini-3.5-flash-lite; its diagnose
mode deliberately submits the unrepaired canonical wire schema to reproduce the
400. The proposal-pipeline script uses GEMINI_DEFAULT_MODEL or that fallback in
this test script, not in production routing. It captures raw proposals only from
disposable synthetic projects in diagnose mode. Verify mode makes four live turns:
hypothesis, conceptual myopia study, existing-object relationship, and executable
First Heartbeat. It accepts objects/relationships, checks duplicate acceptance,
provenance/revisions/Canvas identity, then explicitly approves and executes the
synthetic draft. Temporary databases are removed via engine disposal/cleanup.
Never point live-test storage at the real research database.

Existing documentation records successful real Gemini explanation, hypothesis,
relationship, conceptual-study and executable-draft paths on gemini-3.5-flash-lite.
OpenAI/Anthropic SDK adapters have deterministic contract tests; live account
connectivity is not established by those tests. Provider capabilities always report
live_connectivity_verified=false rather than pretending an env key proves access.
No live inference or regression suite was rerun for this documentation-only handoff.
Re-run relevant checks after implementation; never report historical tests as new runs.

## 9. Architectural constraints and pitfalls to carry forward

1. **Protect the existing demo and data.** No new repository/app, speculative database
   reset, table replacement, or unconditional demo population. Use additive migrations.
2. **Reuse one scientific graph.** Placement is spatial metadata, not a second object
   database. Conversation messages/proposals are not accepted objects or evidence.
3. **Await saves before dependent actions.** flush is asynchronous trigger; sync is
   the completion API. No durable client outbox protects forced termination.
4. **Guard stale sources.** Explicit scientific revisions check base_revision;
   ordinary Notebook patches are last-write-wins. A Stage 3 graph reconstruction
   needs source revision checks and stronger reconciliation semantics.
5. **History is useful but incomplete.** No relationship/layout revisions, complete
   event replay, persistent graph-correction rationales, investigation checkpoints,
   cancellation, execution leasing, or robust crash recovery for scientific runs.
6. **Execution is synchronous and local.** API request threads run fixed workers;
   operations can remain running after a process crash. Conversation expiry does
   not resume an experiment. Retrying scientific failure creates a new draft.
7. **New experiment scope must be registered.** causal_demo is the current gate, not
   a general domain validator or clinical-study execution capability. Do not repurpose
   the causal simulator to fabricate unrelated scientific outcomes.
8. **Evidence is narrow.** Current automatic evidence is simulation/execution_checked.
   Other conceptual source/verification categories are not all implemented adapters.
   Never promote a model suggestion to verified findings or a claim to proven.
9. **Rendering needs richer DTOs.** Current node style does not identify researcher
   vs interpreted vs novel vs measured origin; project graph JSON drops edge details.
10. **Approval is scoped.** Accepting an AI experiment proposal creates a draft;
    approval freezes that Specification; execution still requires another action.
    Never interpret “Accelerate” as blanket permission for future tools/parameters.
11. **No general authorization layer exists.** Local single-user checks, ID ownership
    and Origin restrictions do not provide secure public or multi-user deployment.
12. **Provider generation is non-authoritative.** The model can generate convincing
    but wrong content. Prompt instructions, reference validation and transport schema
    do not verify clinical methods or semantic scientific truth.
13. **Transport and canonical types must stay aligned.** Preserve Gemini's wire fix,
    shared action enum, canonical contract and bounded correction. New actions must
    update validation, acceptance, UI display and tests together.
14. **No invisible expansion of server commands.** Never execute model-generated
    Python/shell, user-specified files, arbitrary tools or URLs. No provider has DB access.
15. **Some settings are planning only.** environment, computeBudget and unused role
    assignments do not create execution environments, accounting or scheduling.
16. **Current resources assume a small project.** load returns full projects; context
    retrieval loads all active objects before budgeting; runs include raw samples;
    history/list endpoints are not all paginated. Stage 3 should bound work explicitly.

## 10. Intended Stage 3 architecture — recommendations, NOT existing behavior

### A. Primary researcher input: free-form research journal

Make the researcher's own writing the primary input: questions, intuitions,
observations, arguments, uncertainties and imported source notes can be written
without choosing an ontology type first. Preserve the exact original text and its
revision history. Do not rewrite it during extraction or silently append model
answers as researcher-authored journal entries.

Recommended design decisions before coding:

- Decide whether journal entries are explicitly tagged existing Note objects or a
  new source-record model. Keep existing structured entries accessible either way.
- Provide stable source-entry IDs, revision IDs and source-span references. Define
  how a graph claim points to a particular passage/revision and what happens after edits.
- Persist content before analysis; avoid sending stale React/localStorage drafts.
- Keep model interpretation and exploratory conversation separate from researcher
  text. Human acceptance/edits must be attributable and recoverable.

### B. Research Graph: reconstruct the researcher's existing understanding

The first AI graph pass should interpret **what is already present in the journal**:
claims, questions, assumptions, observations, dependencies, tensions and experiments
the researcher has described. It must not silently mix in novel AI hypotheses.
Show the source passage/revision and confidence/uncertainty of interpretation
(not probability of scientific truth). Mark inferred connections as interpretations.

Use the existing scientific object/relationship services when a claim is accepted
as scientific content. A reconstruction layer needs explicit provenance/review and
source mapping; it should not create a competing scientific truth database. The
exact new tables/endpoints should be designed in Stage 3, not assumed to exist here.

Reanalysis must be bounded and idempotent for a source revision, preserve stable
identities when matching existing interpretations, mark superseded interpretations,
and surface conflicts against newer journal/object revisions. Do not recreate a
new graph on each request or destroy the user's layout.

### C. Editable graph with persistent researcher corrections and rationales

Users should correct labels/content/types/direction, add or remove interpreted
relations, reject a misreading, and record **why**. Distinguish a correction of the
model's reading from an evidence-based scientific revision of a hypothesis.

Persist corrections and rationales with actor, source/revision, affected object/edge,
before/after values, time and causal event linkage. A later reconstruction should
honor these corrections and rejection decisions instead of resurrecting the same
misinterpretation. If new source text conflicts, ask for review rather than overwriting.

Canvas can remain the renderer but will need provenance-aware DTOs, relationship
edit/rationale services, and durable correction records. Spatial layout remains
independent: initial positioning may assist new nodes, but manual placements and
researcher corrections must survive reload/reanalysis. No current layout engine or
graph-correction endpoint exists to call as-is.

### D. AI Accelerate: novel proposals, visibly distinct from reconstructed thought

Add an explicit action that requests novel hypotheses, relationships, critiques,
alternative representations and experiments using the corrected graph, journal
sources and actual evidence. These are **model-origin pending proposals**, not a
reconstruction of what the researcher already believes.

Reuse the router, context builder, pending-proposal storage, semantic checks and
human acceptance services. Create a typed critique action only after defining its
canonical schema and kernel persistence semantics; there is currently no critique
proposal action. Never pass an arbitrary action string through to execution.

Visually distinguish researcher records, inferred graph interpretations, novel
pending proposals, accepted model-origin claims and experimental findings using
restrained labels/iconography/borders plus accessible text. Selection must not rely
on color alone. Keep the warm palette, full workspace, and closable contextual UI;
do not add a permanent dashboard sidebar or a generic chat-first replacement.

### E. Bounded autonomous investigation with approval and resumable execution

This is a new controller above the kernel, **not a provider-adapter loop**. It should
plan a bounded sequence, persist checkpoints, request approval for explicit tool
specifications, submit only registered implementations, validate actual outputs,
and propose interpretations/revisions. Current synchronous experiment execution and
conversation interruption handling are insufficient for reliable resume.

Recommended requirements before enabling a loop:

- A durable investigation identity, objective, source/context revisions, bounded
  steps/inference count/time/sample/resource limits and explicit stop conditions.
- Persisted step/attempt states and dependencies, including waiting_for_approval,
  running, completed, failed, cancelled/stopped, plus checkpoint/recovery semantics.
  These labels/models are recommendations, not currently implemented enums/tables.
- Per-tool permission and frozen-specification approval; changed parameters invalidate
  approval. A broad “start” click must not authorize arbitrary future commands.
- Idempotency keys, execution attempts and ownership/leases so restart/retry cannot
  duplicate runs, accepted hypotheses or evidence. Define how to recover an in-flight
  worker without falsely calling it completed or blindly running it twice.
- Actual worker outputs, numerical/method checks and artifact provenance. An invalid
  experiment or unavailable tool becomes a clear blocked/conceptual result, never
  a model-generated measurement or fabricated success percentage.
- Budget exhaustion, quota/rate limits, provider failure and cancellation produce
  inspectable stopped states. No endless retries, recursive inference or hidden
  multi-model debate. Costs remain unknown unless a reliable pricing source exists.
- Human review remains the gateway for accepted scientific changes; bounded autonomy
  can gather approved evidence and create proposals, not silently rewrite the journal.

Reuse the First Heartbeat as the first resumable end-to-end scenario. Add no new
simulator just to demonstrate apparent autonomy. Distributed workers/authentication/
production-grade isolation remain separate scopes unless explicitly requested.

### F. Provenance and epistemic separation across all layers

| Layer | Authority / required distinction |
| --- | --- |
| Researcher journal | Original human record; immutable revision snapshots; source spans |
| Reconstructed graph | Versioned model interpretation of those records; uncertainty and correction history |
| Accelerate suggestions | Novel, pending model proposals with context/provider/model/template provenance |
| Human-reviewed scientific state | Accepted objects/relationships/revisions via kernel transactions |
| Experiment specification | Explicit approved scope, predictions and limits frozen before execution |
| Run/artifact/evidence | Actual computation/observation provenance and performed validation checks |
| Interpretation of findings | New hypothesis/revision proposal; never a mutation of recorded measurements |

No model suggestion, source quotation, renderer node, or graph edge alone establishes
experimental evidence. Preserve who wrote, inferred, corrected, proposed, approved,
executed and validated each change. Keep journal-source revision and hypothesis
content revision identities separate. Do not overload existing epistemic_status
or verification_status with UI selection/novelty/investigation states.

## 11. Recommended Stage 3 implementation sequence

1. **Baseline and schema plan:** inspect status/head/migrations, back up data, run
   unpaid regressions, and choose source-journal and interpretation/correction models.
   Define exact acceptance/provenance semantics before modifying live structures.
2. **Journal vertical slice:** add/reuse stable source entries, comfortable free-form
   editing, autosave completion, revisions and recovery. Preserve legacy structured
   entries, scientific actions and Canvas. Test restart persistence first.
3. **Read-only reconstruction proposal:** bounded source/context snapshots and a typed
   extraction contract with passage references. Validate IDs/spans/roles; render an
   explicitly interpreted graph without treating it as researcher-accepted truth.
4. **Durable reconciliation/corrections:** additive migrations/services for source
   mappings, stable graph identity, human decisions and rationales. Idempotent re-run,
   rejection memory, stale-revision conflicts and non-destructive layout persistence.
5. **Graph review/editing UI:** show source evidence, let users correct interpretations
   and edge direction/type, persist rationales, synchronize all views without reload.
   Extend projection DTOs to carry actual provenance instead of guessing by type.
6. **AI Accelerate proposal slice:** a separate bounded request mode/action, canonical
   novel proposal types (including designed critique semantics), distinct visuals,
   review and existing transactional acceptance. Keep conceptual/executable separation.
7. **Single approved investigation step:** use the registered causal adapter with a
   durable investigation/step record, approved Specification and real evidence.
8. **Bounded resume/stop:** add durable attempts/checkpoints, restart recovery,
   idempotency, cancellation, budgets and understandable blocked/error states.
   Only then allow a bounded multi-step controller to advance approved steps.
9. **Full regression, live and UI verification:** retain First Heartbeat, import,
   provider repairs, proposal/acceptance/stale-revision tests; use temporary live
   projects, and distinguish real browser/account verification from fake-provider tests.
10. **Update docs and handoff:** exact APIs/models/migrations, local startup, operational
    recovery and tested/unverified behavior. Do not silently migrate away prior records.

## 12. End-to-end Stage 3 acceptance criteria

All criteria below are intended future acceptance tests, not claims of current code:

1. A researcher writes a multi-paragraph journal freely, saves it, reloads and gets
   the exact text, stable source identity and recoverable prior revisions.
2. AI reconstructs the existing understanding into a graph with source passage and
   revision references; it labels uncertainty and does not silently add novel beliefs.
3. Nodes/edges are editable. A corrected edge/type/statement and its human rationale
   survive reload, reanalysis and provider changes without silent reversion.
4. Reconstructing the same journal revision is idempotent. Editing the source or graph
   during inference produces explicit conflicts/diffs rather than overwrites.
5. AI Accelerate produces novel, visually distinct reviewable suggestions, including
   hypotheses, relationships, critiques and conceptual/executable experiments as supported.
   The original journal and corrected understanding remain distinguishable.
6. Accept/reject is explicit and idempotent. Accepted records use the existing
   scientific services; rejected content stays inspectable and does not mutate science.
7. An unsupported myopia study is saved only as conceptual design. No fake samples,
   execution or verification labels appear.
8. A First Heartbeat proposal becomes a draft; execution is refused before approval.
   The approved immutable Specification produces real NumPy results, validated
   artifacts and correctly directed evidence graph links.
9. The bounded investigation stops at its configured limits and at unapproved steps.
   A process restart resumes from persisted checkpoints without duplicate runs,
   accepted objects, edges or events. Failure/interruption/cancellation remains visible.
10. A proposed evidence-based revision preserves the original claim and conflicts
    against newer accepted content; its approval, provenance and evidence dependencies
    remain available after reload. Recorded measurements cannot be rewritten by a model.
11. Notebook/journal, Research Graph, Canvas and Intelligence views share consistent
    authoritative identities and update without browser refresh. Manual layout survives.
12. Model provider absence, refusal, quota, timeout, schema/semantic failures and
    invalid references produce recoverable, honest states, with no fabricated fallback.
13. Real provider tests use disposable projects/storage. All unpaid regressions pass;
    paid/live, actual worker, JSDOM, browser visual and touch checks are reported separately.
14. Existing projects, imported IDs, settings, conversations, First Heartbeat history,
    original revisions and graph data survive additive migrations unchanged.
15. No credentials reach the browser/logs, no unrestricted model-generated code runs,
    and local-only security limits remain documented. No commit/push without permission.

## 13. Fresh-session checklist

```text
Read this handoff and the current code; recheck git status and migration head.
Keep current Scientific Kernel, registry, worker and repaired proposal contract.
Treat Stage 3 sections as a plan, not already-created functions/endpoints.
Make journal vs interpretation vs novel proposal vs evidence explicit first.
Add durable correction/rationale and investigation state before claiming resume.
Await saves, protect source revisions, preserve IDs/layout and use kernel services.
Test with temporary data; never reset the real DB or use fake production inference.
Implement one complete vertical slice before broad UI expansion.
```

Further existing references: [Scientific Kernel](SCIENTIFIC_KERNEL.md) and
[Research Intelligence](RESEARCH_INTELLIGENCE.md). Their historical phase notes
are useful context, but the current source and this inspected baseline determine
which functions and endpoints actually exist.
