"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { applyMutation, localProjectRepository, LEGACY_PROJECTS_KEY, PROJECTS_KEY, newProject, type Mutation, type Project, type ProjectPatch } from "@/lib/projects";

type Workspace = {
  projects: Project[]; ready: boolean; error: string; pending: boolean;
  create: (title: string, description: string) => string | null;
  update: (id: string, patch: ProjectPatch) => boolean;
  remove: (id: string) => boolean;
  mutate: (mutation: Mutation, immediate?: boolean) => boolean;
  flush: () => boolean;
};
const Context = createContext<Workspace | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const current = useRef<Project[]>([]);
  const queue = useRef<Mutation[]>([]);
  const blocked = useRef(true);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const flush = useCallback(() => {
    if (!queue.current.length) return true;
    try {
      // Rebase field-level changes onto the latest snapshot, including other tabs.
      const latest = localProjectRepository.load();
      const next = queue.current.reduce((state, mutation) => applyMutation(state, mutation), latest);
      if (next !== latest) localProjectRepository.save(next);
      queue.current = [];
      current.current = next;
      setProjects(next);
      setPending(false);
      setError("");
      return true;
    } catch {
      setError("Changes are not saved. Browser storage may be full, unavailable, or contain unreadable data. Keep this page open and retry saving.");
      return false;
    }
  }, []);

  useEffect(() => {
    function load() {
      try {
        current.current = queue.current.reduce((state, mutation) => applyMutation(state, mutation), localProjectRepository.load());
        setProjects(current.current);
        blocked.current = false;
        if (!queue.current.length) setError("");
      } catch {
        blocked.current = true;
        setError("Saved projects could not be read. Existing data has been preserved. Check browser storage permissions and reload to try again.");
      }
      setReady(true);
    }
    load();
    // A fixed cadence, not a debounce: continued interaction never delays a save.
    const interval = setInterval(flush, 10_000);
    function sync(event: StorageEvent) { if ([PROJECTS_KEY, LEGACY_PROJECTS_KEY, null].includes(event.key)) load(); }
    function hidden() { if (document.visibilityState === "hidden") flush(); }
    function leaving(event: BeforeUnloadEvent) { if (!flush()) { event.preventDefault(); event.returnValue = ""; } }
    window.addEventListener("storage", sync);
    window.addEventListener("pagehide", flush);
    window.addEventListener("beforeunload", leaving);
    document.addEventListener("visibilitychange", hidden);
    return () => {
      window.removeEventListener("storage", sync); window.removeEventListener("pagehide", flush);
      window.removeEventListener("beforeunload", leaving); document.removeEventListener("visibilitychange", hidden);
      clearInterval(interval);
      flush();
    };
  }, [flush]);

  const mutate = useCallback((mutation: Mutation, immediate = false) => {
    if (blocked.current) return false;
    const next = applyMutation(current.current, mutation);
    if (next === current.current) return true;
    queue.current.push(mutation);
    current.current = next;
    setProjects(current.current);
    setPending(true);
    if (immediate) flush();
    // Accepted in memory even if disk saving failed; retain the queued draft.
    return true;
  }, [flush]);

  const create = useCallback((title: string, description: string) => {
    if (!title.trim()) return null;
    const project = newProject(title, description);
    return mutate({ kind: "create", project }, true) ? project.id : null;
  }, [mutate]);
  const update = useCallback((id: string, patch: ProjectPatch) => mutate({ kind: "project", projectId: id, patch }), [mutate]);
  const remove = useCallback((id: string) => mutate({ kind: "remove", projectId: id }, true), [mutate]);

  return <Context.Provider value={{ projects, ready, error, pending, create, update, remove, mutate, flush }}>
    {error && <div role="alert" className="storage-error">{error} {pending && <button className="text-button" onClick={flush}>Retry saving</button>}</div>}{children}
  </Context.Provider>;
}

export function useWorkspace() {
  const context = useContext(Context);
  if (!context) throw new Error("Workspace provider is missing");
  return context;
}
