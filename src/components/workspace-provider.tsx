"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { applyMutation, localProjectRepository, LEGACY_PROJECTS_KEY, PROJECTS_KEY, newProject, type Mutation, type Project, type ProjectPatch } from "@/lib/projects";
import { kernel, kernelRepository } from "@/lib/kernel-repository";
type Workspace = { projects: Project[]; ready: boolean; error: string; pending: boolean; create: (title: string, description: string) => string | null; update: (id: string, patch: ProjectPatch) => boolean; remove: (id: string) => boolean; mutate: (mutation: Mutation, immediate?: boolean) => boolean; flush: () => boolean; sync: () => Promise<void> };
const Context = createContext<Workspace | null>(null);
export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [projects,setProjects]=useState<Project[]>([]), [ready,setReady]=useState(false), [error,setError]=useState(""), [pending,setPending]=useState(false), [migration,setMigration]=useState(false);
  const current=useRef<Project[]>([]), queue=useRef<Mutation[]>([]), saving=useRef<Promise<void>|null>(null), active=useRef(false);
  const sync=useCallback(async () => {
    if (saving.current) return saving.current;
    saving.current=(async()=>{
      while(queue.current.length) { await kernelRepository.apply(queue.current[0]); queue.current.shift(); }
      const loaded=await kernelRepository.load();
      current.current=queue.current.reduce((state,m)=>applyMutation(state,m),loaded);
      setProjects(current.current);setPending(queue.current.length>0);setError("");
    })();
    try { await saving.current; } finally {saving.current=null;}
  },[]);
  const flush=useCallback(()=>{ if(!queue.current.length)return true; void sync().catch(e=>setError(String(e)));return false; },[sync]);
  const load=useCallback(async()=>{
    try {
      const stored=localStorage.getItem(PROJECTS_KEY) ?? localStorage.getItem(LEGACY_PROJECTS_KEY);
      if(stored && !localStorage.getItem("vectorheart.kernel.imported.v1")) {setMigration(true);setReady(true);return;}
      await sync();active.current=true;setReady(true);
    } catch(e) {setError(String(e));setReady(true);}
  },[sync]);
  useEffect(()=>{
    void Promise.resolve().then(load); const interval=setInterval(()=>{if(active.current)flush();},10000);
    const hide=()=>{if(document.visibilityState==='hidden')flush();}; const leave=(e:BeforeUnloadEvent)=>{if(queue.current.length){flush();e.preventDefault();e.returnValue='';}};
    window.addEventListener('pagehide',flush);window.addEventListener('beforeunload',leave);document.addEventListener('visibilitychange',hide);
    return()=>{clearInterval(interval);flush();window.removeEventListener('pagehide',flush);window.removeEventListener('beforeunload',leave);document.removeEventListener('visibilitychange',hide);};
  },[load,flush]);
  const mutate=useCallback((m:Mutation,immediate=false)=>{
    if(!active.current)return false; const next=applyMutation(current.current,m);if(next===current.current)return true;
    // Coalesce writing and intermediate canvas positions before server revisions are accepted.
    const previous=queue.current.at(-1);
    if(previous && !saving.current && previous.kind===m.kind && 'projectId' in previous && 'projectId' in m && previous.projectId===m.projectId && (m.kind==='edit-object' && previous.kind==='edit-object' && m.objectId===previous.objectId)) queue.current[queue.current.length-1]={...m,patch:{...previous.patch,...m.patch}};
    else if(previous?.kind==='place' && m.kind==='place' && !saving.current && previous.placement.objectId===m.placement.objectId)queue.current[queue.current.length-1]=m;
    else queue.current.push(m);
    current.current=next;setProjects(next);setPending(true);if(immediate)flush();return true;
  },[flush]);
  function backup(){const blob=new Blob([JSON.stringify({v1:localStorage.getItem(LEGACY_PROJECTS_KEY),v2:localStorage.getItem(PROJECTS_KEY)},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='vectorheart-browser-backup.json';a.click();URL.revokeObjectURL(url);}
  async function importData(){try {const raw=localStorage.getItem(PROJECTS_KEY);const parsed=raw?JSON.parse(raw):null;if(parsed&&parsed.version!==2)throw new Error('Unsupported browser schema; export the backup for recovery.');const projects=parsed?parsed.projects:localProjectRepository.load();const result=await kernel<{warnings:string[]}>("import","POST",{projects,original_backup:{v1:localStorage.getItem(LEGACY_PROJECTS_KEY),v2:raw}});await sync();localStorage.setItem('vectorheart.kernel.imported.v1','yes');setMigration(false);active.current=true;setError(result.warnings.join('; '));}catch(e){setError(String(e));}}
  return <Context.Provider value={{projects,ready,error,pending,sync,flush,mutate,create:(title,description)=>{const p=newProject(title,description);return mutate({kind:'create',project:p},true)?p.id:null;},update:(id,patch)=>mutate({kind:'project',projectId:id,patch}),remove:id=>mutate({kind:'remove',projectId:id},true)}}>
    {error&&<div className="storage-error" role="alert">{error} <button className="text-button" onClick={()=>void load()}>Retry connection</button><button className="text-button" onClick={()=>void sync().catch(e=>setError(String(e)))}>Retry saving</button></div>}
    {migration?<main className="project-content"><h1>Bring your research into the kernel.</h1><p className="subtitle">Export a backup, then import your browser projects. Original records stay intact. Existing kernel projects are preserved.</p><button className="text-button" onClick={backup}>Export JSON backup</button><button className="primary-button" onClick={()=>void importData()}>Import and open workspace</button></main>:children}
  </Context.Provider>;
}
export function useWorkspace(){const value=useContext(Context);if(!value)throw new Error('Missing workspace provider');return value;}
