# Scientific Kernel v0.1

Research Intelligence now extends this kernel. See
[Research Intelligence](RESEARCH_INTELLIGENCE.md) for provider setup, additive
migration 0002, conversations, and human-reviewed model proposals. The older
provider-deferred notes below describe the initial Phase 3 baseline.

The kernel preserves a scientific cycle: human proposal, approval, trusted execution,
validated simulation evidence, and an explicitly approved revision. It is a local,
single-user prototype, not a public multi-user service.

## Start on Windows PowerShell

From the repository root (Python 3.11+, Node 22.13+):

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm install
npm run dev
```

Open http://localhost:3000. The default kernel URL requires no configuration.
Optional Next server variable: `KERNEL_API_URL=http://127.0.0.1:8000` in `.env.local`.
Optional Python variable: `$env:KERNEL_DB_PATH='C:/path/kernel.sqlite3'` before
both migration and service startup. Default: `.vectorheart/kernel.sqlite3`.
The database, virtual environment, and secrets are Git-ignored. No API keys are needed.

## First Heartbeat

Create/open a project, save its settings, and open the Notebook. Click **Try the
First Heartbeat** once. Inspect the competing hypotheses and expand the proposed
operation. Its specification contains both predictions, measurement/validation
plans, limits, and parameters. Click **Approve**, then **Run approved experiment**.
Approval and execution are distinct requests. Expand the simulation run to inspect
mean, interval, compatibility, validation checks, parameters, environment and samples.

Open Research Actions, select Hypothesis A, write a scoped revised statement and
assumption changes, and select Propose Revision. Inspect the original/proposed diff,
approve it, then apply the approved operation. Rejection preserves all evidence.
The Research Trail records the sequence. In Canvas, place the existing Hypothesis,
Experiment and Evidence entries; scientific relationships are the same stored graph.
The experiment `tests` the hypothesis, `produces` evidence, and evidence `supports`
or `challenges` the hypothesis within the simulation's stated mean-compatibility rule.

## State, operations, events

SQLAlchemy tables separate projects, research objects, object revisions,
relationships, placements, operations, specifications, runs, evidence, and events.
UUIDs identify new entities; imported legacy identifiers are preserved even when
they are not UUIDs. Schema versions are explicit for foundational records. SQLite
foreign keys are enabled, and write transactions use BEGIN IMMEDIATE. Event
sequence numbers are assigned inside that transaction, independently per project.

A research object is scientific content. An operation is an intention with validated
input. An event is an append-only journal fact. The registry in `app/main.py` maps
the three action names to Pydantic input schemas and permitted target types.
Only the fixed registered causal adapter executes. Draft → approved/rejected;
approved → running; running → completed/failed. Duplicate completed execution returns
the same operation. Failed operations retain errors; retry creates a new draft linked
by an event, requiring approval again. Interrupted `running` operations after a
process crash currently require developer recovery; they are not automatically replayed.

Every accepted content save snapshots title, body and metadata with a revision
number and previous-revision pointer. Accepted hypothesis modifications verify the
base revision has not changed. The Notebook coalesces adjacent edits before saving.
Deletion marks objects deleted and removes active graph references; project deletion
archives it. History remains in the database. There is no history reconstruction UI.

Hypothesis metadata uses proposed/unresolved/conditionally_supported/challenged/
rejected_within_scope, never proven. This implementation creates proposed hypotheses
and marks accepted revisions unresolved. Evidence verification is execution_checked
only after computational checks; it is not method review or independent replication.

## Execution and validation

`app/science.py` defines Parameters, predictions, simulation and numerical validation.
The trusted worker runs with the virtual-environment Python executable, a fixed
server-controlled script, JSON stdin, no shell, a 15-second timeout, and one runner
slot. Inputs bound samples to 100–5000, X to [-5,5], seed to uint32, and world to A/B.
No browser strings or model-generated code are executed.

Both models have zero observational means and covariance [[1,.8],[.8,1]]. Under
do(X=x), A generates .8x+.6 epsilon, while B generates epsilon. A predicts mean .8x,
variance .36; B predicts 0 and 1. PCG64 via NumPy default_rng uses the recorded seed.
The run records all samples, their canonical JSON SHA-256, Python/NumPy versions,
sample SD (ddof=1), standard error, and mean ± 1.96 SE. A predicted mean is compatible
when it lies within that approximate interval. At x=0 means cannot discriminate.
This does not test all aspects of either model or infer real-world causality.

The parent validates the output schema, finite numbers, count, recomputed statistics,
interval, analytical predictions, compatibility decisions, checksum and simulation
label before creating evidence. Results and revisions have no mutation API. Artifact
samples are embedded in the run record; no user-controlled file paths are accepted.
The approved specification hash is checked before execution. Full dependency versions
are pinned in requirements-lock.txt. Exact reproduction requires the same numerical
environment and implementation; checksum validation is not cryptographic journal integrity.

## Frontend and import

`kernel-repository.ts` is the UI transport boundary. Next `/api/kernel/v1/...` forwards
to a server-configured loopback service with timeouts. Components share one backend
projection of research objects; positions are separate metadata. After import, object
changes no longer write to localStorage. A 10-second buffer retains optimistic edits
and sends field mutations. Navigation/lifecycle events request flushing using fetch
keepalive. Unlike localStorage, network writes cannot synchronously complete during
page termination; await Saved locally (meaning saved on the local kernel) before
closing. Pending failures remain visible in memory. Concurrent same-field edits are
last-write-wins; multi-tab collaboration is not transactional.

Existing keys: vectorheart.projects.v1, vectorheart.projects.v2, and preferences.v1.
The migration gate offers an export of both original keys. v1 notes become entries;
v2 unknown fields and raw backups are preserved in import events. Backend import
validates the complete envelope in a transaction. Existing backend project IDs are
skipped, never overwritten; missing relationship endpoints are reported and skipped.
Malformed import rolls back. The original localStorage values are never deleted or
modified. The UI switches only after successful import and backend reload. If it
fails, export the backup, fix the reported issue or service, and retry. To re-open
the gate remove only `vectorheart.kernel.imported.v1`; repeated imports are safe.
An exported backup wraps raw v1/v2 JSON strings; manual restore uses those original
strings under their respective keys. Back up the SQLite file with the service stopped.

## API

All routes use `/v1`. `/docs` provides generated OpenAPI for current request contracts.
Health; project list/create/read/patch/archive; object list/create/read/patch/delete
and revisions; relationship list/create/delete; Canvas list/put/delete by object;
operation list/create/read/approve/reject/execute/retry; adapters with parameter schema;
runs list/read/artifacts; evidence list; ordered events with after/limit; import; demo.
Errors use `{error:{message}}`. Approval freezes specification; execution consumes it.
Revisions use the modify operation rather than a separate unguarded accept endpoint.

## Providers and extension points

ManualProvider defines formalize_hypothesis, propose_experiment and propose_revision
with typed proposals. No external model is required or called. Gemini, OpenAI,
Anthropic and Custom preferences remain stored configuration; integrations are not
implemented. Gemini SDK/credentials and model provenance are deferred, not simulated.
Future providers must return validated proposals with model provenance and cannot
write measured results or approve operations. Future adapters should preserve the
specification/approval/execution/validation boundary; future remote workers can replace
the subprocess runner. Source artifacts, literature, lenses and datasets can extend
metadata and object types without coupling the kernel to React or provider SDKs.

## Checks and known limits

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm test
npm run lint
npm run typecheck
npm run build
backend/.venv/Scripts/python -m compileall -q backend/app backend/workers
```

The frontend integration test starts an isolated migrated database and real service
on port 8002; that port must be free. It runs actual React DOM interactions and
NumPy execution, not visual browser layout or touch geometry. Python tests use
temporary databases. No LLM is needed. Browser automation availability is separate.

This unauthenticated service must stay on loopback. The Next proxy and origin checks
are not production authentication or a secure arbitrary-code sandbox. Do not expose
either unauthenticated app publicly. No remote scheduling, arbitrary Python,
scientific-history branching, team access or model autonomy is implemented.
