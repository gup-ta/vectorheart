"use client";

import { useEffect, useState } from "react";
import { type Project, type ResearchOperation } from "@/lib/projects";
import { kernel } from "@/lib/kernel-repository";

type Capabilities = { providers: { provider: string; default_model: string | null; available: boolean }[]; priority: string[] };

export function ConfiguredModel({ project, role }: { project: Project; role: ResearchOperation }) {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    let active = true;
    void kernel<Capabilities>("intelligence/providers").then(data => { if (active) setCapabilities(data); }).catch(() => { if (active) setUnavailable(true); });
    return () => { active = false; };
  }, []);
  const assignment = project.settings.modelAssignments[role];
  const provider = assignment.provider === "Automatic"
    ? capabilities?.priority.map(name => capabilities.providers.find(p => p.provider === name.trim() && p.available)).find(Boolean)
    : capabilities?.providers.find(p => p.provider === assignment.provider);
  const model = (assignment.provider !== "Automatic" && assignment.modelId) || provider?.default_model;
  const label = unavailable ? "Model configuration unavailable" : !capabilities ? "Reading model configuration…" : provider && model ? `${provider.provider} · ${model}${provider.available ? "" : " · check configuration"}` : "Choose a provider and model in project settings";
  return <small className="configured-model" title={`${role}. Configuration does not guarantee live provider availability.`}>{label}</small>;
}
