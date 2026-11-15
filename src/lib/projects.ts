export const OBJECT_TYPES = ["Note", "Question", "Hypothesis", "Observation"] as const;
export type ObjectType = typeof OBJECT_TYPES[number];
export const OPERATIONS = ["General Reasoning", "Literature Analysis", "Hypothesis Construction", "Critical Review / Verification", "Experiment Coding", "Conceptual Synthesis"] as const;
export type ResearchOperation = typeof OPERATIONS[number];
export const PROVIDERS = ["Automatic", "OpenAI", "Anthropic", "Google Gemini", "Custom"] as const;
export type ModelAssignment = { provider: typeof PROVIDERS[number]; modelId: string };
export type ProjectSettings = {
  modelAssignments: Record<ResearchOperation, ModelAssignment>;
  researchField: string;
  environment: "None" | "Python" | "External environment";
  computeBudget: { amount: number; unit: "USD" } | null;
};
export type ResearchObject = {
  id: string; projectId: string; type: ObjectType; title: string; body: string;
  createdAt: string; updatedAt: string;
};
export type CanvasPlacement = { objectId: string; position: { x: number; y: number } };
export type ResearchRelationship = { id: string; projectId: string; sourceId: string; targetId: string; type?: string };
export type Project = {
  id: string; title: string; description: string; question: string;
  createdAt: string; updatedAt: string; settings: ProjectSettings;
  lastVisitedView: "notebook" | "canvas" | null;
  objects: ResearchObject[]; placements: CanvasPlacement[]; relationships: ResearchRelationship[];
};
export type ProjectPatch = Partial<Pick<Project, "title" | "description" | "question" | "settings" | "lastVisitedView">>;

export function defaultSettings(): ProjectSettings {
  return {
    modelAssignments: Object.fromEntries(OPERATIONS.map(operation => [operation, { provider: "Automatic", modelId: "" }])) as ProjectSettings["modelAssignments"],
    researchField: "", environment: "None", computeBudget: null,
  };
}
export function newProject(title: string, description: string, id: string = crypto.randomUUID()): Project {
  const now = new Date().toISOString();
  return { id, title: title.trim(), description: description.trim(), question: "", createdAt: now, updatedAt: now,
    settings: defaultSettings(), lastVisitedView: null, objects: [], placements: [], relationships: [] };
}
export function newObject(projectId: string, type: ObjectType = "Note"): ResearchObject {
  const now = new Date().toISOString();
  return { id: crypto.randomUUID(), projectId, type, title: "", body: "", createdAt: now, updatedAt: now };
}

// Version 1 remains a read-only migration backup.
export const LEGACY_PROJECTS_KEY = "vectorheart.projects.v1";
export const PROJECTS_KEY = "vectorheart.projects.v2";
type RecordValue = Record<string, unknown>;
function record(value: unknown): value is RecordValue { return !!value && typeof value === "object" && !Array.isArray(value); }
function strings(value: RecordValue, keys: string[]) { return keys.every(key => typeof value[key] === "string"); }
function dated(value: RecordValue) { return [value.createdAt, value.updatedAt].every(date => typeof date === "string" && Number.isFinite(Date.parse(date))); }
function unique(ids: string[]) { return new Set(ids).size === ids.length && ids.every(Boolean); }

function validSettings(value: unknown): value is ProjectSettings {
  if (!record(value) || !record(value.modelAssignments)) return false;
  const assignments = value.modelAssignments;
  return OPERATIONS.every(key => {
    const item = assignments[key];
    return record(item) && PROVIDERS.includes(item.provider as ModelAssignment["provider"]) && typeof item.modelId === "string";
  }) && typeof value.researchField === "string" && ["None", "Python", "External environment"].includes(value.environment as string) &&
    (value.computeBudget === null || (record(value.computeBudget) && typeof value.computeBudget.amount === "number" && Number.isFinite(value.computeBudget.amount) && value.computeBudget.amount >= 0 && value.computeBudget.unit === "USD"));
}
function validProject(value: unknown): value is Project {
  if (!record(value) || !strings(value, ["id", "title", "description", "question"]) || !value.id || !(value.title as string).trim() || !dated(value) || !validSettings(value.settings)) return false;
  if (value.lastVisitedView !== null && value.lastVisitedView !== "notebook" && value.lastVisitedView !== "canvas") return false;
  if (!Array.isArray(value.objects) || !Array.isArray(value.placements) || !Array.isArray(value.relationships)) return false;
  const objects = value.objects;
  if (!objects.every(o => record(o) && strings(o, ["id", "projectId", "title", "body"]) && o.projectId === value.id && OBJECT_TYPES.includes(o.type as ObjectType) && dated(o))) return false;
  if (!unique(objects.map(o => o.id))) return false;
  const ids = new Set(objects.map(o => o.id));
  if (!value.placements.every(p => record(p) && ids.has(p.objectId) && record(p.position) && typeof p.position.x === "number" && Number.isFinite(p.position.x) && typeof p.position.y === "number" && Number.isFinite(p.position.y)) || !unique(value.placements.map(p => p.objectId))) return false;
  return value.relationships.every(r => record(r) && typeof r.id === "string" && r.projectId === value.id && ids.has(r.sourceId) && ids.has(r.targetId) && r.sourceId !== r.targetId && (r.type === undefined || typeof r.type === "string")) && unique(value.relationships.map(r => r.id));
}
export function migrateLegacy(data: unknown): Project[] {
  if (!Array.isArray(data) || !data.every(p => record(p) && strings(p, ["id", "title", "description", "question", "notes"]) && p.id && (p.title as string).trim() && dated(p)) || !unique(data.map(p => p.id))) throw new Error("Invalid legacy projects; original data preserved.");
  return data.map(p => ({
    id: p.id, title: p.title, description: p.description, question: p.question, createdAt: p.createdAt, updatedAt: p.updatedAt,
    settings: defaultSettings(), lastVisitedView: null,
    objects: p.notes ? [{ id: "legacy-notes-" + p.id, projectId: p.id, type: "Note", title: "Previous research notes", body: p.notes, createdAt: p.createdAt, updatedAt: p.updatedAt }] : [],
    placements: [], relationships: [],
  }));
}

// UI state and mutations do not depend on the persistence implementation.
export interface ProjectRepository { load(): Project[]; save(projects: Project[]): void }
export const localProjectRepository: ProjectRepository = {
  load() {
    const raw = localStorage.getItem(PROJECTS_KEY);
    if (raw === null) return migrateLegacy(JSON.parse(localStorage.getItem(LEGACY_PROJECTS_KEY) ?? "[]"));
    const data: unknown = JSON.parse(raw);
    if (!record(data) || data.version !== 2 || !Array.isArray(data.projects) || !data.projects.every(validProject) || !unique(data.projects.map(p => p.id))) throw new Error("Invalid or unsupported workspace data; original data preserved.");
    return data.projects;
  },
  save(projects) {
    if (!projects.every(validProject) || !unique(projects.map(p => p.id))) throw new Error("Invalid project data");
    localStorage.setItem(PROJECTS_KEY, JSON.stringify({ version: 2, projects }));
  },
};
export function formatDate(date: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(date));
}
export type Mutation =
  | { kind: "create"; project: Project }
  | { kind: "remove"; projectId: string }
  | { kind: "project"; projectId: string; patch: ProjectPatch }
  | { kind: "add-object"; projectId: string; object: ResearchObject; position?: { x: number; y: number } }
  | { kind: "edit-object"; projectId: string; objectId: string; patch: Partial<Pick<ResearchObject, "title" | "body" | "type">> }
  | { kind: "delete-object"; projectId: string; objectId: string }
  | { kind: "place"; projectId: string; placement: CanvasPlacement }
  | { kind: "unplace"; projectId: string; objectId: string }
  | { kind: "connect"; projectId: string; relationship: ResearchRelationship }
  | { kind: "disconnect"; projectId: string; relationshipId: string };

export function applyMutation(projects: Project[], mutation: Mutation, now = new Date().toISOString()): Project[] {
  if (mutation.kind === "create") return projects.some(p => p.id === mutation.project.id) ? projects : [mutation.project, ...projects];
  if (mutation.kind === "remove") return projects.filter(p => p.id !== mutation.projectId);
  return projects.map(project => {
    if (project.id !== mutation.projectId) return project;
    const p = { ...project, updatedAt: now };
    switch (mutation.kind) {
      case "project": return { ...p, ...mutation.patch, updatedAt: Object.keys(mutation.patch).every(key => key === "lastVisitedView") ? project.updatedAt : now };
      case "add-object":
        if (mutation.object.projectId !== p.id || p.objects.some(o => o.id === mutation.object.id)) return project;
        return { ...p, objects: [...p.objects, mutation.object], placements: mutation.position ? [...p.placements, { objectId: mutation.object.id, position: mutation.position }] : p.placements };
      case "edit-object": return { ...p, objects: p.objects.map(o => o.id === mutation.objectId ? { ...o, ...mutation.patch, updatedAt: now } : o) };
      case "delete-object": return { ...p, objects: p.objects.filter(o => o.id !== mutation.objectId), placements: p.placements.filter(v => v.objectId !== mutation.objectId), relationships: p.relationships.filter(r => r.sourceId !== mutation.objectId && r.targetId !== mutation.objectId) };
      case "place":
        if (!p.objects.some(o => o.id === mutation.placement.objectId)) return project;
        return { ...p, placements: [...p.placements.filter(v => v.objectId !== mutation.placement.objectId), mutation.placement] };
      case "unplace": return { ...p, placements: p.placements.filter(v => v.objectId !== mutation.objectId) };
      case "connect": {
        const r = mutation.relationship;
        if (r.projectId !== p.id || r.sourceId === r.targetId || ![r.sourceId, r.targetId].every(id => p.objects.some(o => o.id === id)) || p.relationships.some(edge => edge.id === r.id || (edge.sourceId === r.sourceId && edge.targetId === r.targetId))) return project;
        return { ...p, relationships: [...p.relationships, r] };
      }
      case "disconnect": return { ...p, relationships: p.relationships.filter(r => r.id !== mutation.relationshipId) };
    }
  });
}
