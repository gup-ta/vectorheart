"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Background, BackgroundVariant, Controls, Handle, MarkerType, Position, ReactFlow, ReactFlowProvider, useReactFlow, type Connection, type Node, type NodeProps, type OnNodesChange } from "@xyflow/react";
import { MousePointer2, Minus, Pencil, Plus, X } from "lucide-react";
import { newObject, OBJECT_TYPES, type ObjectType, type Project, type ResearchObject } from "@/lib/projects";
import { useWorkspace } from "./workspace-provider";
import { ResearchEntry, TYPE_ICONS } from "./research-entry";

type ToolMode = "select" | "connect" | "disconnect";
type ResearchNode = Node<{ object: ResearchObject; edit: (id: string) => void; mode: ToolMode; endpoint: boolean }, "research">;
function ResearchNodeView({ data, selected }: NodeProps<ResearchNode>) {
  const Icon = TYPE_ICONS[data.object.type];
  return <div className={`research-node ${selected ? "node-selected" : ""} ${data.endpoint ? "node-endpoint" : ""}`}>
    <Handle type="target" position={Position.Left} isConnectable={data.mode === "select"} aria-label="Incoming connection" />
    <div className="node-type"><Icon size={14} /><span>{data.object.type}</span><button className="icon-button nodrag" disabled={data.mode !== "select"} aria-label={`Edit ${data.object.title || "Untitled"}`} onClick={event => { event.stopPropagation(); data.edit(data.object.id); }}><Pencil size={14} /></button></div>
    <h3>{data.object.title || "Untitled"}</h3>{data.object.body && <p>{data.object.body}</p>}
    <Handle type="source" position={Position.Right} isConnectable={data.mode === "select"} aria-label="Outgoing connection" />
  </div>;
}
const nodeTypes = { research: ResearchNodeView };

function ObjectDialog({ object, close }: { object: ResearchObject; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog ref={ref} className="object-dialog" aria-label="Edit research entry" onCancel={close} onClick={event => { if (event.target === event.currentTarget) close(); }}>
    <div className="object-dialog-header"><span>Shared with your Notebook</span><button className="icon-button" aria-label="Close entry editor" onClick={close}><X size={18} /></button></div>
    <ResearchEntry object={object} onDelete={close} autoFocus />
    <button className="text-button" onClick={close}>Done</button>
  </dialog>;
}

export function ResearchCanvas({ project }: { project: Project }) {
  return <ReactFlowProvider><CanvasSurface project={project} /></ReactFlowProvider>;
}

function CanvasSurface({ project }: { project: Project }) {
  const { mutate, flush } = useWorkspace();
  const flow = useReactFlow<ResearchNode>();
  const surface = useRef<HTMLDivElement>(null);
  const lastToolClick = useRef(0);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [newType, setNewType] = useState<ObjectType>("Note");
  const [existingId, setExistingId] = useState("");
  const [mode, setMode] = useState<ToolMode>("select");
  const [endpoint, setEndpoint] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<string[]>([]);
  const [feedback, setFeedback] = useState("");
  const changeMode = useCallback((next: ToolMode) => {
    setMode(next); setEndpoint(null); setCandidates([]); setFeedback("");
    setSelectedNodes([]); setSelectedEdge(null);
  }, []);
  useEffect(() => {
    function cancel(event: KeyboardEvent) { if (event.key === "Escape") changeMode("select"); }
    window.addEventListener("keydown", cancel);
    return () => window.removeEventListener("keydown", cancel);
  }, [changeMode]);
  useEffect(() => () => { flush(); }, [flush]);
  const editing = project.objects.find(o => o.id === editingId);
  const placedIds = useMemo(() => new Set(project.placements.map(p => p.objectId)), [project.placements]);
  const unplaced = project.objects.filter(o => !placedIds.has(o.id));
  const nodes: ResearchNode[] = useMemo(() => project.placements.flatMap(placement => {
    const object = project.objects.find(o => o.id === placement.objectId);
    return object ? [{ id: object.id, type: "research" as const, position: placement.position, selected: selectedNodes.includes(object.id), data: { object, edit: setEditingId, mode, endpoint: endpoint === object.id }, ariaLabel: `${object.type}: ${object.title || "Untitled"}` }] : [];
  }), [project.placements, project.objects, selectedNodes, mode, endpoint]);
  const edges = useMemo(() => project.relationships.filter(r => placedIds.has(r.sourceId) && placedIds.has(r.targetId)).map(r => ({ id: r.id, source: r.sourceId, target: r.targetId, type: "smoothstep", selected: selectedEdge === r.id, markerEnd: { type: MarkerType.ArrowClosed, color: "#a2674b" }, style: { stroke: "#a2674b", strokeWidth: selectedEdge === r.id || (mode === "disconnect" && (r.sourceId === endpoint || r.targetId === endpoint)) ? 2.5 : 1.3 }, ariaLabel: `Connection from ${project.objects.find(o => o.id === r.sourceId)?.title || "Untitled"} to ${project.objects.find(o => o.id === r.targetId)?.title || "Untitled"}` })), [project.relationships, project.objects, placedIds, selectedEdge, mode, endpoint]);

  const onNodesChange: OnNodesChange<ResearchNode> = useCallback(changes => {
    for (const change of changes) {
      if (mode === "select" && change.type === "position" && change.position) mutate({ kind: "place", projectId: project.id, placement: { objectId: change.id, position: change.position } });
      if (change.type === "select") setSelectedNodes(ids => change.selected ? [...new Set([...ids, change.id])] : ids.filter(id => id !== change.id));
    }
  }, [mutate, project.id, mode]);
  function centerPosition() {
    const rect = surface.current?.getBoundingClientRect();
    return rect ? flow.screenToFlowPosition({ x: rect.left + rect.width / 2 - 130, y: rect.top + rect.height / 2 - 60 }) : { x: 80, y: 80 };
  }
  function connect(connection: Pick<Connection, "source" | "target">) {
    if (!connection.source || !connection.target || connection.source === connection.target) return false;
    if (project.relationships.some(r => r.sourceId === connection.source && r.targetId === connection.target && !r.type)) { setFeedback("That directed connection already exists."); return false; }
    return mutate({ kind: "connect", projectId: project.id, relationship: { id: crypto.randomUUID(), projectId: project.id, sourceId: connection.source, targetId: connection.target } });
  }
  function disconnect(id: string) {
    if (project.relationships.some(r => r.id === id) && mutate({ kind: "disconnect", projectId: project.id, relationshipId: id })) changeMode("select");
  }
  function chooseNode(id: string) {
    if (mode === "select") return;
    lastToolClick.current = Date.now();
    setCandidates([]); setFeedback("");
    if (!endpoint || !placedIds.has(endpoint)) { setEndpoint(id); return; }
    if (id === endpoint) { setFeedback("Choose a different entry."); return; }
    if (mode === "connect") {
      if (connect({ source: endpoint, target: id })) changeMode("select");
    } else {
      const matches = project.relationships.filter(r => (r.sourceId === endpoint && r.targetId === id) || (r.sourceId === id && r.targetId === endpoint));
      if (matches.length === 1) disconnect(matches[0].id);
      else if (matches.length > 1) setCandidates(matches.map(r => r.id));
      else setFeedback("These entries have no connection.");
    }
  }
  function removePlacements(ids: string[]) {
    for (const objectId of ids) mutate({ kind: "unplace", projectId: project.id, objectId });
    setSelectedNodes([]);
  }

  return <main className="canvas-workspace" aria-label="Research Canvas">
    <div className="canvas-toolbar"><div className="canvas-create"><select aria-label="New node type" value={newType} onChange={e => setNewType(e.target.value as ObjectType)}>{OBJECT_TYPES.map(type => <option key={type}>{type}</option>)}</select><button className="text-button" onClick={() => { const object = newObject(project.id, newType); mutate({ kind: "add-object", projectId: project.id, object, position: centerPosition() }); changeMode("select"); setEditingId(object.id); }}><Plus size={16} /> New entry</button></div>
      <div className="canvas-place"><select aria-label="Existing entry to place" value={existingId} onChange={e => setExistingId(e.target.value)}><option value="">Place an existing entry…</option>{unplaced.map(o => <option value={o.id} key={o.id}>{o.type}: {o.title || "Untitled"}</option>)}</select><button className="text-button" disabled={!unplaced.some(o => o.id === existingId)} onClick={() => { mutate({ kind: "place", projectId: project.id, placement: { objectId: existingId, position: centerPosition() } }); setExistingId(""); }}>Place</button></div>
      <div className="canvas-tools" role="group" aria-label="Canvas tools">{([["select", "Select", MousePointer2], ["connect", "Connect", Plus], ["disconnect", "Disconnect", Minus]] as const).map(([tool, label, Icon]) => <button key={tool} className="icon-button" aria-label={label} title={label} aria-pressed={mode === tool} onClick={() => changeMode(tool)}><Icon size={17} /></button>)}</div>
    </div>
    {candidates.length > 0 && <div className="relationship-picker" role="group" aria-label="Choose connection to remove"><span>Choose a connection to remove:</span>{project.relationships.filter(r => candidates.includes(r.id)).map(r => <button className="text-button" key={r.id} onClick={() => disconnect(r.id)}>{project.objects.find(o => o.id === r.sourceId)?.title || "Untitled"} &rarr; {project.objects.find(o => o.id === r.targetId)?.title || "Untitled"} &middot; {r.type || "Untyped"}</button>)}</div>}
    <div className={`canvas-surface canvas-mode-${mode}`} ref={surface}>
      <ReactFlow<ResearchNode> nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onConnect={connect}
        onNodeClick={(_, node) => chooseNode(node.id)}
        onNodeDoubleClick={(_, node) => { if (mode === "select" && Date.now() - lastToolClick.current > 400) setEditingId(node.id); }}
        nodesDraggable={mode === "select"} nodesConnectable={mode === "select"}
        onKeyDown={event => { if (mode !== "select" && (event.key === "Enter" || event.key === " ")) { const node = (event.target as HTMLElement).closest(".react-flow__node"); const id = node?.getAttribute("data-id"); if (id) { event.preventDefault(); chooseNode(id); } } }}
        onEdgeClick={(_, edge) => { if (mode === "select") setSelectedEdge(edge.id); }} onPaneClick={() => { setSelectedEdge(null); setEndpoint(null); setCandidates([]); setFeedback(""); }}
        onEdgesChange={changes => { for (const change of changes) if (change.type === "select") setSelectedEdge(id => change.selected ? change.id : id === change.id ? null : id); }}
        onBeforeDelete={async ({ nodes: deleting }) => !deleting.length || window.confirm("Remove selected entries and their visible connections from the Canvas? Their content stays in the Notebook.")}
        onNodesDelete={deleted => removePlacements(deleted.map(node => node.id))}
        onEdgesDelete={deleted => { for (const edge of deleted) mutate({ kind: "disconnect", projectId: project.id, relationshipId: edge.id }); }}
        isValidConnection={connection => connection.source !== connection.target && !project.relationships.some(r => r.sourceId === connection.source && r.targetId === connection.target && !r.type)}
        fitView minZoom={0.15} maxZoom={2.5} deleteKeyCode={mode === "select" ? ["Backspace", "Delete"] : null} defaultEdgeOptions={{ interactionWidth: 24 }}>
        <Background variant={BackgroundVariant.Dots} gap={28} size={0.7} color="#d8cfc2" />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
      {!nodes.length && <div className="canvas-empty">Place a notebook entry or start a new thought.</div>}
      {mode === "select" && (selectedNodes.length > 0 || selectedEdge) && <div className="canvas-selection">{selectedNodes.length > 0 && <button className="text-button" onClick={() => { if (window.confirm("Remove selected entries from the Canvas? They will remain in the Notebook.")) removePlacements(selectedNodes); }}>Remove from canvas</button>}{selectedEdge && <button className="text-button" onClick={() => { mutate({ kind: "disconnect", projectId: project.id, relationshipId: selectedEdge }); setSelectedEdge(null); }}>Delete connection</button>}</div>}
    </div>
    <p className="canvas-help" role="status">{feedback || (mode === "select" ? "Drag to arrange · Connect the small handles · Double-click an entry to write" : mode === "connect" ? endpoint ? "Choose the target entry. Escape to cancel." : "Choose the source entry. Escape to cancel." : endpoint ? "Choose the other endpoint. Escape to cancel." : "Choose an endpoint to disconnect. Escape to cancel.")}</p>
    {editing && <ObjectDialog object={editing} close={() => setEditingId(null)} />}
  </main>;
}
