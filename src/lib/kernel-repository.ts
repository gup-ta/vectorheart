import { type Mutation, type Project } from "./projects";
export async function kernel<T>(path: string, method = "GET", data?: unknown): Promise<T> {
  const response = await fetch(`/api/kernel/v1/${path}`, { method, headers: { "Content-Type": "application/json" }, ...(data === undefined ? {} : { body: JSON.stringify(data) }), keepalive: method !== "GET" });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || "Kernel request failed");
  return result as T;
}
export const kernelRepository = {
  async load(): Promise<Project[]> { return (await kernel<Project[]>("projects")).filter(p => !p.settings.archived); },
  async apply(m: Mutation) {
    if (m.kind === "create") return kernel("projects", "POST", m.project);
    const path = `projects/${m.projectId}`;
    switch (m.kind) {
      case "remove": return kernel(path, "DELETE");
      case "project": return kernel(path, "PATCH", m.patch);
      case "add-object": await kernel(`${path}/objects`, "POST", m.object); if (m.position) await kernel(`${path}/canvas/${m.object.id}`, "PUT", m.position); return;
      case "edit-object": return kernel(`${path}/objects/${m.objectId}`, "PATCH", m.patch);
      case "delete-object": return kernel(`${path}/objects/${m.objectId}`, "DELETE");
      case "place": return kernel(`${path}/canvas/${m.placement.objectId}`, "PUT", m.placement.position);
      case "unplace": return kernel(`${path}/canvas/${m.objectId}`, "DELETE");
      case "connect": return kernel(`${path}/relationships`, "POST", m.relationship);
      case "disconnect": return kernel(`${path}/relationships/${m.relationshipId}`, "DELETE");
    }
  },
};
