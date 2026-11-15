"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { newObject, OBJECT_TYPES, type ObjectType, type Project } from "@/lib/projects";
import { useWorkspace } from "./workspace-provider";
import { ResearchEntry, WritingField } from "./research-entry";

export function ProjectNotebook({ project }: { project: Project }) {
  const { update, mutate } = useWorkspace();
  const [type, setType] = useState<ObjectType>("Note");
  const [newId, setNewId] = useState<string | null>(null);
  return <main className="project-content research-document">
    <div className="section-intro"><p className="eyebrow">RESEARCH NOTEBOOK</p><h2>A question worth following.</h2></div>
    <section className="central-question"><p className="field-label">Central research direction</p><WritingField label="Central research direction" className="question-input" value={project.question} onChange={question => update(project.id, { question })} placeholder="What would you like to understand?" multiline /></section>
    <div className="entries-heading"><h3>Research entries <span>{project.objects.length}</span></h3><div className="entry-add"><select aria-label="New entry type" value={type} onChange={e => setType(e.target.value as ObjectType)}>{OBJECT_TYPES.map(value => <option key={value}>{value}</option>)}</select><button className="text-button" onClick={() => { const object = newObject(project.id, type); if (mutate({ kind: "add-object", projectId: project.id, object })) setNewId(object.id); }}><Plus size={16} /> Add entry</button></div></div>
    {project.objects.length === 0 && <p className="notebook-empty">Begin with a question, an observation, or an idea.</p>}
    {project.objects.map(object => <ResearchEntry key={object.id} object={object} autoFocus={object.id === newId} />)}
  </main>;
}
