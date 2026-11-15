import assert from "node:assert/strict";
import { test, beforeEach } from "node:test";
import { localProjectRepository, PROJECTS_KEY } from "../src/lib/projects.ts";

const store = new Map();
globalThis.localStorage = {
  getItem: key => store.get(key) ?? null,
  setItem: (key, value) => store.set(key, value),
};
beforeEach(() => store.clear());
const project = {
  id: "test-project", title: "A research question", description: "Context",
  question: "Why?", notes: "An observation.",
  createdAt: "2026-11-15T00:00:00.000Z", updatedAt: "2026-11-15T00:00:00.000Z",
};

test("a fresh workspace is empty and deleted projects stay deleted", () => {
  assert.deepEqual(localProjectRepository.load(), []);
  localProjectRepository.save([project]);
  assert.deepEqual(localProjectRepository.load(), [project]);
  localProjectRepository.save([]);
  assert.deepEqual(localProjectRepository.load(), []);
});

test("renamed projects and notebook edits survive a storage round trip", () => {
  const edited = { ...project, title: "Renamed", question: "How?", notes: "First line\nSecond line — α" };
  localProjectRepository.save([edited]);
  assert.deepEqual(localProjectRepository.load(), [edited]);
});

test("corrupt or incompatible data is rejected without being replaced", () => {
  for (const raw of ["broken JSON", "{}", '[{"id":"partial"}]', JSON.stringify([{ ...project, updatedAt: "invalid" }])]) {
    store.set(PROJECTS_KEY, raw);
    assert.throws(() => localProjectRepository.load());
    assert.equal(store.get(PROJECTS_KEY), raw);
  }
});

test("storage write failures propagate to the caller", () => {
  const original = localStorage.setItem;
  localStorage.setItem = () => { throw new Error("Quota exceeded"); };
  try { assert.throws(() => localProjectRepository.save([project]), /Quota exceeded/); }
  finally { localStorage.setItem = original; }
});
