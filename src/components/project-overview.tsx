"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { OPERATIONS, PROVIDERS, formatDate, type ModelAssignment, type Project, type ProjectSettings } from "@/lib/projects";
import { useWorkspace } from "./workspace-provider";
import { ProviderAvailability } from "./research-intelligence";

export function ProjectOverview({ project }: { project: Project }) {
  const { update, sync } = useWorkspace();
  const router=useRouter();
  const [title, setTitle] = useState(project.title);
  const [description, setDescription] = useState(project.description);
  const [settings, setSettings] = useState(project.settings);
  const [dirty, setDirty] = useState(false);
  function changeSettings(patch: Partial<ProjectSettings>) { setSettings(s => ({ ...s, ...patch })); setDirty(true); }
  async function save() {
    if (!title.trim()) return false;
    const accepted = update(project.id, { title: title.trim(), description: description.trim(), settings });
    if (accepted) { try { await sync();setDirty(false); return true; } catch {return false;} }
    return false;
  }
  return <main className="project-content overview-content">
    <div className="section-intro"><p className="eyebrow">PROJECT OVERVIEW</p><h2>A foundation for your research.</h2><p>Set a direction. Make this workspace your own.</p></div>
    <form onSubmit={event => { event.preventDefault(); save(); }}>
      <section className="overview-section"><h3>Project information</h3><p className="field-help">Created {formatDate(project.createdAt)}</p>
        <label htmlFor="overview-title">Project title</label><input id="overview-title" required maxLength={120} value={title} onChange={e => { setTitle(e.target.value); setDirty(true); }} />
        <label htmlFor="overview-description">Description <span className="muted">(optional)</span></label><textarea id="overview-description" rows={3} maxLength={500} value={description} onChange={e => { setDescription(e.target.value); setDirty(true); }} />
      </section>
      <section className="overview-section"><h3>Research intelligence</h3><p className="field-help">Automatic uses the server provider priority. Explicit assignments use only that provider and its project model or server default. Configure credentials on the Python server.</p><ProviderAvailability/>
        <div className="model-assignments">{OPERATIONS.map((operation, index) => {
          const assignment = settings.modelAssignments[operation];
          function changeAssignment(patch: Partial<ModelAssignment>) { changeSettings({ modelAssignments: { ...settings.modelAssignments, [operation]: { ...assignment, ...patch } } }); }
          return <div className="model-row" key={operation}><label htmlFor={`provider-${index}`}>{operation}</label><div className="model-fields"><select id={`provider-${index}`} value={assignment.provider} onChange={e => changeAssignment({ provider: e.target.value as ModelAssignment["provider"] })}>{PROVIDERS.map(provider => <option key={provider}>{provider}</option>)}</select>{assignment.provider !== "Automatic" && <input aria-label={`${operation} model identifier`} value={assignment.modelId} onChange={e => changeAssignment({ modelId: e.target.value })} placeholder="Model identifier (optional)" maxLength={200} />}</div></div>;
        })}</div>
      </section>
      <section className="overview-section"><h3>Research preferences</h3>
        <label htmlFor="research-field">Research field <span className="muted">(optional)</span></label><input id="research-field" value={settings.researchField} onChange={e => changeSettings({ researchField: e.target.value })} placeholder="e.g. Mathematics, Machine Learning, Biology" maxLength={200} />
        <label htmlFor="environment">Experimental environment</label><select id="environment" value={settings.environment} onChange={e => changeSettings({ environment: e.target.value as ProjectSettings["environment"] })}><option>None</option><option value="Python">Python (future integration)</option><option value="External environment">External environment (future integration)</option></select><p className="field-help">Environments are not connected. Code cannot be executed here.</p>
        <label htmlFor="compute-budget">Compute budget <span className="muted">(optional, USD)</span></label><input id="compute-budget" type="number" min="0" step="0.01" value={settings.computeBudget?.amount ?? ""} onChange={e => changeSettings({ computeBudget: e.target.value === "" ? null : { amount: Number(e.target.value), unit: "USD" } })} placeholder="No budget set" /><p className="field-help">A planning preference only. No billing or scheduling.</p>
      </section>
      <div className="overview-actions"><button type="submit" className="primary-button" disabled={!dirty || !title.trim()}>Save changes</button><span className="muted text-xs" role="status">{dirty ? "Unsaved settings" : "Settings saved locally"}</span></div>
      <Link className="enter-workspace" href={`/projects/${project.id}/notebook`} onClick={event => { if (dirty) {event.preventDefault();void save().then(ok=>{if(ok)router.push(`/projects/${project.id}/notebook`);});} }}>Open Research Notebook <ArrowRight size={17} /></Link>
    </form>
  </main>;
}
