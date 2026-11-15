export type Project = {
  id: string;
  title: string;
  description: string;
  question: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
};

// Replace this adapter when a remote persistence layer is introduced.
export interface ProjectRepository {
  load(): Project[];
  save(projects: Project[]): void;
}

export const PROJECTS_KEY = "vectorheart.projects.v1";

function isProject(value: unknown): value is Project {
  if (!value || typeof value !== "object") return false;
  const p = value as Record<string, unknown>;
  return ["id", "title", "description", "question", "notes", "createdAt", "updatedAt"].every(key => typeof p[key] === "string") &&
    !!p.id && !!p.title && Number.isFinite(Date.parse(p.createdAt as string)) && Number.isFinite(Date.parse(p.updatedAt as string));
}

export const localProjectRepository: ProjectRepository = {
  load() {
    const raw = localStorage.getItem(PROJECTS_KEY);
    if (raw === null) return [];
    const data: unknown = JSON.parse(raw);
    if (!Array.isArray(data) || !data.every(isProject)) throw new Error("Invalid project data");
    return data;
  },
  save(projects) { localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects)); },
};

export function formatDate(date: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(date));
}
