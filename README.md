# vectorheart
how can one escape their own capacity to perceive?

## VectorHeart — Research Workspace

A quiet research workspace built with Next.js App Router, React, TypeScript,
Tailwind CSS, and Lucide icons.

### Local development

Requires Node.js 22.13 or newer and npm (including the development test tools).

```sh
npm install
npm run dev
```

Open http://localhost:3000. Creating a project opens its overview/settings.
Configure project information, six model assignments, field, environment, and
optional USD budget, then save and open the Notebook. Provider and environment
settings are configuration only: nothing calls a model or executes code.

Notebook entries support Note, Question, Hypothesis, and Observation types.
The Canvas can place existing entries, create and edit entries, drag nodes,
connect handles, zoom, and fit the view. The compact Select, Connect (+), and
Disconnect (−) tools support two-click node interactions. Connect uses the first
entry as the source and the second as the target. Disconnect removes only the
chosen relationship, offering a direction/type picker if more than one exists.
Escape cancels a tool; empty-space clicks clear its endpoint. Focused nodes also
accept Enter/Space for endpoint selection. Select a connection to delete it.
Select a node and use Remove from canvas to keep its Notebook entry; deleting
the entry itself removes it everywhere, including its relationships.

Home search, renaming, deletion, and workspace preferences remain available.
Project entry URLs reopen the last Notebook or Canvas view; new projects open
settings. The settings icon is always accessible from a project.

### Verification and production

```sh
npm run lint
npm run typecheck
npm test
npm run build
npm start
```

### Structure

- `src/app/`: homepage, root layout and styles, plus project entry, settings,
  notebook, and canvas routes under `projects/[id]/`.
- `src/components/project-workspace.tsx`: shared project header and navigation.
- `src/components/project-overview.tsx`: project configuration.
- `src/components/project-notebook.tsx`, `research-entry.tsx`: structured writing.
- `src/components/research-canvas.tsx`: React Flow surface and object editor.
- `src/components/workspace-provider.tsx`: live state, buffered mutation queue,
  save status, retry, and cross-tab synchronization.
- `src/lib/projects.ts`: typed objects, placements, relationships, settings,
  mutation operations, validation, migration, and persistence adapter.
- `tests/projects.test.mjs`: migration, integrity, and persistence regression tests.
- `tests/workspace.test.mjs`: actual React component interactions in JSDOM.

`ProjectRepository` isolates persistence from UI components for a future remote
adapter. There are no external services, credentials, authentication, or model APIs.

Each project owns one array of research objects. The Notebook and Canvas edit
those same objects by ID; placements contain only object IDs and positions,
while relationships reference source/target object IDs. There is no duplicated
Canvas content database. Deletion maintains referential integrity.

Projects are stored in a versioned envelope under `vectorheart.projects.v2` in
localStorage. On first load, v1 projects are converted in memory: their research
questions remain intact and nonempty notes become structured entries. The
original `vectorheart.projects.v1` record is never modified or deleted. The v2
record becomes authoritative after the first successful save, even if empty.
Malformed/unsupported records are preserved and block writing until resolved.

Edits update the UI immediately. A single fixed 10-second interval batches pending
mutations into one localStorage write; ongoing activity does not reset the timer.
No-op edits and clean intervals do not write. Canvas drag events, connections,
disconnections, and editor changes share this buffer. Project creation/deletion
and explicit settings saves retain their intentional immediate saves. Navigation,
workspace unmount, page hiding, and page exit flush pending edits synchronously.
Failed saves keep drafts in memory, retry on the next interval,
and show a retry action; do not close the tab until saving succeeds. Browser crashes
or forced termination may prevent lifecycle flushing. Settings use
an explicit Save changes action (Open Research Notebook also saves the form).

Cross-tab storage events refresh content. Pending field-level edits are rebased
onto the latest snapshot before writing; focused text remains stable. Simultaneous
writes to the same field are last-write-wins. localStorage does not provide
transactional multi-tab collaboration or cloud synchronization.

Preferences still use `vectorheart.preferences.v1`. Data does not follow you
between browsers, devices, or origins/ports; clearing site data removes it.
No sample projects are added. Canvas viewport/selection are transient; object
positions and connections persist. Tests cover data and DOM interactions, not
real-browser layout, pointer geometry, or touch behavior.
