# vectorheart
how can one escape their own capacity to perceive?

A warm, minimal scientific workspace built with Next.js, React, TypeScript,
Tailwind, React Flow, and a local FastAPI/SQLite scientific kernel.

See [Scientific Kernel setup and architecture](docs/SCIENTIFIC_KERNEL.md) for
PowerShell setup, safe browser-data import, First Heartbeat demo, API, tests,
provenance, and security limitations. Start the Python kernel and run `npm run dev`.
Do not expose this unauthenticated prototype publicly.

[Research Intelligence](docs/RESEARCH_INTELLIGENCE.md) adds server-side OpenAI,
Gemini and Anthropic routing, bounded scientific context, persistent conversations,
and proposal review. Configure a server API key and account model in `backend/.env`,
run Alembic upgrade head, and use the existing Python/Next.js startup commands.

[Stage 3: Living Research Graph](docs/STAGE3.md) adds a versioned free-form journal,
source-grounded graph previews, durable researcher corrections, spatial AI
Accelerate proposals and bounded investigations that pause for human approval
before running registered scientific tools. Apply migration `0003` and restart
the existing Python service. The local startup commands remain the same.

[Stage 4: Literature Intelligence](docs/STAGE4.md) connects verified OpenAlex,
Europe PMC and Crossref records to the shared research graph, with abstract-grounded
review, literature-aware Accelerate and bounded read-only investigation tools.
Apply migration `0004` and restart Python. Scholarly discovery also works without
a model; interpretations and scientific changes remain explicitly reviewable.
