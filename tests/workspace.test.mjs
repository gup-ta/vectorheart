import assert from "node:assert/strict";
import { test, after } from "node:test";
import { JSDOM } from "jsdom";

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', { url: "http://localhost:3000", pretendToBeVisual: true });
globalThis.self = dom.window;
after(async () => { if(root) await act(async()=>root.unmount());dom.window.close(); });
for (const key of ["window", "document", "HTMLElement", "HTMLInputElement", "HTMLTextAreaElement", "HTMLSelectElement", "HTMLDialogElement", "Element", "Node", "MutationObserver", "Event", "CustomEvent", "MouseEvent", "StorageEvent", "localStorage", "getComputedStyle"]) {
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
const { ResearchIntelligence } = await import("../src/components/research-intelligence.tsx");



const { spawn, spawnSync } = await import('node:child_process');
const { mkdtempSync } = await import('node:fs');
const { tmpdir } = await import('node:os');
const { join, resolve } = await import('node:path');
const env={...process.env,KERNEL_DB_PATH:join(mkdtempSync(join(tmpdir(),'vh-ui-')),'kernel.sqlite3')};
const python=resolve('backend/.venv/Scripts/python.exe');
const migrated=spawnSync(python,['-m','alembic','-c','backend/alembic.ini','upgrade','head'],{env});
assert.equal(migrated.status,0,migrated.stderr.toString());
const server=spawn(python,['backend/tests/ui_server.py'],{env,stdio:'ignore',windowsHide:true});
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
  if (view === 'intelligence') return h('div',null,h(ResearchIntelligence,{project}),h(ProjectNotebook,{project}));
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
test('Our vision opens and closes without leaving the workspace or changing research',async()=>{
  await render('home',true);await until(()=>workspace?.ready);
  const before=workspace.projects.length;
  await click('Our vision');
  const vision=document.querySelector('dialog[aria-labelledby="vision-title"]');
  assert.equal(vision.open,true);
  assert.match(vision.textContent,/The Research That Comes Next/);
  assert.match(vision.textContent,/FUTURE POSSIBILITIES/);
  assert.match(vision.textContent,/Acceptance never means scientific verification/);
  assert.equal(vision.querySelectorAll('.vision-capabilities article').length,6);
  await click('Close our vision');
  assert.equal(document.querySelector('dialog[aria-labelledby="vision-title"]'),null);
  assert.equal(workspace.projects.length,before);
  await act(async()=>root.unmount());root=null;
});

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

test('Research Intelligence discusses selected objects, accepts and rejects proposals, and restores conversation',async()=>{
  await render('intelligence',true);await until(()=>workspace.projects.length>0);
  await click('Discuss this research object');await until(()=>document.querySelector('.intelligence-dialog[open]'));
  const selected=input('Discuss research object').value;assert.ok(selected);
  await fill(input('Research question'),'Suggest a useful question about this research.');
  await click('Send');await until(()=>document.body.textContent.includes('Accept proposal'));
  assert.match(document.querySelector('.intelligence-conversation').textContent,/test-only-model/);
  const before=workspace.projects[0].objects.length;
  await click('Accept proposal');await until(()=>workspace.projects[0].objects.length===before+1);
  assert.ok(workspace.projects[0].objects.some(o=>o.title==='An accepted intelligence question'));
  assert.ok(document.querySelector('.intelligence-proposal').textContent.includes('accepted'));
  await until(()=>!document.querySelector('#intelligence-prompt').disabled);
  await fill(input('Research question'),'Suggest another question.');await click('Send');await until(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Reject proposal'));
  await click('Reject proposal');await until(()=>document.querySelector('.intelligence-conversation').textContent.includes('rejected'));
  assert.equal(workspace.projects[0].objects.length,before+1);
  await click('Close Research Intelligence');assert.equal(document.querySelector('.intelligence-dialog'),null);
  await render('intelligence',true);await until(()=>workspace.projects.length>0);
  await click('Research Intelligence');await until(()=>document.querySelector('.intelligence-conversation')?.textContent.includes('rejected'));
  assert.match(document.querySelector('.intelligence-conversation').textContent,/accepted/);
  await click('Close Research Intelligence');
  await render('canvas');assert.ok([...input('Existing entry to place').options].some(o=>o.textContent.includes('An accepted intelligence question')));
  await act(async()=>root.unmount());root=null;
});

test('contextual intelligence shortcuts prefill the selected hypothesis without submitting inference',async()=>{
  await render('intelligence',true);await until(()=>workspace.projects.length>0);
  const project=workspace.projects[0];const object=project.objects.find(o=>o.type==='Hypothesis');assert.ok(object);
  const before=project.objects.length;
  await act(async()=>window.dispatchEvent(new CustomEvent('vectorheart-discuss',{detail:{projectId:project.id,objectId:object.id,mode:'Design Experiment',prompt:'Suggest a discriminating experiment.'}})));
  await until(()=>document.querySelector('.intelligence-dialog[open]'));
  assert.equal(input('Research mode').value,'Design Experiment');
  assert.equal(input('Discuss research object').value,object.id);
  assert.equal(input('Research question').value,'Suggest a discriminating experiment.');
  assert.equal(workspace.projects[0].objects.length,before);
  await click('Close Research Intelligence');
  await act(async()=>root.unmount());root=null;
});

test('journal autosaves revisions, generates a reviewable graph and accepts spatial Accelerate proposals',async()=>{
  await render('notebook',true);await until(()=>workspace.projects.length>0);
  await click('New journal entry');await until(()=>document.querySelector('[aria-label="Journal writing"]'));
  await fill(input('Journal title'),'A free-form research day');
  await fill(input('Journal writing'),'I wonder whether outdoor light and near-work explain the association. This is a question, not a clinical finding.');
  // Exercise the actual debounce, then the navigation/action save barrier.
  await act(async()=>{await new Promise(r=>setTimeout(r,1800));});
  await flush();
  const journal=workspace.projects[0].objects.find(o=>o.title==='A free-form research day');
  assert.equal(journal.metadata.journal_entry,true);assert.ok(journal.currentRevision>=2);
  await click('View saved revisions');await until(()=>document.body.textContent.includes('Revision 1'));
  await render('canvas');
  await click('Update Research Graph');await until(()=>document.body.textContent.includes('Accept graph interpretation'));
  assert.match(document.body.textContent,/review/);
  assert.ok(!workspace.projects[0].objects.some(o=>o.title==='A journal-grounded hypothesis'));
  await click('Accept graph interpretation');await until(()=>workspace.projects[0].objects.some(o=>o.title==='A journal-grounded hypothesis'));
  const interpreted=workspace.projects[0].objects.find(o=>o.title==='A journal-grounded hypothesis');
  assert.equal(interpreted.metadata.origin,'model_interpretation');
  assert.ok(workspace.projects[0].placements.some(p=>p.objectId===interpreted.id));
  await click('AI Accelerate');await until(()=>document.body.textContent.includes('Accept A novel Accelerate hypothesis'));
  const before=workspace.projects[0].objects.length;
  await click('Accept A novel Accelerate hypothesis');await until(()=>workspace.projects[0].objects.length===before+1);
  assert.ok(workspace.projects[0].objects.some(o=>o.metadata?.origin==='ai_accelerate'));
  await render('notebook',true);await until(()=>document.querySelector('[aria-label="Journal writing"]'));
  assert.match(input('Journal writing').value,/outdoor light/);
  assert.ok(workspace.projects[0].objects.some(o=>o.id===interpreted.id));
  await act(async()=>root.unmount());root=null;
});

test('Canvas correction mutations are immediate, buffered, auditable and content-preserving',async()=>{
  await render('notebook',true);await until(()=>workspace.projects.length>0);
  const {newObject}=await import('../src/lib/projects.ts');
  const pid=workspace.projects[0].id,a=newObject(pid),b=newObject(pid);
  await act(async()=>{workspace.mutate({kind:'add-object',projectId:pid,object:{...a,title:'Correction source'}});workspace.mutate({kind:'add-object',projectId:pid,object:{...b,title:'Correction target'}});});
  await flush();const id=crypto.randomUUID();
  await act(async()=>{workspace.mutate({kind:'connect',projectId:pid,relationship:{id,projectId:pid,sourceId:a.id,targetId:b.id,type:'related_to',details:{origin:'researcher_correction',rationale:'A researcher-reported connection.'}}});});
  assert.ok(workspace.projects[0].relationships.some(r=>r.id===id));
  let stored;await act(async()=>{stored=await (await fetch(`/api/kernel/v1/projects/${pid}/relationships`)).json();});
  assert.ok(!stored.some(r=>r.id===id));await flush();
  await act(async()=>{stored=await (await fetch(`/api/kernel/v1/projects/${pid}/relationships`)).json();});
  assert.ok(stored.some(r=>r.id===id));
  await act(async()=>{workspace.mutate({kind:'disconnect',projectId:pid,relationshipId:id,correctionId:crypto.randomUUID(),rationale:'Only correlation was reported.'});});
  assert.ok(!workspace.projects[0].relationships.some(r=>r.id===id));await flush();
  let corrections;await act(async()=>{corrections=await (await fetch(`/api/kernel/v1/projects/${pid}/graph/corrections`)).json();});
  assert.ok(corrections.some(c=>c.kind==='remove_relationship'&&c.rationale==='Only correlation was reported.'));
  assert.ok(workspace.projects[0].objects.some(o=>o.id===a.id)&&workspace.projects[0].objects.some(o=>o.id===b.id));
  await act(async()=>root.unmount());root=null;
});

test('literature sources and grounded connections are inspectable, human-reviewed and shared across reload',async()=>{
  await render('canvas',true);await until(()=>workspace.projects.length>0);
  const hypothesis=workspace.projects[0].objects.find(o=>o.type==='Hypothesis');assert.ok(hypothesis);
  await fill(input('Literature research focus'),hypothesis.id);
  await click('Ground in Literature');await until(()=>document.body.textContent.includes('1 proposed interpretations'));
  const paperButton=[...document.querySelectorAll('.literature-candidates button')][0];assert.ok(paperButton);
  await act(async()=>paperButton.click());await until(()=>document.querySelector('[aria-label="Scholarly source inspection"]'));
  assert.match(document.querySelector('.literature-inspector').textContent,/10.1371\/journal.pone.0181772/);
  assert.match(document.querySelector('.literature-inspector').textContent,/qualifies/);
  assert.ok(!workspace.projects[0].objects.some(o=>o.metadata?.origin==='literature_source'));
  await click('Accept literature relationship');await until(()=>workspace.projects[0].objects.some(o=>o.metadata?.origin==='literature_source'));
  const paper=workspace.projects[0].objects.find(o=>o.metadata?.origin==='literature_source');
  const claim=workspace.projects[0].objects.find(o=>o.metadata?.literature_claim);
  assert.ok(paper&&claim);assert.equal(claim.metadata.source_type,'literature');
  assert.ok(workspace.projects[0].relationships.some(r=>r.sourceId===paper.id&&r.targetId===hypothesis.id&&r.details?.literature_classification==='qualifies'));
  await click('Close literature inspection');
  await render('notebook',true);await until(()=>workspace.projects[0]?.objects.some(o=>o.id===paper.id));
  assert.ok(workspace.projects[0].objects.some(o=>o.id===claim.id));
  await act(async()=>root.unmount());root=null;
});

test('hypothesis inspection exposes real intelligence shortcuts and prepares an approval-aware investigation',async()=>{
  await render('canvas',true);await until(()=>workspace.projects.length>0);
  const project=workspace.projects[0],hypothesis=project.objects.find(o=>o.type==='Hypothesis');assert.ok(hypothesis);
  const before=project.objects.length;
  await act(async()=>workspace.mutate({kind:'place',projectId:project.id,placement:{objectId:hypothesis.id,position:{x:0,y:0}}}));
  await until(()=>[...document.querySelectorAll('button')].some(b=>b.getAttribute('aria-label')===`Edit ${hypothesis.title}`));
  await click(`Edit ${hypothesis.title}`);
  assert.ok(document.querySelector('dialog[aria-label="Edit research entry"][open]'));
  let detail;const receive=event=>{detail=event.detail;};window.addEventListener('vectorheart-discuss',receive);
  await click('Suggest experiment');await until(()=>detail);
  window.removeEventListener('vectorheart-discuss',receive);
  assert.equal(detail.objectId,hypothesis.id);assert.equal(detail.mode,'Design Experiment');
  assert.match(detail.prompt,/conceptual design/);
  await click(`Edit ${hypothesis.title}`);await click('Investigate with tools');
  await until(()=>document.querySelector('.investigate-launch').open);
  assert.match(input('Investigation objective').value,/Investigate this hypothesis/);
  assert.ok(input('Investigation objective').value.includes(hypothesis.title));
  assert.equal(workspace.projects[0].objects.length,before);
  await act(async()=>root.unmount());root=null;
});
