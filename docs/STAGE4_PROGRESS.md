# Stage 4 implementation checkpoint

Baseline: clean commit `34900ab`; Stage 3 and migration 0003 are present.
No browser automation is permitted. Do not commit/push or touch user projects.

## Confirmed before implementation

- Existing `app.stage3` owns leased ResearchRun/ResearchStep orchestration; use it.
- Existing `ResearchProposal` and kernel helpers own review/scientific mutations.
- Paper identity belongs in a bibliographic registry; accepted paper/claim objects
  and edges must remain in the existing scientific graph.
- Direct live HTTP requests succeeded: OpenAlex works search (200), Europe PMC
  core search (200), and Crossref resolution of a DOI returned by Europe PMC (200).
- Current official documentation checked for all three APIs. OpenAlex casual
  access works without a key; optional free key increases budget. No account setup.

## Implemented checkpoints

1. Added 0004: canonical sources/aliases, immutable snapshots, project/run hits, cache.
2. Implemented three provider adapters, bounded safe HTTP, dedup/cache and DOI resolve.
3. Implemented anchored analysis proposals using ResearchProposal and kernel review;
   accepted paper/claim Concepts share the existing graph; no fabricated local Evidence.
4. Added graph-native literature controls/inspection and four read-only tools in the
   existing Stage 3 loop. Existing budgets/experiment approval remain unchanged.
5. Full backend suite: 80 passed. Component/frontend suite: 23 passed. Lint,
   TypeScript, production build, compilation and pip check passed. docs/STAGE4.md
   documents actual contracts, API/configuration, source-integrity rules and limits.
   Production app import and Literature API route registration were also checked.

## Live verification and diagnosed integration issues

- Real OpenAlex, Europe PMC and Crossref retrieval/resolution succeeded.
- Real Gemini planning, grounded interpretation, acceptance and adversarial search
  succeeded on gemini-3.5-flash-lite; accepted records/revisions/graph provenance checked.
- Literature-aware Accelerate succeeded with human acceptance in a subsequent live run.
- Agent selected literature.search, retrieved real publications, then incorporated
  their actual abstracts into follow-up reasoning. Focused live agent test passed.
- Fixed reference-role mismatch: exact verified source/snapshot/DOI aliases are
  normalized into explicit literature reference fields; unknown IDs still rejected.
- Fixed tool/context mismatch: all verified tool-returned records visible to the
  model are now in its explicit citation allowlist; trace copies are compacted.
- The final full seven-model-call live sequence PASSED: ground/accept, adversarial
  search, literature-aware Accelerate/accept, agent-selected scholarly search and
  actual-source-grounded follow-up, invalid DOI rejection. No simulated API results.
- Existing DB backed up consistently and additive migration 0004 applied successfully.
- Registered source inspection and related/reference discovery also passed a live
  backend-only smoke test, resolving two actual referenced works.

Update this file as work proceeds. No browser automation has been used. All live
checks use temporary databases and synthetic projects, never the user's projects.
