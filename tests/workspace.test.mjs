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
const { PROJECTS_KEY, LEGACY_PROJECTS_KEY, newObject } = await import("../src/lib/projects.ts");

let workspace;
let route = "/";
const router = { push: value => { route = value; }, replace: value => { route = value; }, prefetch: () => {}, back() {}, forward() {}, refresh() {} };
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
async function flush() { await act(async () => workspace.flush()); }

test("actual homepage, creation dialog, settings and notebook interactions persist", async () => {
  await render("home", true);
  await click("New project");
  await fill(input("Project title"), "Interaction test research");
  await fill(input("Description"), "A description entered through the creation form.");
  await click("Create project");
  assert.match(route, /^\/projects\/[^/]+\/settings$/);
  const id = workspace.projects[0].id;
  assert.equal(workspace.projects[0].description, "A description entered through the creation form.");

  await render("settings");
  await fill(input("Project title"), "Edited research title");
  await fill(input("General Reasoning"), "Anthropic");
  await fill(input("General Reasoning model identifier"), "configured-model");
  await fill(input("Research field"), "Physics");
  await fill(input("Experimental environment"), "Python");
  await fill(input("Compute budget"), "42.50");
  await click("Save changes");
  const stored = JSON.parse(localStorage.getItem(PROJECTS_KEY)).projects[0];
  assert.equal(stored.title, "Edited research title");
  assert.equal(stored.settings.modelAssignments["General Reasoning"].modelId, "configured-model");
  assert.equal(stored.settings.computeBudget.amount, 42.5);
  assert.ok(document.querySelector(`a[href="/projects/${id}/notebook"]`));

  await render("notebook");
  await fill(input("Central research direction"), "What explains this observation?");
  await fill(input("New entry type"), "Hypothesis");
  await click("Add entry");
  await fill(input("Entry title"), "A testable hypothesis");
  const body = input("Entry body");
  await act(async () => body.focus());
  await fill(body, "First line\nSecond line — α");
  body.setSelectionRange(5, 5);
  assert.equal(body.selectionStart, 5);
  await flush();
  assert.equal(input("Entry body"), body, "Editor is not remounted during saving");
  assert.equal(body.selectionStart, 5, "Autosaving preserves cursor position");
  assert.equal(workspace.projects[0].objects[0].type, "Hypothesis");
  await fill(input("Entry type"), "Observation");
  await flush();
  await render("notebook", true);
  assert.equal(input("Entry body").value, "First line\nSecond line — α");
  assert.equal(input("Entry type").value, "Observation");
  assert.equal(input("Central research direction").value, "What explains this observation?");

  await render("home");
  await fill(input("Search projects"), "absent search");
  assert.match(container.textContent, /No projects found/);
  await fill(input("Search projects"), "Edited research");
  assert.ok(document.querySelector(`a[href="/projects/${id}"]`));

  await render("notebook");
  await click("Delete entry A testable hypothesis");
  assert.equal(workspace.projects[0].objects.length, 0);
  assert.equal(JSON.parse(localStorage.getItem(PROJECTS_KEY)).projects[0].objects.length, 0);
});

test("autosave debounces writing, flushes on pagehide, and synchronizes another tab", async () => {
  await render("notebook", true);
  await click("Add entry");
  await flush();
  const before = localStorage.getItem(PROJECTS_KEY);
  await fill(input("Entry title"), "Debounced title");
  await fill(input("Entry body"), "Debounced content");
  assert.equal(localStorage.getItem(PROJECTS_KEY), before, "Keystrokes do not immediately write storage");
  await act(async () => new Promise(resolve => setTimeout(resolve, 700)));
  assert.equal(JSON.parse(localStorage.getItem(PROJECTS_KEY)).projects[0].objects[0].body, "Debounced content");
  await fill(input("Entry body"), "Flush before leaving");
  await act(async () => window.dispatchEvent(new Event("pagehide")));
  assert.equal(JSON.parse(localStorage.getItem(PROJECTS_KEY)).projects[0].objects[0].body, "Flush before leaving");
  const remote = JSON.parse(localStorage.getItem(PROJECTS_KEY));
  remote.projects[0].objects.push({ ...newObject(remote.projects[0].id, "Question"), title: "Another tab's entry" });
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(remote));
  await act(async () => window.dispatchEvent(new StorageEvent("storage", { key: PROJECTS_KEY })));
  assert.equal(workspace.projects[0].objects.length, 2);
  assert.match(container.textContent, /Research entries 2/);
});

test("Canvas controls place, create, edit, connect and delete shared entries", async () => {
  await render("canvas", true);
  const first = workspace.projects[0].objects[0];
  await fill(input("Existing entry to place"), first.id);
  await click("Place");
  assert.equal(workspace.projects[0].placements.length, 1);
  await fill(input("New node type"), "Observation");
  await click("New entry");
  await fill(input("Entry title"), "Canvas observation");
  await fill(input("Entry body"), "Content written on the canvas.");
  await click("Done");
  const created = workspace.projects[0].objects.find(o => o.title === "Canvas observation");
  assert.ok(created);
  assert.equal(workspace.projects[0].placements.length, 2);
  await click("Connect");
  await fill(input("Connection source"), first.id);
  await fill(input("Connection target"), created.id);
  await click("Add connection");
  assert.equal(workspace.projects[0].relationships.length, 1);
  await flush();
  await render("canvas", true);
  assert.equal(workspace.projects[0].relationships.length, 1);
  assert.equal(workspace.projects[0].placements.length, 2);
  await render("notebook");
  assert.ok([...document.querySelectorAll("textarea")].some(field => field.value === "Content written on the canvas."));
  await render("canvas");
  await click("Edit Canvas observation");
  await fill(input("Entry body"), "Edited again from Canvas");
  await click("Done");
  await render("notebook");
  assert.ok([...document.querySelectorAll("textarea")].some(field => field.value === "Edited again from Canvas"));
  await click("Delete entry Canvas observation");
  assert.equal(workspace.projects[0].relationships.length, 0);
  assert.ok(!workspace.projects[0].placements.some(p => p.objectId === created.id));
});

test("project routing remembers research views and exposes exactly two tabs plus settings", async () => {
  await render("notebook-route");
  assert.equal(workspace.projects[0].lastVisitedView, "notebook");
  assert.equal(document.querySelectorAll('nav[aria-label="Research views"] a').length, 2);
  assert.equal(document.querySelector('nav a[aria-current="page"]').textContent, "Notebook");
  assert.ok(document.querySelector('a[aria-label="Project settings"]'));
  await flush();
  await render("entry");
  assert.equal(route, `/projects/${workspace.projects[0].id}/notebook`);
  await act(async () => workspace.update(workspace.projects[0].id, { lastVisitedView: "canvas" }));
  await flush();
  assert.equal(route, `/projects/${workspace.projects[0].id}/canvas`);
  await render("missing");
  assert.match(container.textContent, /That project isn’t here/);
});

test("failed autosave retains the draft and Retry saving persists it", async () => {
  await render("notebook", true);
  const original = dom.window.Storage.prototype.setItem;
  dom.window.Storage.prototype.setItem = () => { throw new Error("Storage full"); };
  try {
    await fill(input("Entry body"), "Do not lose this draft");
    await flush();
    assert.match(document.querySelector('[role="alert"]').textContent, /Changes are not saved/);
    assert.equal(input("Entry body").value, "Do not lose this draft");
  } finally { dom.window.Storage.prototype.setItem = original; }
  await click("Retry saving");
  assert.equal(JSON.parse(localStorage.getItem(PROJECTS_KEY)).projects[0].objects[0].body, "Do not lose this draft");
  assert.equal(document.querySelector('[role="alert"]'), null);
});

test("legacy projects render as structured entries in the actual Notebook", async () => {
  await act(async () => root.unmount()); root = null;
  localStorage.clear();
  const legacy = [{ id: "legacy-project", title: "Preserved project", description: "", question: "Legacy direction", notes: "Legacy notes\nStill here", createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-02-01T00:00:00Z" }];
  localStorage.setItem(LEGACY_PROJECTS_KEY, JSON.stringify(legacy));
  await render("notebook", true);
  assert.equal(input("Entry body").value, "Legacy notes\nStill here");
  assert.equal(input("Entry title").value, "Previous research notes");
  await fill(input("Entry body"), "Updated migrated notes");
  await flush();
  assert.equal(localStorage.getItem(LEGACY_PROJECTS_KEY), JSON.stringify(legacy));
  await act(async () => root.unmount()); root = null;
});
