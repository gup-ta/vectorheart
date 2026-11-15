# Literature Intelligence

Stage 4 connects the existing research graph to verified scholarly records. It
extends the Python kernel, proposal review and Stage 3 worker; it does not introduce
a second scientific graph, a chat-centric workflow or another agent runtime.

## Local startup and configuration

From the repository root, in Windows PowerShell:

```powershell
# Existing virtual environment/dependencies may be reused. First installation only:
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
npm install

# Apply additive migrations before starting/restarting the Python service.
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
npm run dev
```

The usual UI address is http://localhost:3000. These commands do not open a browser.
Restart Python after changing backend code or environment; the usual command has
no reload flag. No packages were added for Stage 4: existing httpx, Pydantic,
SQLAlchemy/Alembic, provider SDKs and React Flow are reused.

Server-side variables in `backend/.env` (process environment takes precedence):

| Variable | Purpose |
| --- | --- |
| `KERNEL_DB_PATH` | Default repository `.vectorheart/kernel.sqlite3`; use the same path for migrations/server |
| `OPENALEX_API_KEY` | Optional OpenAlex access/budget; anonymous basic discovery also works |
| `LITERATURE_CONTACT_EMAIL` | Optional Crossref polite-pool contact; used only by scholarly HTTP requests |
| `GEMINI_API_KEY`, `GEMINI_DEFAULT_MODEL` | Optional Gemini inference, account-supported model |
| `OPENAI_API_KEY`, `OPENAI_DEFAULT_MODEL` | Existing OpenAI inference configuration |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_DEFAULT_MODEL` | Existing Anthropic inference configuration |
| `VECTORHEART_PROVIDER_PRIORITY` | Existing deterministic Automatic routing |
| `VECTORHEART_MAX_OUTPUT_TOKENS`, `VECTORHEART_MODEL_TIMEOUT` | Existing ordinary Intelligence/investigation limits |
| `VECTORHEART_CONTEXT_CHARS` | Existing bounded ordinary project context |

Next server uses `KERNEL_API_URL`, default `http://127.0.0.1:8000`. Keys never use
`NEXT_PUBLIC_`. Literature planning/analysis uses the project's **Literature
Analysis** assignment. Accelerate/investigation retains **General Reasoning**.
Explicit provider selections never silently fall back. Scholarly retrieval remains
usable without any LLM credentials; unavailability does not produce fake responses.

The local SQLite database was consistently backed up in Git-ignored
`.vectorheart/backups` before applying migration 0004. Back up with SQLite's backup
API or with the service stopped; copying only an active WAL database's main file
is not a complete backup. No test project was added to the user's database.

## Scholarly providers and HTTP boundary

- **OpenAlex**: primary discovery with `/works?search=...&per_page=5`, individual
  work/identifier resolution, inverted-index abstract reconstruction, authors,
  dates/venue, access links, reference IDs and explicit retraction flags.
- **Europe PMC**: biomedical search using `format=json`, `resultType=core`,
  `pageSize=5`; DOI/PMID/PMCID matching, abstracts, publication types and OA links.
- **Crossref**: independently resolves returned DOI metadata using `/works/{doi}`;
  verifies the exact returned DOI, supplements identifiers/metadata, records
  reference DOIs and update metadata where available.
- Semantic Scholar is not implemented; it is not required for basic discovery.

The common scholarly adapter interface is separate from model-provider inference.
`scholarly_providers.py` only targets three server-controlled HTTPS origins. No
user/model URL can become a destination. Arbitrary URLs, private addresses and
redirects are not followed; publisher/OA links are displayed for manual inspection,
not downloaded. HTML/JATS snippets are normalized as text, not executed. No PDF,
publisher scraping, paywall bypass or full-text article archive is implemented.

Bounds: at most three planned queries; five records per provider request; eight
network requests including retries/DOI verification; a 45-second retrieval budget;
ten-second request timeouts, two-MB response cap, per-provider pacing and one
transient retry. Retry-After is respected: long waits become a persisted cooldown
and an actionable rate-limit error rather than immediate hammering. Other providers
continue within the remaining shared budget. Results can be partial.

Public response caching is SQLite-backed for 24 hours, bounded to 256 envelopes.
Cache identity excludes credentials/contact information. Original retrieval time is
retained on cached responses. Cache eviction never removes scientific records or
immutable source snapshots. HTTP errors contain safe provider/status messages,
not request URLs with keys, headers or private project text.

Official API documentation checked during implementation:
[OpenAlex API](https://help.openalex.org/api/),
[authentication](https://help.openalex.org/api/authentication/),
[search](https://help.openalex.org/api/searching/),
[Europe PMC REST](https://dev.europepmc.org/RestfulWebService), and
[Crossref REST](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).

## Data model and additive migration

Migration **0004** follows **0003** and adds six supporting tables:

| Table | Role |
| --- | --- |
| `scholarly_sources` | Stable canonical bibliographic identity |
| `source_identifiers` | Unique `(kind,value)` DOI/OpenAlex/PMID/PMCID aliases |
| `source_snapshots` | Immutable normalized content versions, provider, original retrieval time and SHA-256 hash |
| `literature_hits` | Project/run/query/strategy/rank-to-snapshot provenance, deduplicated per run/snapshot/query |
| `project_sources` | One canonical paper-object reference per project/source, pointing into existing `objects` |
| `literature_cache` | Disposable public HTTP-response cache |

Existing scientific tables are retained. Literature investigations reuse
`ResearchRun(kind=literature)`, `ResearchStep`, the leased Stage 3 worker and event
journal. Literature interpretations reuse `ResearchMessage` and `ResearchProposal`
with a registered typed action, `propose_literature_relationship`. Conversation
storage preserves provenance but is not the primary literature UI.

Accepted publications are existing **Concept** research objects tagged
`origin=literature_source`, rendered as Paper nodes. Accepted paraphrased claims
are separate Concepts tagged `origin=literature_interpretation`,
`literature_claim=true`, `source_type=literature`, `verification_status=unverified`.
They have ordinary stable IDs and content revisions; Notebook and Canvas share them.
No local `ExperimentRun` or measured `Evidence` row is fabricated for a publication.

Identifier aliases take precedence over titles. Similar titles are never fuzzy-
merged into authenticated records. No DOI is required if a returned OpenAlex,
PMID or PMCID identity exists. Records without supported verifiable identifiers
are not promoted to verified sources. Conflicting aliases are reported rather than
silently merging unrelated records. Independent provider snapshots remain separate.
Updates preserve old content/hash versions and older proposal anchors.

## Discovery and grounded analysis

**Ground in Literature**, **Challenge with Literature** and **Explore Literature**
are available on Research Graph. Ordinary object inspection offers the contextual
ground/challenge actions. Scope can be an object, Shift-selected objects, selected
relationship endpoints or project context (up to eight target objects).

1. Freeze target object revisions and project event-sequence marker.
2. Ask the configured Literature Analysis model for up to three useful confirmatory,
   contradictory, alternative, methodological or foundational queries.
3. If model planning is unavailable, disclose that and perform a deterministic
   researcher-query/title search. This is metadata retrieval, not pretend inference.
4. Retrieve real API records; rank using query relevance/access to substantive text,
   not citation count as truth. Preserve all returned provenance; expose up to 12
   deduplicated candidates, with at most eight provisional paper nodes on the graph.
5. Analyze at most four source records using actual metadata/abstracts. Context is
   capped at 100000 characters; each supplied abstract excerpt is at most 5000
   characters. Source snapshots retain the bounded available abstract, up to 16000
   characters, never full-text articles.
6. Validate up to six independent findings. Invalid findings are withheld with
   reasons while valid siblings and the normal scientific summary survive.
7. Stage reviewable paper-to-project interpretations; do not mutate the scientific
   graph during discovery/analysis.

`LiteratureAnalysis` output has summary, findings, disagreements and limitations.
Each finding identifies a supplied immutable snapshot and an actual target object,
classification, paraphrased claim, scientific rationale, exact short source anchor,
limitations, method notes and missing information. The canonical
`LiteratureAssociation` stores source/snapshot IDs, access level and exact character
offsets. Anchors must match the actual retrieved text and fall within what the model
was supplied. Numerical claims/method descriptions cannot introduce numbers absent
from the source. These mechanical checks do not prove semantic entailment.

Supported classifications: supports, challenges, qualifies, alternative_explanation,
method, background, insufficient_information, cites. Metadata/title-only records
cannot support clinical/scientific findings: only background/insufficient information
or independently verified bibliographic citations are allowed. A `cites` edge
requires an API-reported reference matching the verified target paper's aliases;
it never implies agreement. The six existing canonical relationship types are kept;
finer literary classifications live in edge metadata and readable labels.

All external text is explicitly untrusted data in versioned system instructions.
Actual methods/design/population/uncertainty must come from accessible content;
missing details remain missing. Retraction flags and provider update information
are retained, with unknown/not-flagged distinguished from a guarantee of validity.
Disagreement summaries may explicitly say no genuine contradiction was established.
Adversarial search does not force a dramatic or invented disagreement.

## Review, graph integration and scientific authority

Candidate papers and dashed proposed connections appear directly in the current
Canvas renderer. Paper nodes have restrained distinct styling; existing green
Accelerate proposals retain their styling. Node/edge inspection shows identifiers,
authors/date/venue/type, source links, available abstract, scientific rationale,
access level, caveats and provenance. DOI resolution and Save paper reference work
without model analysis. Saving a reference asserts existence, not support.

Accept/reject uses existing Intelligence/Stage 3 review endpoints. Acceptance:

- Revalidates source scope, immutable snapshot, anchor and target revision.
- Reuses/creates a project Paper Concept through `add_object()` and its initial
  revision; repeated saves do not create duplicate paper objects.
- Creates/reuses the accepted claim Concept. Identical accepted snapshot/target/
  classification/claim combinations are reused across repeated searches.
- Adds claim `derived_from` paper provenance, then paper → target supports,
  challenges or related_to with the precise classification, rationale, claim ID,
  limitations and model/snapshot provenance in edge metadata.
- Retains multiple assessments on an edge; opposite supports/challenges remain
  separate links. No conflict is resolved by automatically choosing a winner.
- Places new paper/target nodes without moving existing positions; claims are also
  available through Notebook/Place existing entry without graph clutter.
- Records an immutable-by-API scientific acceptance event. Repeated acceptance of
  the same proposal returns its stored result IDs.

Rejection retains conversation/proposal history and optional rationale. Future
analysis sees prior reviews; disconnected researcher-rejected source→target/type
links remain deterministically blocked until explicit human reconnection.
Scientific object/source revisions and hashes remain inspectable after reload.
Source artifacts and accepted literature claims cannot be silently rewritten via
the ordinary content editor; obtain a fresh analysis/review instead.

Stale target revisions conflict instead of overwriting newer research. Accepted
literature claims may motivate the existing Modify/revision workflow, but only
when validated as accepted, source-grounded claims linked to that hypothesis.
Bare paper IDs, model suggestions or fabricated metadata cannot masquerade as
measured Evidence. Revisions remain unresolved/scoped, preserve old content and
record their external-source dependency; publication existence never proves a claim.

## Literature-aware Intelligence and Accelerate

The existing context builder supplies bounded actual literature, access labels,
source hashes, accepted/rejected interpretations and canonical paper/claim IDs.
Accelerate uses that content along with the journal, scientific graph and corrections.
Canonical scientific proposals can include `literature_source_ids`; readable
responses separately carry `literature_references`. Accepted proposals preserve
source snapshot references in model provenance and link canonical source objects
using the existing kernel. Their novelty is relative to retrieved sources, never
an unsupported claim that nobody has previously discovered the idea.

Reference-role normalization fixes a live integration mismatch: a model sometimes
places an actual supplied source/snapshot/DOI alias in an object-reference field.
Only exact aliases from verified supplied records can move to the separate
literature-reference field. No fuzzy matching, invented DOI, new source or missing
scientific rationale is supplied. Unknown/out-of-project IDs still fail validation.
The existing repaired Gemini transport and canonical per-proposal checks remain.

## Read-only tools in the existing investigation loop

The actual Stage 3 leased worker discovers four additional registered tools:

- `literature.search`: bounded real discovery and DOI verification.
- `literature.resolve_identifier`: verified DOI/PMID/PMCID/OpenAlex resolution.
- `literature.inspect_source`: inspect an already project-scoped verified source.
- `literature.find_related`: resolve up to two actual returned bibliography IDs;
  with no reference list, explicitly labeled related-title discovery.

Model responses may contain one typed `tool_request`; no arbitrary action name,
URL destination, code or filesystem path is supported. The tool request is validated
before a `ResearchStep(kind=literature_tool)` is queued. Actual public retrieval
executes outside the database lock, snapshots/results are checkpointed, and the
same worker reasons again over real returned records. No research-object creation
or scientific acceptance occurs as a side effect of this read-only tool.

All tool-returned sources visible in the trace are also in the explicit citation
allowlist. Trace copies are compacted to avoid duplicating full abstracts. Global
source metadata caching never exposes another project's private interpretations.
Cross-project source access requires independent retrieval or an accepted reference
in the current project.

Existing investigation limits are unchanged: up to five model steps, default three;
at most three total tool submissions, shared between literature and computation.
Each literature tool also has a bounded network budget. Actual experiments still
require a registered domain-appropriate adapter, frozen specification, explicit
human approval and the original trusted executor. Clinical myopia is not tested
by the synthetic causal simulator. An unavailable experiment remains conceptual.

## Persistence, outages and recovery

Planning, retrieval and analysis have separate durable checkpoints. A model failure
does not discard retrieved sources or rewrite research. Retry resumes from stored
queries/hits; **Analyze available sources** starts a new analysis over preserved
snapshots, records its parent run and uses zero new scholarly requests. Long rate
limits produce cooldowns; no uncontrolled retries or silent provider substitution.
Cancellation stops further reasoning while retaining real retrieval history.

The Stage 3 worker's database lease/checkpoint rules still apply. A full backend
crash during an uncommitted scientific execution requires explicit recovery rather
than blind replay. Read-only fetches can be repeated within remaining budgets and
are deduplicated by cache/identifier/hit constraints. This is local orchestration,
not a secure distributed durable job system.

## API inventory

Browser calls use existing `/api/kernel/v1/...`; backend routes below are `/v1`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/literature/providers` | Safe scholarly capabilities/limits, no keys |
| GET | `/literature/tools` | Actual read-only tool registry |
| POST | `/projects/{pid}/literature/runs` | Start idempotent ground/challenge/explore |
| POST | `/projects/{pid}/literature/runs/{rid}/analyze` | New analysis over preserved sources |
| GET | `/projects/{pid}/literature/sources?run_id=...` | Scoped deduplicated candidates |
| GET | `/projects/{pid}/literature/sources/{sid}?snapshot_id=...` | Inspect source/version/interpretations |
| POST | `/projects/{pid}/literature/sources/{sid}/save` | Human save of a paper reference |
| POST | `/projects/{pid}/literature/resolve` | Validated identifier resolution |

Existing `/projects/{pid}/research-runs` list/read/proposals/resume/cancel and proposal
accept/reject endpoints cover literature runs. Existing `/intelligence/proposals/
{id}/accept` dispatches the typed literature action to its transactional handler.
Existing objects/relationships/revisions/events APIs expose accepted scientific state.

Important files: `scholarly_providers.py`, `literature_models.py`,
`literature_schemas.py`, `literature.py`, migration `0004_literature.py`, and frontend
`literature-intelligence.tsx`. Narrow extensions to `intelligence*`,
`gemini_transport.py`, `research_context.py`, `stage3.py`, `main.py`,
`research-canvas.tsx` and `graph-intelligence.tsx` preserve the existing infrastructure.

## Verification and manual demonstration

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm test
npm run lint
npm run typecheck
npm run build
backend/.venv/Scripts/python -m compileall -q backend/app backend/workers
backend/.venv/Scripts/python -m pip check
```

Deterministic tests use recorded public metadata for the CC-BY PLOS ONE article
with DOI **10.1371/journal.pone.0181772**. Fixture inference is explicitly test-only;
normal app operation has no mock provider fallback. Tests cover normalization,
alias deduplication, immutable snapshots, HTTP limits/cache/redirect rejection,
grounding/numerical checks, acceptance/rejection/stale data, source isolation,
outage recovery, readonly tools, source-aware Accelerate, shared graph persistence
and existing First Heartbeat/Stage 3 behavior.

Opt-in live backend checks, never the user's projects:

```powershell
# Public scholarly APIs, no model required:
backend/.venv/Scripts/python backend/tests/live_stage4.py --retrieval-only
# Also exercise source inspection and actual reference-list discovery:
backend/.venv/Scripts/python backend/tests/live_stage4.py --retrieval-only --tools
# Full sequence; permits at most seven real configured Gemini requests:
backend/.venv/Scripts/python backend/tests/live_stage4.py --verify
```

`--focus intelligence` and `--focus agent` isolate those model workflows for
diagnosis. Live verification succeeded with **gemini-3.5-flash-lite** selected from
the server configuration: real planning/grounded acceptance, adversarial search,
literature-aware Accelerate/acceptance and agent-selected real retrieval followed
by actual-source-grounded reasoning. The final full sequence passed with seven
model calls. OpenAlex, Europe PMC and Crossref returned real records; an invalid
DOI returned 404 without creating a verified source. No browser was launched or
automated. UI pointer/visual verification remains a manual responsibility.
The registered source-inspection and related/reference discovery paths were also
verified live, resolving two actual bibliography records without inferring agreement.

Manual workflow after startup:

1. Create a disposable project and hypothesis about outdoor light exposure and
   childhood myopia independently of digital screen use. Choose a configured
   Literature Analysis model; project defaults can use Automatic.
2. In Research Graph, select the hypothesis (or choose it in Search scope), then
   Ground in Literature. Inspect candidate paper nodes/abstract scope and proposed
   rationale; accept one relationship. Reload and inspect its history.
3. Challenge with Literature. Read alternative explanations/methodological limits;
   do not expect a genuine contradiction when the retrieved evidence cannot establish one.
4. Run AI Accelerate. Inspect the novel proposal and its source references, then
   accept it into Notebook/Canvas through the existing human review path.
5. In a separate project, begin a bounded investigation that first searches the
   literature and then proposes a useful next hypothesis/design. Inspect its real
   tool results and follow-up reasoning; no unsupported clinical experiment runs.
6. Resolve `10.9999/vectorheart-nonexistent-reference-987654321`; inspect the safe
   not-found error. No verified paper should appear for that fabricated identifier.

## Scientific and deployment limitations

- Metadata and abstracts only; no automatic full-text/PDF ingestion or Semantic
  Scholar adapter. Links to lawful OA content are supplied for manual inspection.
- Bibliographic verification establishes returned identity, not study quality,
  peer review, causal truth, independent replication or individual medical advice.
- Exact anchors/numeric/reference checks reduce fabrication; semantic interpretation
  and contradictions still require researcher judgment. No calibrated truth score.
- Search is bounded and API-dependent. Absence from retrieved literature is not
  evidence of global novelty. Ranking is not a comprehensive systematic review.
- No automatic reconciliation of disputed findings or silent scientific revisions.
- Existing local-only, unauthenticated security boundary remains. Bind Python to
  loopback. CORS/proxy restrictions do not make this safe for public multi-user use.
- No browser automation was used. Researchers should manually assess responsiveness,
  pointer interactions and source-inspection ergonomics before public demonstrations.

## Recorded verification

Implementation verification on 2026-11-15:

- Backend suite: **80 passed**, including all existing Scientific Kernel/Stage 3
  regressions and real NumPy execution. One existing Starlette/AnyIO deprecation warning.
- Frontend/component suite: **23 passed**; no browser automation or screenshot claims.
- ESLint, TypeScript, production Next.js build, Python compilation and `pip check`
  passed. Local Alembic reports **0004 (head)** after the pre-migration backup.
- Live OpenAlex discovery/work lookup, Europe PMC core discovery and Crossref DOI
  resolution succeeded. Invalid DOI resolution returned **404**, with no fabricated
  source. Read-only inspection and reference discovery resolved two actual records.
- The complete live Gemini sequence passed with **seven real requests** using
  `gemini-3.5-flash-lite` from server configuration. This covered grounded review,
  acceptance/idempotency, adversarial queries, source-aware Accelerate/acceptance,
  autonomous scholarly-tool selection and actual-record follow-up reasoning.
- All live checks used temporary databases and disposable synthetic projects.
  OpenAI/Anthropic adapters were preserved/regression-tested, not live-account tested.
