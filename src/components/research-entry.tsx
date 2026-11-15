"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Eye, FileText, HelpCircle, Lightbulb, Trash2 } from "lucide-react";
import { OBJECT_TYPES, formatDate, type ResearchObject, type ObjectType } from "@/lib/projects";
import { useWorkspace } from "./workspace-provider";

export const TYPE_ICONS = { Note: FileText, Question: HelpCircle, Hypothesis: Lightbulb, Observation: Eye };

// Keep focused text local so a cross-tab refresh cannot move the caret or replace a draft.
export function WritingField({ value, onChange, label, placeholder, className = "", multiline = false, autoFocus = false }: {
  value: string; onChange: (value: string) => void; label: string; placeholder?: string; className?: string; multiline?: boolean; autoFocus?: boolean;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const dirty = useRef(false);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const displayed = draft ?? value;
  useLayoutEffect(() => {
    if (textarea.current) { textarea.current.style.height = "auto"; textarea.current.style.height = `${textarea.current.scrollHeight}px`; }
  }, [displayed]);
  const props = {
    "aria-label": label, placeholder, className, autoFocus, value: displayed,
    onFocus: () => { dirty.current = false; setDraft(value); },
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { dirty.current = true; setDraft(event.target.value); onChange(event.target.value); },
    onBlur: () => { if (dirty.current && draft !== null && draft !== value) onChange(draft); dirty.current = false; setDraft(null); },
  };
  return multiline ? <textarea ref={textarea} rows={3} {...props} /> : <input {...props} />;
}

export function ResearchEntry({ object, autoFocus = false, onDelete }: { object: ResearchObject; autoFocus?: boolean; onDelete?: () => void }) {
  const { mutate } = useWorkspace();
  const Icon = TYPE_ICONS[object.type];
  const edit = (patch: Partial<Pick<ResearchObject, "title" | "body" | "type">>) => mutate({ kind: "edit-object", projectId: object.projectId, objectId: object.id, patch });
  return <article className="research-entry" aria-label={`${object.type}: ${object.title || "Untitled"}`}>
    <div className="entry-topline"><div className="entry-type"><Icon size={15} strokeWidth={1.5} /><select aria-label="Entry type" value={object.type} onChange={e => edit({ type: e.target.value as ObjectType })}>{OBJECT_TYPES.map(type => <option key={type}>{type}</option>)}</select></div>
      <button className="icon-button delete-button" aria-label={`Delete entry ${object.title || "Untitled"}`} onClick={() => { if (window.confirm("Delete this research entry from both Notebook and Canvas, including its connections? This cannot be undone.")) { mutate({ kind: "delete-object", projectId: object.projectId, objectId: object.id }, true); onDelete?.(); } }}><Trash2 size={15} /></button>
    </div>
    <WritingField label="Entry title" className="entry-title" value={object.title} onChange={title => edit({ title })} placeholder="Untitled" autoFocus={autoFocus} />
    <WritingField label="Entry body" className="entry-body" value={object.body} onChange={body => edit({ body })} placeholder="Begin with a question, an observation, or an idea." multiline />
    <p className="entry-date">Created <time dateTime={object.createdAt}>{formatDate(object.createdAt)}</time><span> · </span>Updated <time dateTime={object.updatedAt}>{formatDate(object.updatedAt)}</time></p>
  </article>;
}
