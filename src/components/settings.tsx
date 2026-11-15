"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Check, Settings2, X } from "lucide-react";

function subscribePreferences(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}
function readPreferences() {
  try { return localStorage.getItem("vectorheart.preferences.v1") || "{}"; }
  catch { return "{}"; }
}

export function Settings() {
  const [open, setOpen] = useState(false);
  const raw = useSyncExternalStore(subscribePreferences, readPreferences, () => "{}");
  const [draft, setDraft] = useState<{ serif: boolean; compact: boolean } | null>(null);
  let stored = { serif: true, compact: false };
  try {
    const parsed = JSON.parse(raw);
    stored = { serif: parsed?.serif !== false, compact: parsed?.compact === true };
  } catch { /* Use defaults when stored preferences are invalid. */ }
  const { serif, compact } = draft ?? stored;
  const [error, setError] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    document.documentElement.dataset.notesFont = serif ? "serif" : "sans";
    document.documentElement.dataset.density = compact ? "compact" : "comfortable";
  }, [serif, compact]);
  useEffect(() => {
    if (!open) return;
    function outside(e: PointerEvent) { if (!root.current?.contains(e.target as Node)) setOpen(false); }
    function escape(e: KeyboardEvent) { if (e.key === "Escape") { setOpen(false); toggle.current?.focus(); } }
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, [open]);
  function save(nextSerif: boolean, nextCompact: boolean) {
    setDraft({ serif: nextSerif, compact: nextCompact });
    try { localStorage.setItem("vectorheart.preferences.v1", JSON.stringify({ serif: nextSerif, compact: nextCompact })); setError(""); }
    catch { setError("Preferences apply for this visit but could not be saved."); }
  }
  return <div ref={root} className="settings-root">
    {open && <section id="preferences" className="settings-panel" aria-label="Workspace preferences">
      <div className="flex items-center justify-between"><h2>Make yourself at home.</h2><button className="icon-button" aria-label="Close preferences" onClick={() => { setOpen(false); toggle.current?.focus(); }}><X size={17} /></button></div>
      <p className="muted text-sm mb-5">A few small things, your way.</p>
      <label className="preference"><span>Serif type in notes</span><input type="checkbox" checked={serif} onChange={e => save(e.target.checked, compact)} /></label>
      <label className="preference"><span>Compact project list</span><input type="checkbox" checked={compact} onChange={e => save(serif, e.target.checked)} /></label>
      <p className="local-notice"><Check size={14} /> Projects live in this browser.</p><p className="muted text-xs">No account needed. Clearing browser data removes your projects.</p>
      {error && <p role="alert" className="text-xs mt-3">{error}</p>}
    </section>}
    <button ref={toggle} className="settings-toggle" aria-label="Workspace settings" aria-expanded={open} aria-controls="preferences" onClick={() => setOpen(!open)}><Settings2 size={18} strokeWidth={1.5} /><span>Workspace settings</span></button>
  </div>;
}
