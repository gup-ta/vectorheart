# Research Intelligence v0.1

Research Intelligence reasons over a bounded snapshot of a project and returns
reviewable scientific proposals. Model providers have no database access, tool
execution, or approval authority. The existing First Heartbeat computation,
scientific objects, operations, evidence and revision journal remain authoritative.

## Windows PowerShell setup

From the repository root, stop an existing kernel before updating its packages.
Existing SQLite records are preserved by additive migration `0002`.

```powershell
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
Copy-Item backend/.env.example backend/.env  # only if backend/.env does not exist
# Edit backend/.env locally: set at least one real API key and account model ID.
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm install
npm run dev
```

Open http://localhost:3000. New installations first create the virtual environment
with `python -m venv backend/.venv`. The kernel loads `backend/.env` using
python-dotenv; process environment variables take precedence. Restart the Python
service after changing credentials or model defaults. No new startup service is needed.

Variables (all credentials remain on the Python server):

| Variable | Meaning |
| --- | --- |
| OPENAI_API_KEY / OPENAI_DEFAULT_MODEL | OpenAI credential and account-supported model |
| ANTHROPIC_API_KEY / ANTHROPIC_DEFAULT_MODEL | Anthropic credential and model |
| GEMINI_API_KEY / GEMINI_DEFAULT_MODEL | Gemini credential and model |
| VECTORHEART_PROVIDER_PRIORITY | Ordered names, default OpenAI,Google Gemini,Anthropic |
| VECTORHEART_CONTEXT_CHARS | Project context characters; default 24000, clamped 4000–48000 |
| VECTORHEART_MAX_OUTPUT_TOKENS | Output limit; default 3000, clamped 256–8000 |
| VECTORHEART_MODEL_TIMEOUT | Overall adapter budget in seconds; default 30, clamped 5–40 |
| KERNEL_DB_PATH | Existing database location override; same value for migration/startup |
| KERNEL_API_URL | Next server only; default http://127.0.0.1:8000 |

No model ID is assumed valid for an account. Automatic routing chooses the first
provider with a nonempty key and server default model, according to priority.
Explicit project provider assignments use that provider's project model ID, then
its server default. Explicit selection never falls back. Custom remains unavailable.
Capabilities report configuration, not verified connectivity or account permissions.
Reported SDK token usage is stored; estimated cost is null (no pricing assumptions).

## Provider APIs

`model_providers.py` implements one request/response protocol. SDK adapters are
the only modules importing OpenAI, Anthropic or Google GenAI clients. They receive
instructions, user request, structured context, history, model, schema, token limit
and timeout, and return parsed structured output plus reported usage.

Native SDK paths verified against official documentation and installed signatures:

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs):
  `responses.parse(text_format=ResearchIntelligenceResponse)`, no tools, `store=False`.
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs):
  `messages.parse(output_format=ResearchIntelligenceResponse)` sends native schema output.
- [Google GenAI Python SDK](https://github.com/googleapis/python-genai):
  `models.generate_content` with JSON MIME type and a Gemini-specific Pydantic
  transport `response_schema`, followed by strict canonical validation of raw JSON.
  The transport omits `additionalProperties`: the installed SDK converts the
  canonical `extra='forbid'` setting to `additional_properties`, which the live
  Gemini endpoint rejects as an unknown field. Canonical schemas remain strict.
  Invalid proposal payloads are withheld individually without fabricating fields.

Models vary in native schema support. Unsupported model/schema, refusal, truncation,
authentication, rate limit, timeout, malformed output and network failures produce
sanitized recoverable message records; SDK exception bodies are never exposed.
SDK automatic retries are disabled. At most one immediate retry is allowed for
network/service failures and timeouts within the adapter's budget. Authentication,
schema errors and rate limits are not retried automatically. No recursive inference
or automatic scientific execution occurs. Two local inference slots bound concurrency.

## Context and scientific constraints

`ResearchContextBuilder` queries only the active SQLite project. Order: selected
object, one-hop neighbors, important/relevant scientific objects, recent objects.
It includes project title, description, question and field; current content and
allowed scientific metadata; graph relations; actual evidence summaries, parameters
and verification checks; recent event labels; and up to eight completed messages.
History messages are excerpted to 1500 characters each, separate from the project
context budget. Raw sample arrays and import backup payloads are not sent.

Source content and prior messages are untrusted data in a JSON payload, separated
from versioned system instructions `research-intelligence.v1`. Whole JSON objects
are omitted to fit the budget, with field excerpts and truncation explicitly marked.
Stable IDs, current revision numbers and revision IDs are retained in the saved
message's context provenance. Model references must be a subset of supplied IDs.
Known environment credential values are redacted if pasted into context/history.
The model cannot infer that it saw omitted context. This is deterministic retrieval,
not semantic search. Prompt separation reduces injection risk but does not establish
the scientific correctness of generated prose; human review remains essential.

The common Pydantic response contains answer, uncertainties, context references,
zero to three proposals, and limitations. Proposals have bounded text/arrays and
six allowed actions: create_question, create_hypothesis, create_observation,
propose_relationship, propose_experiment, propose_revision. Backend-generated IDs, status and provenance cannot be chosen by
the model. A malformed overall response fails the turn. Semantically invalid
proposals (missing/foreign references, wrong target, invalid adapter parameters,
missing revision evidence) are withheld individually with a recorded reason.

The live proposal-generation repair found a contract mismatch: Gemini's former
transport exposed an unrestricted action string, and the system prompt omitted the
canonical action identifiers. The requested Formalize and Design Experiment modes
therefore produced `formalize_hypothesis` and `Design Experiment`, both correctly
rejected by the canonical `action_type` enum. The transport now reuses the same
`ProposalAction` enum as canonical validation. `proposal_contract()` derives model
instructions from that canonical schema, including exact action names, bounds,
source/target rules and clinical/conceptual versus executable tool scope.

If a proposal has a repairable formatting/action-name problem, a turn permits one
targeted correction request. That request gets the precise field errors, the
supported schema, the same context, and only invalid candidates. Transport retries
are disabled for this correction. Corrected proposals must preserve scientific
statements, titles, assumptions, predictions, limitations, references and numeric
parameters exactly; no missing scientific reasoning or sources are manufactured.
Valid siblings and the original explanation are retained. Raw invalid candidates
are used only in memory; persisted rejection details contain field-level diagnostics,
not raw inputs. Canonical and project-semantic validation still run before review
and again at acceptance. Invalid references/parameters are rejected, not repaired
by guessing a different object or changing experimental values.

Accepted relationship proposals use existing graph endpoints and the kernel's
relationship service, preserving direction, type, model provenance, rationale and
an unverified label. Duplicate acceptance returns the same edge; pre-existing edges
are not overwritten. Suggested observations are stored as model_suggestion and
unverified, never as execution-generated evidence. Neither action changes measured
experiment results. Existing persisted proposal payloads remain compatible; optional
relationship fields default to null. No database migration is required.

All accepted hypotheses remain proposed, never verified measurements. A supported
causal experiment requires the actual registered adapter, validated parameters,
and an existing `causal_demo` hypothesis. Other experiment ideas are saved as
explicitly conceptual Notes; they cannot produce measured evidence.

## Persistence and acceptance

Migration 0002 adds `research_conversations`, `research_messages`, and
`research_proposals` in the same SQLite database. It changes no existing scientific
tables. One conversation per project is supported. Messages preserve mode, status,
provider/model, reported usage, context revisions, template version and timestamps.
Proposals preserve payload, source message/references, provenance, review status and
result IDs. Conversation text is not scientific evidence.

Turns persist the user message and a pending assistant record before inference,
release the database transaction for the network call, then persist its result.
An idempotency key and payload hash prevent duplicate turns; changed payloads with
the same key are rejected. A failed request remains in history; a new key retries.
Concurrent turns in one conversation are rejected. Refreshing history marks a
running request older than three minutes as interrupted, allowing recovery after
a process crash. Closing the UI does not cancel submitted server work. Network
loss can be recovered by reopening/refreshing the stored conversation.

Accept/reject operations run under the kernel's existing write transaction and
validate references again. Repeated acceptance returns the original result IDs.
Question/hypothesis creation uses existing `add_object`, revisions and relationship
services. A hypothesis with a Note/Question source uses the registered Construct
operation and the shared construction service. Provenance and assumptions are attached, and sources are linked as
derived_from. The source content is preserved. An executable experiment creates
the kernel's draft Destroy operation/specification; acceptance never approves or
executes an experiment. Revision acceptance checks the generation-time base
revision and linked Evidence, creates the existing Modify operation, and performs
approved revision application atomically through the shared kernel revision service.
Old content is retained, and approval/running/completion/revision events are recorded.
Rejecting changes only review status/history, not scientific content.

The drawer awaits workspace saves before inference or acceptance. After acceptance
it reloads the shared project repository and dispatches a trail refresh event.
Notebook and Canvas therefore use the same objects/relationships as before; no
AI content or conversation is written to localStorage. New objects are available
in the existing Canvas placement selector, without rearranging the Canvas.

## Interface and routes

Research Intelligence is a closable native-dialog drawer accessible in project
headers. Each Notebook entry offers Discuss this research object; normal Canvas
node selection offers the same context when opening the drawer. A dropdown also
allows explicit context selection. Explore/Formalize/Challenge/Design Experiment/
Synthesize map to existing General Reasoning/Hypothesis Construction/Critical
Review / Verification/Experiment Coding/Conceptual Synthesis preferences.

All endpoints use the existing same-origin Next proxy:

```
GET  /v1/intelligence/providers
GET  /v1/projects/{pid}/intelligence/conversations
POST /v1/projects/{pid}/intelligence/conversations
GET  /v1/projects/{pid}/intelligence/conversations/{cid}
POST /v1/projects/{pid}/intelligence/conversations/{cid}/turns
POST /v1/projects/{pid}/intelligence/proposals/{id}/accept
POST /v1/projects/{pid}/intelligence/proposals/{id}/reject
```

The turn body is `{message, mode, selected_object_id, idempotency_key}`. Turn results
are persisted assistant messages with proposals, metadata, status, and error code
when failed. `/docs` on the Python service describes request schemas. Proxy timeout
for intelligence routes is 95 seconds; ordinary kernel requests keep their old limit.

## Verify connectivity and try causal research

1. Configure one key and default model in backend/.env, migrate, and start both services.
2. Confirm GET http://localhost:3000/api/kernel/v1/intelligence/providers shows that
   configuration; this alone is not a live provider test.
3. Open a project Notebook and click Try the First Heartbeat if it is not set up.
4. Open Research Intelligence, select a causal hypothesis and Design Experiment.
   Ask: “These two models explain the same observed relationship between X and Y.
   What experiment could distinguish them?”
5. A completed response with provider/model and reported usage verifies inference.
   Review assumptions and any proposed registered intervention. Accepting it creates
   a draft operation. Open the Notebook operation, inspect it, approve it, and run it.
6. Return to Intelligence and ask what the latest measured evidence implies. Actual
   simulation summaries and checks now enter the context. Any suggested revision
   requires linked evidence and explicit human acceptance.
7. Refresh the app: messages, rejected/accepted proposals, scientific revisions,
   results and trail remain available. Simulation never establishes external causality.

Live Gemini verification subsequently succeeded with `gemini-3.5-flash-lite`:
scientific explanation, canonical hypothesis proposal, kernel acceptance,
provenance, shared Notebook/Canvas retrieval and duplicate-acceptance protection.
These tests used an isolated temporary database, removed afterward. OpenAI and
Anthropic live connections remain unverified. No fabricated response is used in production.
Tests use injected deterministic providers and a separate explicit test server;
the normal startup cannot select those test providers.

To reproduce the original request-schema failure or opt into two live verification
requests (uses the existing server credential; consumes API quota):

```powershell
backend/.venv/Scripts/python backend/tests/live_gemini_repair.py --diagnose
backend/.venv/Scripts/python backend/tests/live_gemini_repair.py --verify
backend/.venv/Scripts/python backend/tests/live_proposal_pipeline.py --verify
```

`--diagnose` compares a simple schema, the intentionally unrepaired canonical wire
schema, and the current full pathway. `--verify` tests the repaired full pathway
and human acceptance in disposable storage. Neither script edits real projects.
`live_proposal_pipeline.py --diagnose` captures synthetic raw proposals and precise
canonical field failures for the two reported prompts. `--verify` makes four live
requests to check hypothesis acceptance/persistence, existing-object relationships,
a conceptual myopia study without execution, and an executable First Heartbeat
draft followed by explicit approval and real NumPy computation. All use temporary
databases removed afterward, and consume provider API quota. Raw proposal capture
is restricted to this explicit synthetic diagnostic, never ordinary request logs.
Gemini diagnostics log stage, status, error class, model and a sanitized provider
message. Credentials, canonical validation inputs and request context are omitted.
Frontend error text distinguishes model availability/overload, quota, timeout,
authentication, rejected schema, invalid JSON and internal scientific validation.

## Tests and limitations

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm test
npm run lint
npm run typecheck
npm run build
```

Backend tests cover routing, SDK invocation/normalization, context isolation and
budgeting, invalid references, idempotency, conceptual/executable experiments,
stale revisions, history, and original scientific regressions. Frontend JSDOM tests
exercise the drawer, contextual selection, send, separate proposals, accept/reject,
reload, and availability in Canvas, alongside real First Heartbeat computation.
The test service uses port 8002, temporary SQLite, and deterministic responses only.
It consumes no paid credits. Visual layout, touch, live account/model availability
and provider latency need verification on the target browser/account.

The kernel remains an unauthenticated local, single-user service. Bind Python to
127.0.0.1 and do not publicly expose Next or the kernel. No arbitrary code, agent
loops, external crawling or tools are available to the model. Provider SDKs transmit
the bounded research request to the configured external provider when the user
presses Send; consider that provider's data policies for confidential research.

Add a provider by implementing `generate_structured_response`, registering safe
configuration/routing, and adding SDK contract tests. Add an action by extending
the response enum, independent semantic validator, transactional acceptance path,
and kernel action service. Do not give adapters direct database access or execution
authority. Do not loosen existing experiment approval rules to accommodate models.
