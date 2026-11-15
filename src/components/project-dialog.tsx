"use client";

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

export function ProjectDialog({ title, initialName = "", initialDescription = "", onClose, onSave }: {
  title: string; initialName?: string; initialDescription?: string; onClose: () => void;
  onSave: (name: string, description: string) => boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [error, setError] = useState("");
  useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog ref={ref} className="project-dialog" aria-labelledby="project-dialog-title" onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <form onSubmit={event => { event.preventDefault(); if (name.trim() && onSave(name.trim(), description.trim())) onClose(); else setError("Could not save this project. Check the storage message and try again."); }}>
      <div className="flex items-center justify-between gap-4"><h2 id="project-dialog-title">{title}</h2><button type="button" className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={19} /></button></div>
      <label htmlFor="project-name">Project title</label><input id="project-name" autoFocus required maxLength={120} value={name} onChange={e => setName(e.target.value)} placeholder="Mechanistic Interpretability of Transformers" />
      <label htmlFor="project-description">Description <span className="muted">(optional)</span></label><textarea id="project-description" rows={3} maxLength={500} value={description} onChange={e => setDescription(e.target.value)} placeholder="Investigating the algorithms learned by transformers trained on graph reasoning tasks." />
      {error && <p role="alert">{error}</p>}
      <div className="dialog-actions"><button type="button" className="text-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={!name.trim()}>{initialName ? "Save changes" : "Create project"}</button></div>
    </form>
  </dialog>;
}
