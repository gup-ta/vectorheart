import assert from "node:assert/strict";
import { test, beforeEach } from "node:test";
import { localProjectRepository as repository, PROJECTS_KEY, LEGACY_PROJECTS_KEY, newProject, newObject, defaultSettings, OPERATIONS, applyMutation } from "../src/lib/projects.ts";

const storage = new Map();
globalThis.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
beforeEach(() => storage.clear());
const legacy = { id: "existing", title: "Existing research", description: "Keep this", question: "Why?", notes: "Line one\nLine two — α", createdAt: "2026-11-15T00:00:00.000Z", updatedAt: "2026-11-15T00:00:00.000Z" };
function fixture() {
  const project = newProject("Research", "Description", "project-a");
  const hypothesis = newObject(project.id, "Hypothesis");
  const observation = newObject(project.id, "Observation");
  let state = applyMutation([project], { kind: "add-object", projectId: project.id, object: hypothesis, position: { x: 30, y: -40 } });
  state = applyMutation(state, { kind: "add-object", projectId: project.id, object: observation, position: { x: 400, y: 100 } });
  const relationship = { id: "connection", projectId: project.id, sourceId: hypothesis.id, targetId: observation.id };
  state = applyMutation(state, { kind: "connect", projectId: project.id, relationship });
  return { state, project, hypothesis, observation, relationship };
}

test("new projects have stable IDs, timestamps, and independent Automatic assignments", () => {
  const first = newProject("  First  ", "Context");
  const second = newProject("Second", "");
  assert.notEqual(first.id, second.id);
  assert.equal(first.title, "First");
  assert.ok(Number.isFinite(Date.parse(first.createdAt)));
  assert.equal(first.lastVisitedView, null);
  OPERATIONS.forEach(operation => assert.deepEqual(first.settings.modelAssignments[operation], { provider: "Automatic", modelId: "" }));
  first.settings.modelAssignments[OPERATIONS[0]].provider = "OpenAI";
  assert.equal(second.settings.modelAssignments[OPERATIONS[0]].provider, "Automatic");
});

test("legacy migration preserves metadata, question, multiline notes, and original storage", () => {
  const original = JSON.stringify([legacy]);
  storage.set(LEGACY_PROJECTS_KEY, original);
  const [migrated] = repository.load();
  assert.equal(migrated.id, legacy.id);
  assert.equal(migrated.question, legacy.question);
  assert.equal(migrated.objects[0].body, legacy.notes);
  assert.equal(migrated.objects[0].projectId, legacy.id);
  assert.equal(migrated.createdAt, legacy.createdAt);
  assert.deepEqual(repository.load(), [migrated]);
  repository.save([migrated]);
  assert.deepEqual(repository.load(), [migrated]);
  assert.equal(storage.get(LEGACY_PROJECTS_KEY), original);
});

test("empty legacy notes do not create placeholder entries", () => {
  storage.set(LEGACY_PROJECTS_KEY, JSON.stringify([{ ...legacy, notes: "" }]));
  assert.equal(repository.load()[0].objects.length, 0);
});

test("empty v2 workspace does not resurrect deleted legacy projects", () => {
  storage.set(LEGACY_PROJECTS_KEY, JSON.stringify([legacy]));
  repository.save([]);
  assert.deepEqual(repository.load(), []);
});

test("metadata, all provider assignments, preferences, and last research view persist", () => {
  const project = newProject("Original", "");
  const settings = defaultSettings();
  settings.modelAssignments["Hypothesis Construction"] = { provider: "Custom", modelId: "my-local-model" };
  settings.researchField = "Machine Learning"; settings.environment = "Python"; settings.computeBudget = { amount: 125.50, unit: "USD" };
  const state = applyMutation([project], { kind: "project", projectId: project.id, patch: { title: "Edited", description: "New description", settings, lastVisitedView: "canvas" } });
  repository.save(state);
  assert.deepEqual(repository.load(), state);
});

test("shared object edits, type changes, positions and connections survive reload", () => {
  const { state, project, hypothesis } = fixture();
  let edited = applyMutation(state, { kind: "edit-object", projectId: project.id, objectId: hypothesis.id, patch: { title: "A shared thought", body: "Long research\nMultiline body", type: "Question" } });
  edited = applyMutation(edited, { kind: "place", projectId: project.id, placement: { objectId: hypothesis.id, position: { x: -900, y: 123.5 } } });
  repository.save(edited);
  const [loaded] = repository.load();
  assert.equal(loaded.objects.length, 2);
  assert.equal(loaded.objects[0].body, "Long research\nMultiline body");
  assert.equal(loaded.objects[0].type, "Question");
  assert.deepEqual(loaded.placements.find(p => p.objectId === hypothesis.id).position, { x: -900, y: 123.5 });
  assert.equal(loaded.relationships.length, 1);
});

test("removing a placement keeps its Notebook object; deleting an object removes all references", () => {
  const { state, project, hypothesis } = fixture();
  const unplaced = applyMutation(state, { kind: "unplace", projectId: project.id, objectId: hypothesis.id });
  assert.equal(unplaced[0].objects.length, 2);
  assert.equal(unplaced[0].placements.length, 1);
  const deleted = applyMutation(state, { kind: "delete-object", projectId: project.id, objectId: hypothesis.id });
  assert.equal(deleted[0].objects.length, 1); assert.equal(deleted[0].placements.length, 1); assert.equal(deleted[0].relationships.length, 0);
  repository.save(deleted);
  assert.deepEqual(repository.load(), deleted);
});

test("duplicate, self, foreign-project and dangling relationships are rejected", () => {
  const { state, project, relationship } = fixture();
  for (const change of [{ id: "duplicate" }, { id: "self", targetId: relationship.sourceId }, { id: "missing", targetId: "absent" }, { id: "foreign", projectId: "another-project" }]) {
    const next = applyMutation(state, { kind: "connect", projectId: project.id, relationship: { ...relationship, ...change } });
    assert.equal(next[0].relationships.length, 1);
  }
});

test("connections can be independently deleted", () => {
  const { state, project, relationship } = fixture();
  const result = applyMutation(state, { kind: "disconnect", projectId: project.id, relationshipId: relationship.id });
  assert.equal(result[0].relationships.length, 0); assert.equal(result[0].objects.length, 2);
});

test("field-level rebase preserves other-tab edits and does not resurrect deleted objects", () => {
  const { state, project, hypothesis } = fixture();
  const otherTab = applyMutation(state, { kind: "edit-object", projectId: project.id, objectId: hypothesis.id, patch: { title: "Other tab title" } });
  const rebased = applyMutation(otherTab, { kind: "edit-object", projectId: project.id, objectId: hypothesis.id, patch: { body: "Local writing" } });
  assert.equal(rebased[0].objects[0].title, "Other tab title");
  assert.equal(rebased[0].objects[0].body, "Local writing");
  const deleted = applyMutation(rebased, { kind: "delete-object", projectId: project.id, objectId: hypothesis.id });
  assert.equal(applyMutation(deleted, { kind: "edit-object", projectId: project.id, objectId: hypothesis.id, patch: { body: "late edit" } })[0].objects.length, 1);
});

test("corrupt, unsupported, duplicate and orphaned v2 data is rejected without overwriting it", () => {
  const { state } = fixture();
  for (const raw of ["broken JSON", "{}", JSON.stringify({ version: 3, projects: state }), JSON.stringify({ version: 2, projects: [...state, ...state] }), JSON.stringify({ version: 2, projects: [{ ...state[0], placements: [{ objectId: "missing", position: { x: 0, y: 0 } }] }] })]) {
    storage.set(PROJECTS_KEY, raw); assert.throws(() => repository.load()); assert.equal(storage.get(PROJECTS_KEY), raw);
  }
});

test("invalid legacy data is preserved and storage write failures propagate", () => {
  storage.set(LEGACY_PROJECTS_KEY, "[{}]");
  assert.throws(() => repository.load()); assert.equal(storage.get(LEGACY_PROJECTS_KEY), "[{}]");
  const original = localStorage.setItem;
  localStorage.setItem = () => { throw new Error("Quota exceeded"); };
  try { assert.throws(() => repository.save([newProject("Test", "")]), /Quota exceeded/); }
  finally { localStorage.setItem = original; }
});
