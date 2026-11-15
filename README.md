# vectorheart
how can one escape their own capacity to perceive?

## VectorHeart v0.1

A quiet research workspace built with Next.js App Router, React, TypeScript,
Tailwind CSS, and Lucide icons.

### Local development

Requires Node.js 20.9 or newer and npm.

```sh
npm install
npm run dev
```

Open http://localhost:3000. Create a project to begin a research notebook.
Projects support search, renaming, description editing, deletion, research
questions, and notes. Workspace settings offer compact rows and serif notes.

### Verification and production

```sh
npm run lint
npm run typecheck
npm run build
npm start
```

### Structure

- `src/app/`: App Router pages, global styles, and root layout.
- `src/components/`: project dialogs, notebook, workspace state, settings, branding.
- `src/lib/projects.ts`: project types, validation, and persistence adapter.
- `tests/projects.test.mjs`: storage regression tests. Run with Node.js 22.6+
  using `node --experimental-strip-types --test tests/projects.test.mjs`.

`ProjectRepository` isolates persistence from UI components for a future remote
adapter. There are no external services, credentials, authentication, or model APIs.

Projects are stored under `vectorheart.projects.v1` in this browser's localStorage.
Preferences use `vectorheart.preferences.v1`. Data does not follow you between
browsers or devices; clearing site data removes it. No sample projects are added.
Storage failures are reported without overwriting unreadable project data.
Edits save immediately; concurrent edits in multiple tabs use last-write-wins.
