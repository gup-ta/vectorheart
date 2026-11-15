import assert from "node:assert/strict";
import { test, after } from "node:test";
import { JSDOM } from "jsdom";

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', { url: "http://localhost:3000", pretendToBeVisual: true });
globalThis.self = dom.window;
after(() => dom.window.close());
for (const key of ["window", "document", "HTMLElement", "HTMLInputElement", "HTMLTextAreaElement", "HTMLSelectElement", "HTMLDialogElement", "Element", "Node", "MutationObserver", "Event", "MouseEvent", "StorageEvent", "localStorage", "getComputedStyle"]) {
  Object.defineProperty(globalThis, key, { configurable: true, value: dom.window[key] });
}
Object.defineProperty(globalThis, "navigator", { configurable: true, value: dom.window.navigator });
globalThis.requestAnimationFrame = dom.window.requestAnimationFrame.bind(dom.window);
globalThis.cancelAnimationFrame = dom.window.cancelAnimationFrame.bind(dom.window);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
// DOM tests cover interaction wiring, not visual layout or pointer geometry.
globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
window.ResizeObserver = globalThis.ResizeObserver;
window.confirm = () => true;
HTMLDialogElement.prototype.showModal = function () { this.open = true; };
HTMLDialogElement.prototype.close = function () { this.open = false; };

const { createElement: h, act } = await import("react");
const { createRoot } = await import("react-dom/client");
const { AppRouterContext } = await import("next/dist/shared/lib/app-router-context.shared-runtime.js");
const { WorkspaceProvider, useWorkspace } = await import("../src/components/workspace-provider.tsx");
const { default: Home } = await import("../src/app/page.tsx");
const { ProjectOverview } = await import("../src/components/project-overview.tsx");
const { ProjectNotebook } = await import("../src/components/project-notebook.tsx");
const { ResearchCanvas } = await import("../src/components/research-canvas.tsx");
const { ProjectWorkspace } = await import("../src/components/project-workspace.tsx");



const { spawn, spawnSync } = await import('node:child_process');
const { mkdtempSync } = await import('node:fs');
const { tmpdir } = await import('node:os');
const { join, resolve } = await import('node:path');
const env={...process.env,KERNEL_DB_PATH:join(mkdtempSync(join(tmpdir(),'vh-ui-')),'kernel.sqlite3')};
const python=resolve('backend/.venv/Scripts/python.exe');
const migrated=spawnSync(python,['-m','alembic','-c','backend/alembic.ini','upgrade','head'],{env});
assert.equal(migrated.status,0,migrated.stderr.toString());
const server=spawn(python,['-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8002'],{env,stdio:'ignore',windowsHide:true});
after(()=>server.kill());
const nativeFetch=globalThis.fetch;
globalThis.fetch=(url,options)=>nativeFetch(String(url).replace('/api/kernel','http://127.0.0.1:8002'),options);
for(let i=0;i<100;i++){try{if((await nativeFetch('http://127.0.0.1:8002/v1/health')).ok)break;}catch{} await new Promise(r=>setTimeout(r,50));}

let workspace;

const router = { push: () => {}, replace: () => {}, prefetch: () => {}, back() {}, forward() {}, refresh() {} };
function Harness({ view }) {
  workspace = useWorkspace();
  if (!workspace.ready) return null;
  if (view === "home") return h(Home);
  const project = workspace.projects[0];
  if (!project) return null;
  if (view === "entry") return h(ProjectWorkspace, { id: project.id });
  if (view === "missing") return h(ProjectWorkspace, { id: "nonexistent" });
  if (view === "notebook-route") return h(ProjectWorkspace, { id: project.id, view: "notebook" });
  return view === "settings" ? h(ProjectOverview, { project }) : view === "canvas" ? h(ResearchCanvas, { project }) : h(ProjectNotebook, { project });
}
const container = document.getElementById("root");
let root;
async function render(view, fresh = false) {
  if (fresh && root) await act(async () => root.unmount());
  if (!root || fresh) root = createRoot(container);
  await act(async () => root.render(h(AppRouterContext.Provider, { value: router }, h(WorkspaceProvider, null, h(Harness, { view })))));
}
function input(label) {
  const direct = [...document.querySelectorAll("input, textarea, select")].find(element => element.getAttribute("aria-label") === label);
  if (direct) return direct;
  const associated = [...document.querySelectorAll("label")].find(element => element.textContent.trim().startsWith(label));
  assert.ok(associated, `Missing field ${label}`);
  return document.getElementById(associated.htmlFor);
}
async function fill(element, value) {
  assert.ok(element, "Field exists");
  await act(async () => {
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, "value").set.call(element, value);
    element.dispatchEvent(new Event(element instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
  });
}
async function click(text) {
  const button = [...document.querySelectorAll("button")].find(element => element.textContent.trim() === text || element.getAttribute("aria-label") === text);
  assert.ok(button, `Missing button ${text}`);
  await act(async () => button.click());
}
async function flush() { await act(async () => workspace.sync()); }

async function settle(){await act(async()=>{await new Promise(r=>setTimeout(r,150));});}
async function until(check){for(let i=0;i<60;i++){await settle();if(check())return;}assert.fail('Timed out waiting for kernel/UI');}
test('real kernel-backed Notebook completes First Heartbeat and reloads scientific history',async()=>{
  await render('home',true);await until(()=>workspace?.ready);
  await click('New project');await fill(input('Project title'),'Scientific integration');await click('Create project');await flush();
  await render('notebook');await until(()=>document.body.textContent.includes('Try the First Heartbeat'));
  await click('Try the First Heartbeat');await until(()=>workspace.projects[0].objects.length===3);
  await until(()=>document.body.textContent.includes('Approve'));
  await click('Approve');await until(()=>document.body.textContent.includes('Run approved experiment'));
  await click('Run approved experiment');await until(()=>workspace.projects[0].objects.some(o=>o.type==='Evidence'));
  assert.ok(workspace.projects[0].objects.some(o=>o.type==='Experiment'));
  assert.match(document.body.textContent,/Measured mean:/);
  const hypothesis=workspace.projects[0].objects.find(o=>o.type==='Hypothesis');
  const original=hypothesis.body;
  await click('Research Actions');await fill(input('Research object'),hypothesis.id);
  await fill(input('Proposed statement'),'The claim is supported only within the configured synthetic world.');
  await click('Propose Revision');await until(()=>document.body.textContent.includes('Proposed'));
  await click('Approve');await until(()=>document.body.textContent.includes('Apply approved operation'));
  await click('Apply approved operation');await until(()=>workspace.projects[0].objects.find(o=>o.id===hypothesis.id).body!==original);
  const pid=workspace.projects[0].id;
  const evidence=workspace.projects[0].objects.find(o=>o.type==='Evidence');
  await render('canvas');await fill(input('Existing entry to place'),hypothesis.id);await click('Place');await fill(input('Existing entry to place'),evidence.id);await click('Place');await flush();
  assert.equal(workspace.projects[0].placements.length,2);
  assert.ok(workspace.projects[0].relationships.some(r=>r.sourceId===evidence.id&&r.targetId===hypothesis.id));
  await render('notebook',true);await until(()=>workspace.projects.length>0);
  assert.equal(workspace.projects[0].placements.length,2);
  let revisions;await act(async()=>{revisions=await (await fetch('/api/kernel/v1/projects/'+pid+'/objects/'+hypothesis.id+'/revisions')).json();});
  assert.equal(revisions[0].body_snapshot,original);assert.equal(revisions.length,2);
  await until(()=>document.body.textContent.includes('revision accepted'));
  await act(async()=>root.unmount());root=null;
});
test('explicit browser import preserves raw backup and stable IDs without overwriting kernel projects',async()=>{
  const {PROJECTS_KEY,newProject,newObject}=await import('../src/lib/projects.ts');
  const p=newProject('Imported research','Legacy context');
  p.objects=[{...newObject(p.id),title:'Preserved note',body:'Original browser content'}];
  const raw=JSON.stringify({version:2,projects:[{...p,unknownLegacyField:'retained',relationships:[{id:'dangling-test',projectId:p.id,sourceId:p.objects[0].id,targetId:'missing'}]}]});
  localStorage.setItem(PROJECTS_KEY,raw);localStorage.removeItem('vectorheart.kernel.imported.v1');
  await render('home',true);await until(()=>document.body.textContent.includes('Import and open workspace'));
  assert.ok([...document.querySelectorAll('button')].some(b=>b.textContent==='Export JSON backup'));
  await click('Import and open workspace');await until(()=>workspace.projects.some(v=>v.id===p.id));
  assert.equal(localStorage.getItem(PROJECTS_KEY),raw);
  assert.equal(workspace.projects.find(v=>v.id===p.id).objects[0].body,'Original browser content');
  assert.equal(workspace.projects.find(v=>v.id===p.id).relationships.length,0);
  let trail;await act(async()=>{trail=await (await fetch('/api/kernel/v1/projects/'+p.id+'/events')).json();});
  assert.equal(trail.find(e=>e.event_type==='legacy_import').payload.original_record.unknownLegacyField,'retained');
  await act(async()=>root.unmount());root=null;
});
