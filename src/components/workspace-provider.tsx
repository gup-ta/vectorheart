"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { localProjectRepository, PROJECTS_KEY, type Project } from "@/lib/projects";

type Workspace = {
  projects: Project[];
  ready: boolean;
  error: string;
  create: (title: string, description: string) => string | null;
  update: (id: string, patch: Partial<Pick<Project, "title" | "description" | "question" | "notes">>) => boolean;
  remove: (id: string) => boolean;
};
const Context = createContext<Workspace | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const current = useRef<Project[]>([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const blocked = useRef(false);

  useEffect(() => {
    function load() {
      try {
        current.current = localProjectRepository.load();
        setProjects(current.current);
        blocked.current = false;
        setError("");
      } catch {
        blocked.current = true;
        setError("Your browser’s saved projects could not be read. Existing data has been preserved. Check browser storage permissions and reload to try again.");
      }
      setReady(true);
    }
    load();
    function sync(event: StorageEvent) { if (event.key === PROJECTS_KEY || event.key === null) load(); }
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);

  function persist(next: Project[]) {
    if (blocked.current) return false;
    try {
      localProjectRepository.save(next);
      current.current = next;
      setProjects(next);
      setError("");
      return true;
    } catch {
      setError("Changes could not be saved. Your browser storage may be full or unavailable. Keep this page open and try again.");
      return false;
    }
  }

  function create(title: string, description: string) {
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    return persist([{ id, title: title.trim(), description: description.trim(), question: "", notes: "", createdAt: now, updatedAt: now }, ...current.current]) ? id : null;
  }
  function update(id: string, patch: Partial<Pick<Project, "title" | "description" | "question" | "notes">>) {
    return persist(current.current.map(p => p.id === id ? { ...p, ...patch, updatedAt: new Date().toISOString() } : p));
  }
  function remove(id: string) { return persist(current.current.filter(p => p.id !== id)); }

  return <Context.Provider value={{ projects, ready, error, create, update, remove }}>
    {error && <div role="alert" className="storage-error">{error}</div>}{children}
  </Context.Provider>;
}

export function useWorkspace() {
  const context = useContext(Context);
  if (!context) throw new Error("Workspace provider is missing");
  return context;
}
