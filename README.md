# VECTORHEART

**Human curiosity. Computational possibility.**

### Understanding, still becoming.

*What if scientific understanding were not merely recorded, but continuously reconstructed, challenged, extended, and experimentally investigated?*

Research has always been a process of evolving ideas. Yet most scientific software treats its output as static: notebooks, documents, datasets, and papers.

**VECTORHEART explores a different possibility: scientific understanding itself as a living computational system.**

A researcher writes freely. AI reconstructs the hypotheses, questions, evidence, and relationships emerging from those records. The researcher corrects that interpretation. New ideas become inspectable proposals. Scientific tools test what can be tested. Existing literature connects individual investigations to the wider body of scientific knowledge.

And through every revision, experiment, contradiction, and discovery, the intellectual history remains intact.

**Write → Understand → Challenge → Discover**

---

## The Current Instrument

### From scattered research notes to living scientific understanding.

VECTORHEART brings six interconnected capabilities into a single research environment.

### 01 — Research Journal

**Research begins with the freedom to think.**

A writing-first environment for observations, experiments, conversations, failed attempts, uncertainties, and emerging ideas. Researchers write naturally without being forced to organize every thought into rigid scientific categories.

The original scientific record is preserved.

### 02 — Living Research Graph

**Ideas become relationships. Relationships become understanding.**

AI reconstructs the scientific structure within research records, generating an interconnected graph of hypotheses, questions, observations, experiments, and evidence.

Researchers can inspect sources, correct interpretations, create or reject connections, and preserve how their understanding changes over time.

The graph is not merely a visualization. It is an editable representation of an evolving scientific investigation.

### 03 — AI Accelerate

**Scientific imagination, augmented by computation.**

AI examines the existing research structure and proposes new hypotheses, alternative explanations, overlooked relationships, challenges, and experimental directions.

These appear directly within the research graph as reviewable scientific proposals, accompanied by concise rationales and source references.

The researcher remains in control of what becomes part of the scientific record.

### 04 — Scientific Kernel

**Every scientific claim deserves a history.**

Beneath the interface is a persistent scientific infrastructure supporting versioned research objects, evidence records, computational experiments, provenance, and human approval.

VECTORHEART distinguishes original observations from AI interpretations, proposed hypotheses from recorded evidence, and accepted experiments from executed ones.

Scientific understanding can evolve without forgetting how it arrived at its present form.

### 05 — Autonomous Investigation

**From proposing an experiment to investigating its outcome.**

A bounded scientific agent can select registered computational tools, propose experiments, pause for explicit researcher approval, execute authorized operations, and incorporate actual results into subsequent reasoning.

The current computational demonstration uses synthetic causal models. It establishes the tool-execution and evidence-tracking workflow, not real-world experimental conclusions.

### 06 — Literature Intelligence

**Individual curiosity meets accumulated human knowledge.**

VECTORHEART connects research questions to real scholarly publications through literature discovery, bibliographic verification, and source-grounded interpretation.

Relevant publications and evidence relationships can become inspectable parts of the research graph, allowing researchers to examine supporting findings, conflicting explanations, and established experimental approaches.

Published findings remain distinct from experiments independently executed within VECTORHEART.

---

## Why VECTORHEART?

**Because scientific discovery is not a sequence of isolated answers. It is the evolution of understanding.**

Research advances through uncertainty, mistakes, unexpected relationships, experiments, contradictions, and revisions.

Much of this process disappears into disconnected documents or remains invisible in a scientist's personal notes.

VECTORHEART aims to preserve that intellectual process and make it computationally accessible.

Rather than positioning AI as an oracle that produces answers, we envision it as a research collaborator that helps scientists identify what they might have overlooked, challenge what they currently believe, and determine what deserves investigation next.

**Human curiosity drives the questions. Computational intelligence expands the possibilities. Experimental evidence constrains the conclusions.**

---

## The Research That Comes Next

*Our long-term vision extends well beyond the current prototype.*

Imagine scientific memory that spans decades rather than individual projects.

Imagine systems that identify contradictions across enormous networks of research, connect discoveries from apparently unrelated fields, and suggest experiments capable of distinguishing competing theories.

Imagine AI research environments connected directly to laboratory instruments, simulations, scientific databases, and advanced multimodal models that understand equations, experimental measurements, scientific images, and complex computational representations.

And imagine **universities operating their own scientific AI infrastructure**: institutional GPU clusters running powerful open-weight models alongside commercial APIs where appropriate, supporting researchers while keeping sensitive data within properly secured, institutionally controlled environments.

VECTORHEART's model-independent architecture provides an initial foundation for exploring this possibility.

Future scientific intelligence should not require researchers to surrender control of their ideas, their data, or their intellectual history.

Our ambition is not to replace scientists.

**It is to give human curiosity an entirely new computational medium.**

---

## Current Scope and Scientific Integrity

VECTORHEART is a research prototype.

Its AI capabilities depend on configured model providers, and inference quality and availability vary by model. Computational execution is restricted to registered scientific tools. The current causal intervention environment is synthetic. Literature interpretation is limited by the source material actually retrieved.

AI-generated proposals are not verified discoveries. Researcher acceptance is not empirical confirmation.

These distinctions are deliberate architectural principles, not incidental restrictions.

---

> **Scientific discovery should not end when an experiment is recorded. Every result should become the beginning of the next question.**

**VECTORHEART — Understanding, still becoming.**

---

## Technical Overview

The workspace uses **Next.js, React, TypeScript, Tailwind CSS, and React Flow**, with a **FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite, and NumPy** scientific kernel.

The Notebook and Research Graph share the same authoritative research objects and relationships. Canvas positions are separate spatial metadata. Journal entries preserve original writing and versioned history; model interpretations and proposals retain source and model provenance.

The browser communicates through same-origin Next.js API routes, which forward to the local Python kernel. Model inference and scholarly retrieval run server-side. SQLite stores research objects, immutable revisions, ordered events, operations, experiment runs, conversations, proposals, investigation checkpoints, and scholarly source snapshots.

### Technical Documentation

| Document | Coverage |
| --- | --- |
| [Scientific Kernel](docs/SCIENTIFIC_KERNEL.md) | Foundational architecture, safe browser-data import, First Heartbeat, operations, revisions, numerical validation, API, and security boundaries |
| [Research Intelligence](docs/RESEARCH_INTELLIGENCE.md) | OpenAI/Gemini/Anthropic adapters, model routing, environment variables, bounded project context, conversations, and proposal acceptance |
| [Living Research Graph](docs/STAGE3.md) | Journal persistence, graph extraction, researcher corrections, AI Accelerate, and bounded approval-aware investigation |
| [Literature Intelligence](docs/STAGE4.md) | Scholarly providers, source verification, abstract-grounded analysis, graph review, literature tools, and scientific limitations |
| [Stage 3 Handoff](docs/STAGE3_HANDOFF.md) | Historical architecture and implementation context preceding Stage 3 |

Earlier documents retain some descriptions of their original implementation stage. The Stage 3 and Stage 4 documents describe the subsequent graph, autonomy, and literature extensions.

## Run Locally

Requirements: **Python 3.11+** and **Node.js 22.13+**, with npm. Run the following commands from the repository root in Windows PowerShell.

### 1. Install and configure

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
npm install

# Preserve an existing configuration; create this file only when absent.
if (-not (Test-Path backend/.env)) {
    Copy-Item backend/.env.example backend/.env
}
```

For AI features, edit `backend/.env` with at least one provider credential and a model identifier available to your account:

| Provider | Server-side variables |
| --- | --- |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_DEFAULT_MODEL` |
| Google Gemini | `GEMINI_API_KEY`, `GEMINI_DEFAULT_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_DEFAULT_MODEL` |

Project settings assign providers and models to research operations. **Automatic** follows `VECTORHEART_PROVIDER_PRIORITY`; an explicit provider selection never silently substitutes another provider. Configuration alone does not guarantee live API access. Institutional hosting and open-weight model deployment are future possibilities, not current integrations.

The journal, manual scientific workflows, First Heartbeat simulation, and basic scholarly discovery work without a model API key. Scholarly discovery uses **OpenAlex, Europe PMC, and Crossref**; `OPENALEX_API_KEY` and `LITERATURE_CONTACT_EMAIL` are optional configuration. Source analysis currently uses metadata and available abstracts, without full-text or PDF ingestion.

Keep credentials server-side. Never place API keys in `NEXT_PUBLIC_` variables or commit `backend/.env`.

### 2. Migrate and start the kernel

Back up an existing database before migrating. Use SQLite's backup API or stop the service before copying it; copying only the main file of an active WAL database is not a complete backup.

```powershell
backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The additive migration chain currently runs through **`0004`**, preserving the existing Scientific Kernel, Research Intelligence, Living Research Graph, and Literature Intelligence records. Restart Python after backend or environment changes.

### 3. Start the workspace

In a second terminal:

```powershell
npm run dev
```

Open **http://localhost:3000**. The kernel's generated API documentation is available locally at **http://127.0.0.1:8000/docs**.

The database defaults to `.vectorheart/kernel.sqlite3`. Set `KERNEL_DB_PATH` consistently for migration and service startup to use a different location. The Next.js server uses `KERNEL_API_URL`, defaulting to `http://127.0.0.1:8000`; an override belongs in `.env.local`. Databases, virtual environments, and secret configuration are Git-ignored.

Existing browser-local projects have an explicit backup/export and import path. Successful migration switches research data access to the kernel while leaving original localStorage data intact as a backup. See the [Scientific Kernel documentation](docs/SCIENTIFIC_KERNEL.md) before importing or recovering existing work.

**This is a local, single-user, unauthenticated prototype. Keep the Python service bound to loopback and do not expose either service publicly.** The proxy and origin checks are not a substitute for production authentication or execution isolation.

## Explore the Scientific Workflow

1. **Write.** Create a project and open the Notebook. Record ideas in the journal; structured entries remain available when useful.
2. **Understand.** Open Research Graph and generate a source-grounded graph preview with your configured model. Inspect and accept the interpretation.
3. **Correct.** Edit interpretations or add/remove relationships with rationales. These corrections inform future graph generation.
4. **Challenge.** Use AI Accelerate for reviewable graph proposals, or launch a bounded investigation. Experiments require their own explicit approval.
5. **Investigate.** In the Notebook, expand **Scientific tools & research history** and select **Try the First Heartbeat**. Inspect the synthetic causal experiment, approve its specification, then run it to examine real NumPy measurements and validation checks.
6. **Ground.** Select a hypothesis and use **Ground in Literature** or **Challenge with Literature**. Inspect actual publications and available source content before accepting proposed evidence relationships.

## Development Checks

From the repository root, after installing dependencies:

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm test
npm run lint
npm run typecheck
npm run build
```

Backend tests use temporary databases. Frontend integration tests start an isolated kernel on **port 8002**, which must be free; they exercise React DOM interactions and real synthetic computation without browser automation. Ordinary regression tests use deterministic provider fixtures and do not require paid model calls. See the technical documentation for separate live-provider verification scripts and their requirements.
