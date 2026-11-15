# Living Research Graph and bounded investigation

Stage 3 extends the existing scientific kernel. It does not add another scientific
database, provider implementation, or arbitrary-code execution path. The subsequent
[Stage 4](STAGE4.md) now adds literature retrieval and read-only scholarly tools;
this document describes the retained Stage 3 foundation.

## Start locally (Windows PowerShell)

From the repository root, with the existing Python virtual environment and npm
dependencies installed:

```powershell
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm run dev
```

Open http://localhost:3000. Restart an already-running Python service after code or
environment changes. No additional packages are required. First installation:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
npm install
```

Keep provider keys/default models in `backend/.env`; process environment overrides
that file. Existing project model assignments remain authoritative:

- Graph extraction uses **Conceptual Synthesis**.
- Accelerate/investigation use **General Reasoning**.
- Automatic routing uses `VECTORHEART_PROVIDER_PRIORITY` and correctly configured
  server defaults; explicit providers never silently fall back.
- Set the appropriate `OPENAI_API_KEY` / `OPENAI_DEFAULT_MODEL`,
  `GEMINI_API_KEY` / `GEMINI_DEFAULT_MODEL`, or
  `ANTHROPIC_API_KEY` / `ANTHROPIC_DEFAULT_MODEL`.
- `KERNEL_DB_PATH` must match between migrations and the server. Default:
  `.vectorheart/kernel.sqlite3`. `KERNEL_API_URL` is Next-server-only and defaults
  to `http://127.0.0.1:8000`. Existing inference limits still apply.

Back up an existing database using SQLite's backup API or with the service stopped
before migrating. Do not discard its WAL file during an active copy. The local
database was backed up into Git-ignored `.vectorheart/backups` before applying this
implementation's migration.

## Data and provenance

Migration **0003**, following 0002, only adds:

- `research_runs`: graph/accelerate/investigate identity, request idempotency,
  source snapshot/revision pointers, configuration, output preview, counters,
  database lease, status/error and timestamps.
- `research_steps`: ordered, uniquely numbered per-run checkpoints, model-message
  and operation references, input/result metadata and completion state.
- `graph_corrections`: immutable-by-API human decisions, rationales, before/after
  records, source revisions and object/endpoint references. Relationship removal
  keeps the original row's contents here after removing it from the active graph.

Journal entries are ordinary versioned Note objects with `journal_entry=true`,
`origin=researcher_record`, tags and optional linked IDs. They remain readable
without any AI. Every accepted save creates a meaningful content/metadata revision
through `revise()`. A base-revision conflict preserves the editor draft and requires
explicit review before overwriting the latest saved version.

The journal saves after 1.5 seconds of inactivity; the workspace's existing
10-second flush bounds continuous writing. Registered journal savers participate
in `WorkspaceProvider.sync()` before model actions, navigation flushing and backend
refresh. Saving retains local focused text/caret. Page lifecycle saves are best
effort HTTP requests; a forced browser/process termination can lose an unsent
draft. There is no second authoritative localStorage journal. For large writes,
the fetch helper avoids the browser's keepalive body-size limit.

Canonical accepted objects/relationships stay in the existing tables, and are shared
by Notebook and Canvas. Existing scientific revisions, events, specifications,
runs, Evidence and frozen approval hashes remain in use. Model interpretations
carry source passages (object ID, revision, excerpt, offsets), uncertainty labels,
model/provider/run provenance and `verification_status=unverified`. Human acceptance
records agreement to store an interpretation, not scientific verification.

## Journal to Research Graph

Write ordinary dated entries in Notebook; structured editing and First Heartbeat
remain available below the journal. In Research Graph, choose **Generate Research
Graph** (or **Update Research Graph**). The provider/model beneath that control is
resolved from the existing Conceptual Synthesis assignment.

The server snapshots every active project object, its complete body, current
revision, graph, human corrections, event labels and accepted/rejected proposal
reviews. It never scans arbitrary files. Long records are divided into 6000-character
source spans and packed into approximately 14000-character passage batches. Each
batch retains its object/revision identity; later batches see earlier interpretations
as reusable identities for cross-entry consolidation and linking. This is a bounded
map/accumulate extraction, not a last-N-notes filter or vector search.

Graph output uses `GraphExtraction`: source-grounded nodes and typed edges, concise
rationales and explicit/inferred/uncertain interpretation labels. Gemini receives
a compatible non-forbidding transport; responses are checked for field bounds,
actual project endpoints, exact source excerpts/revisions, allowed canonical types,
duplicates and durable human rejection constraints before staging. Recorded
experiments/results are represented by existing objects or unverified concepts;
extraction cannot create kernel Evidence or an executed Experiment.

The preview is visible directly on the graph with dashed outlines. Inspect a node
or edge to see its rationale and original source. **Accept graph interpretation**
atomically checks the source/correction snapshot, creates new canonical objects
and relationships, records an event and places previously unplaced interpretations.
Existing content and positions are preserved; no whole-graph rearrangement occurs.
New placements use a restrained deterministic grid beside the existing layout.
Existing identities, exact content matches and extraction fingerprints are reused.
Model-assisted semantic consolidation is not a guarantee of perfect deduplication.

Rejecting a preview stores rejection fingerprints and the optional rationale.
Incremental updates do not silently reintroduce those interpretations. If sources
or corrections change during generation, accepting the stale preview conflicts;
generate a fresh preview rather than overwriting newer work.

## Researcher corrections

Select/Connect/Disconnect remain the three Canvas tools. The two-click workflows
ask for an optional rationale. A connection creates only a relationship. Disconnect
removes only the selected edge; when multiple directed/typed links connect a pair,
the existing relationship chooser remains available. Escape/mode changes clear
unfinished selections. Research objects are not deleted by disconnection.
Canvas changes update React state immediately and use the existing buffered
mutation queue; model actions/navigation await that queue before reading scientific
state. Client-assigned correction/edge IDs make retries idempotent, including
relationship deletion without duplicate correction history.

An extracted node's inspector and Notebook editor provide **Save researcher
correction** for its type, title/content and rationale. This records before/after
content and a new revision. Journal and recorded Experiment/Evidence content cannot
be rewritten through this correction API. Original sources remain separately
accessible. Ordinary researcher-authored structured objects still use their
existing editor.

Future extraction and Accelerate receive the correction records. A deterministic
server check prevents recreating a rejected source→target/type relationship.
Only an explicit human reconnection lifts that constraint. A different scientific
relationship is not silently treated as the same typed link; scientifically valid
reconsideration still requires human review. Source-grounding checks validate
references/excerpts, not the semantic truth of every model interpretation.

## AI Accelerate

**AI Accelerate** performs bounded project-aware inference through
`intelligence.perform_turn()`, the existing official provider adapters, canonical
proposal validation and `ResearchProposal` persistence. It requests novel,
informative Construct/Connect/Destroy/Modify/Experiment suggestions. A critique
is represented as an uncertainty question rather than an unconstrained new action.
It can return no proposals when justified. Exact duplicate statements/edges are
withheld with diagnostics.

Pending suggestions appear as restrained green, dashed nodes/edges on the Research
Graph, not as accepted research objects or a chat-centric experience. Click to
inspect scientific justification, source links, assumptions, predictions,
limitations, revision differences and executability. Accept/reject individually;
optional review rationales persist. A secondary run summary retains history and
review controls even after the provisional overlay disappears.

Acceptance reuses the existing transactional Intelligence/kernel pathways.
Accepted objects receive model/run provenance, become visible in Notebook and
are placed on Canvas. Relationship acceptance uses the same scientific graph.
References are revalidated against saved source revisions; stale proposals conflict.
Repeated acceptance returns the same IDs. A conceptual study becomes an explicitly
marked Note. An executable experiment becomes a **draft**, requiring separate
specification approval and execution.

## Bounded autonomous investigation

Open **Investigate with tools**, write an objective and choose up to five reasoning
steps (default three). A run is a real model-selected next-action loop:

1. Persist source context, resource limits and a leased run identity.
2. Ask the routed provider for the best next action using current project state,
   actual registered adapter schemas/restrictions, earlier steps, corrections,
   reviewed proposals and any real evidence.
3. If it chooses a valid executable experiment, create one draft through `propose()`
   and pause at `awaiting_approval`. There is no model-to-executor shortcut.
4. Show purpose, parameters, analytical predictions, measurement/validation plans
   and the registered synthetic scope. **Approve experiment & resume** calls the
   original kernel approval boundary. Rejecting stops without executing.
5. Reconcile the operation's saved state, execute only an approved operation via
   `main.execute()`, preserve the real NumPy outputs/checks, and place the resulting
   Experiment/Evidence objects without moving existing nodes.
6. The next model request receives the actual measured evidence, parameters,
   verification status and machine-readable execution trace. The model decides
   whether another informative experiment is needed or final proposals suffice.
7. Final hypotheses, links and evidence-based revisions remain human-reviewable.
   A revision preserves the original content and checks its current revision.

There is no hardcoded experimental sequence or mock result in normal execution.
The only executable adapter is `toy.causal_intervention.v1`, with the existing
`causal_demo` scope gate, sample/parameter bounds, frozen hash, fixed subprocess,
15-second timeout and numerical validation. It cannot execute a clinical myopia
study. Synthetic evidence remains `simulation` / `execution_checked`, never proof
about a real population. Unsupported experiments remain conceptual.

Per-run limits: 1–5 reasoning calls, at most three tool executions, 240 accumulated
active seconds and 40000 reported tokens. Single calls also obey existing output
and timeout limits. Stage 3 disables automatic transport/correction retries; a
human retry consumes another model-call allowance. The two-worker local pool and
120-second database leases prevent concurrent advancement of the same run.
Unknown token usage stays unknown; no cost estimate is invented. No recursive
agent debate, arbitrary shell/Python, new simulator or unapproved execution exists.
Reported-token and accumulated-time thresholds are checked between bounded calls;
an in-flight call can cross a threshold. The request/step/tool counts and individual
output/timeout limits provide the hard execution bounds; this is not a billing cap.

Graph extraction separately allows 64 passage batches / 4 MB snapshot / 900 active
seconds. Over-limit projects fail explicitly instead of silently ignoring old
notes. Larger Accelerate/investigation contexts require an up-to-date complete
graph source map first; the final reasoning context has a 100000-character safety
cap and fails clearly if it cannot fit. This bounded local prototype is not
unlimited-scale distributed research infrastructure.

### Recovery semantics

Run/step/operation/message IDs and budgets are in SQLite. **Resume / recover**
reacquires an expired/released lease and reconciles checkpoints. It does not repeat
a completed operation, replay a finished run or bypass a pending approval.
Cross-process resume of an approved checkpoint is covered by a real subprocess
test with actual NumPy execution.

If the entire backend crashes during a trusted subprocess execution and no result
was committed, the operation remains `running`. Recovery deliberately stops as
`interrupted` instead of assuming success or blindly executing twice. Inspect the
operation/run and recover with an explicitly approved new attempt; fully automatic
orphan-worker reconciliation is not implemented. Likewise an interrupted inference
can require the existing conversation's 180-second interruption recovery before
retry. Resume is user-triggered after restart; this is not a deployed durable queue.
Stopping a run prevents further reasoning; an already-approved worker may finish
and retain its actual evidence. It cannot erase an executed experiment.

## New endpoints

All paths below are under `/v1/projects/{pid}`; browser calls use the existing
same-origin `/api/kernel/v1/...` proxy. Project ownership is checked server-side.

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/journal` | Read/create dated journal Notes |
| PATCH | `/journal/{oid}` | Version-checked title/body/tags/links save |
| GET, POST | `/graph/corrections` | Read/record human graph corrections |
| GET, POST | `/research-runs` | Read recent runs / idempotently start |
| GET | `/research-runs/{rid}` | Run state, source revisions, trace |
| POST | `/research-runs/{rid}/resume` | Resume/reconcile a checkpoint |
| POST | `/research-runs/{rid}/cancel` | Stop further work |
| POST | `/research-runs/{rid}/approve` | Explicitly approve pending experiment and resume |
| POST | `/research-runs/{rid}/accept-graph` | Atomically accept current graph preview |
| POST | `/research-runs/{rid}/reject-graph` | Reject preview, retain rationale/constraints |
| GET | `/research-runs/{rid}/proposals` | Canonical reviewable proposals for run |
| POST | `/research-runs/{rid}/proposals/{proposal_id}/accept` | Accept via existing scientific services |
| POST | `/research-runs/{rid}/proposals/{proposal_id}/reject` | Reject, optionally explain |

`GET /v1/adapters` now also describes output schema, supported domain, approval
requirement and execution limits. Existing routes are retained. Journal/object
history uses the existing `/objects/{oid}/revisions` endpoint. The ordinary
Intelligence acceptance endpoint also reuses an investigation's prepared draft
instead of creating a second operation.

## Source map

- `backend/app/stage3.py`: journal/correction APIs, corpus batching, graph preview
  validation/acceptance and durable investigation orchestration.
- `stage3_models.py`, `stage3_schemas.py`, `migrations/versions/0003_living_research.py`:
  orchestration storage and contracts; existing scientific tables are untouched.
- `intelligence.py`: reusable inference entry point, stage-run provenance,
  scientific review, stale-reference and correction guards.
- `model_providers.py`: existing SDKs; Gemini retains its repaired canonical
  transport, with the separate source-extraction schema for graph requests.
- `research_context.py`: existing scientific context plus correction constraints.
- `src/components/research-journal.tsx`: writing-first editor, save barrier/history.
- `graph-intelligence.tsx`: run controls, spatial proposal projection, review,
  approval and summaries; no provider inference in the browser.
- `graph-correction-editor.tsx`, `research-canvas.tsx`: human graph correction,
  source inspection, live graph overlays and retained Canvas tools.
- `workspace-provider.tsx`: existing optimistic queue plus registered journal savers.

## Verification and demos

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm test
npm run lint
npm run typecheck
npm run build
backend/.venv/Scripts/python -m compileall -q backend/app backend/workers
backend/.venv/Scripts/python -m pip check
```

Backend tests use deterministic providers but exercise real persistence, revisions,
cross-project isolation, stale references, graph corrections, resource/lease limits,
conceptual experiments, human approval and actual NumPy measurements. A separate
Python process resumes an approved investigation. Frontend JSDOM tests use a
disposable real kernel and explicit test-only inference fixtures; they cover
journal autosave/reload, graph review, proposal overlays, acceptance and existing
First Heartbeat regression. They do not prove visual/mobile pointer behavior.

Opt-in paid verification, using configured Gemini credentials and a temporary DB:

```powershell
backend/.venv/Scripts/python backend/tests/live_stage3.py --verify
```

Use `--focus graph` to isolate extraction/update or `--focus discovery` to isolate
Accelerate/experimentation. The script enforces at most seven provider calls per
invocation, including its bounded availability retry.

The live script covers synthetic myopia diary → graph → human correction → update,
Accelerate hypothesis acceptance, and a separate First Heartbeat investigation →
approval → actual execution → evidence-based revision. It permits one bounded
availability retry and never switches the selected model. An external 503 is a
failed live check, not a simulated pass. Normal inference has no fake fallback.

For manual use:

1. Write two illustrative journal entries about outdoor light, screen time and
   near-work. Generate and inspect the graph; accept its interpretation.
2. Disconnect an inappropriate edge, explaining that only correlation was reported.
   Update the graph and check the decision/history.
3. Choose AI Accelerate. Inspect a green provisional hypothesis or link, then accept
   or reject it. Confirm the accepted object in Notebook and Research Graph.
4. In a **separate project**, use Notebook's **Try the First Heartbeat**.
5. In Research Graph, begin a bounded investigation to distinguish the supplied
   A/B causal worlds. Review the agent-selected synthetic intervention and approve.
6. Inspect the real experiment/evidence and the next evidence-grounded proposals.
   Accept a scoped revision; reload to inspect its earlier content and run history.

## Current limitations and security boundary

- Local, single-user, unauthenticated service only. Bind to loopback; Origin checks
  and the Next proxy do not make this safe for public deployment.
- The trusted worker is not a sandbox for arbitrary code. Models never write
  directly to scientific tables or change recorded numerical measurements.
- Semantic extraction/novelty is fallible; source/excerpt checks do not establish
  entailment or scientific truth. Human review remains essential.
- Positioning is a deterministic grid for new nodes, not an optimized graph-layout
  engine. Very dense graphs need manual arrangement and zoom.
- Graph preview acceptance is atomic for the entire validated interpretation;
  Accelerate proposals are individually reviewable. Bulk selected-proposal review
  and historical graph replay are not implemented.
- Very large corpora fail at documented limits; no vector DB or unbounded hidden
  inference. Full project snapshots stay server-side for audit and use local disk.
- A browser killed before an HTTP journal save completes can lose an unsent draft.
  An orphaned running scientific worker requires explicit recovery as above.
- OpenAI/Anthropic retain their existing adapters; live connectivity requires the
  user's corresponding account and was not inferred from fake-provider tests.
- Literature search, external evidence retrieval, remote execution, authentication,
  distributed scheduling and Stage 4 are outside this implementation.

## Verification record — 2026-11-15

- `python -m pytest backend/tests -q`: **63 passed**; one existing Starlette/AnyIO
  deprecation warning. These include actual NumPy execution and fresh-process
  checkpoint resume, with deterministic inference fixtures.
- `npm test`: **21 passed**, including existing First Heartbeat and Intelligence
  regression, journal save/reload, preview/acceptance, provisional graph projection
  and immediate-but-buffered connection/disconnection corrections.
- `npm run lint`, `npm run typecheck`, `npm run build`, Python compile/import
  checks and `python -m pip check`: passed during implementation.
- Local migrations applied successfully; `alembic current` reports **0003 (head)**.
  The existing SQLite database was backed up first; synthetic/live tests used
  separate temporary databases, not user projects.
- **Live Gemini** (`gemini-3.5-flash-lite`, selected from configured environment):
  journal extraction, source provenance, graph acceptance, researcher link removal,
  incremental update and rejection preservation succeeded. The live Accelerate
  stage subsequently failed with genuine HTTP **503 high-demand/overload** errors,
  including a bounded retry. A focused discovery retry was also blocked by 503.
  Full live Accelerate/agent/revision completion is therefore **not verified**.
  No response was simulated or silently routed to a different provider.
- Production Next.js and FastAPI preview services started using disposable data.
  Visual browser checks could not complete: the browser automation host was
  unavailable and Windows browser automation stopped because URL-policy
  enforcement is unsupported. Actual pointer geometry, mobile layout and visual
  review remain manual checks; JSDOM results are not presented as browser tests.
