"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Check, Pencil } from "lucide-react";
import { Brand } from "./brand";
import { useWorkspace } from "./workspace-provider";
import { ProjectDialog } from "./project-dialog";
import { formatDate, type Project } from "@/lib/projects";

export function ProjectNotebook({ id }: { id: string }) {
  const { projects, ready } = useWorkspace();
  const project = projects.find(p => p.id === id);
  return <div className="page-shell"><header className="site-header"><Brand /><Link className="back-link" href="/"><ArrowLeft size={16} /> All projects</Link></header>
    {!ready ? <main className="notebook"><p role="status">Opening your notebook…</p></main> : project ? <Editor key={project.id} project={project} /> : <main className="notebook"><p className="eyebrow">NOT FOUND IN THIS BROWSER</p><h1>That notebook isn’t here.</h1><p className="subtitle">It may have been deleted or created in another browser.</p><Link href="/" className="text-button mt-8"><ArrowLeft size={16} /> Back to your projects</Link></main>}
  </div>;
}

function Editor({ project }: { project: Project }) {
  const { update } = useWorkspace();
  const [editing, setEditing] = useState(false);
  const [failedDraft, setFailedDraft] = useState<Partial<Pick<Project, "question" | "notes">>>({});
  const unsaved = Object.keys(failedDraft).length > 0;
  function save(patch: Partial<Pick<Project, "question" | "notes">>) {
    const draft = { ...failedDraft, ...patch };
    if (update(project.id, draft)) setFailedDraft({}); else setFailedDraft(draft);
  }
  return <main className="notebook"><p className="eyebrow"><span className="tiny-line" /> RESEARCH NOTEBOOK</p>
    <div className="notebook-title"><h1>{project.title}</h1><button className="icon-button" aria-label="Rename project" onClick={() => setEditing(true)}><Pencil size={18} /></button></div>
    {project.description && <p className="subtitle">{project.description}</p>}
    <div className="notebook-meta"><time dateTime={project.updatedAt}>Updated {formatDate(project.updatedAt)}</time><span role="status">{unsaved ? "Unsaved changes" : <><Check size={14} /> Saved in this browser</>}</span></div>
    {unsaved && <button className="text-button" onClick={() => save({})}>Retry saving</button>}
    <section className="question-section"><label htmlFor="research-question"><span className="section-number">01</span> The research question</label><p className="field-help">What would you like to understand?</p><textarea id="research-question" className="question-input" rows={3} placeholder="Begin with a question. It doesn’t have to be the final one." value={failedDraft.question ?? project.question} onChange={e => save({ question: e.target.value })} /></section>
    <section className="notes-section"><label htmlFor="research-notes"><span className="section-number">02</span> Notes & observations</label><p className="field-help">Follow a thread. Capture an observation. Leave room for the unexpected.</p><textarea id="research-notes" className="notes-input" placeholder="Your thinking starts here…" value={failedDraft.notes ?? project.notes} onChange={e => save({ notes: e.target.value })} /></section>
    <p className="notebook-bottom">A work in progress is a good place to be.</p>
    {editing && <ProjectDialog title="A little refinement." initialName={project.title} initialDescription={project.description} onClose={() => setEditing(false)} onSave={(title, description) => update(project.id, { title, description })} />}
  </main>;
}
