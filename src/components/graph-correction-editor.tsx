"use client";
import { useState } from "react";
import { kernel } from "@/lib/kernel-repository";
import { type ResearchObject } from "@/lib/projects";
import { useWorkspace } from "./workspace-provider";

export function GraphCorrectionEditor({ object, done }: { object: ResearchObject; done: () => void }) {
  const { sync } = useWorkspace();
  const [title, setTitle] = useState(object.title), [body, setBody] = useState(object.body), [type, setType] = useState(object.type.toLowerCase());
  const [rationale, setRationale] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [baseRevision,setBaseRevision] = useState(object.currentRevision);
  async function save() {
    setBusy(true);
    try {
      await sync(); const result=await kernel<{after:{currentRevision:number}}>(`projects/${object.projectId}/graph/corrections`, "POST", { kind: "edit_object", object_id: object.id, title, body, object_type: type, rationale, base_revision: baseRevision });
      setBaseRevision(result.after.currentRevision);
      await sync(); window.dispatchEvent(new Event("vectorheart-research-refresh")); done();
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <section className="graph-correction-editor"><h3>Correct this interpretation</h3><p>Corrections guide future graph generation. They do not establish scientific truth.</p>
    <label>Object type<select aria-label="Corrected object type" value={type} onChange={e => setType(e.target.value)}>{["note", "question", "hypothesis", "observation", "concept", "prediction"].map(t => <option key={t}>{t}</option>)}</select></label>
    <label>Title<input aria-label="Corrected title" maxLength={120} value={title} onChange={e => setTitle(e.target.value)} /></label>
    <label>Scientific content<textarea aria-label="Corrected scientific content" maxLength={10000} value={body} onChange={e => setBody(e.target.value)} rows={6} /></label>
    <label>Why is this interpretation incorrect?<textarea aria-label="Correction rationale" value={rationale} maxLength={4000} onChange={e => setRationale(e.target.value)} /></label>
    {error && <p role="alert">{error}</p>}<button className="text-button" disabled={busy} onClick={() => void save()}>Save researcher correction</button>
  </section>;
}
