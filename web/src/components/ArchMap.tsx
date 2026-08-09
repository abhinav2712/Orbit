import { useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { ServiceProposal } from "../lib/api";
import ServiceInspector from "./ServiceInspector";

const ROLE_COLOR: Record<string, string> = {
  frontend: "#7dd3fc",
  api: "#7dd3fc",
  worker: "#a78bfa",
  database: "#fb923c",
  cache: "#fb923c",
  storage: "#fb923c",
};

export default function ArchMap({ services }: { services: ServiceProposal[] }) {
  const [selected, setSelected] = useState<ServiceProposal | null>(null);

  const { nodes, edges } = useMemo(() => {
    const publicRoles = new Set(["frontend", "api"]);
    const nodes: Node[] = services.map((s, i) => ({
      id: s.name,
      position: {
        x: (i % 3) * 220,
        y: Math.floor(i / 3) * 140 + (publicRoles.has(s.role) ? 0 : 160),
      },
      data: { label: `${s.name}\n${s.zerops_type}` },
      style: {
        background: "#0f172a",
        border: `1px solid ${ROLE_COLOR[s.role] ?? "#475569"}`,
        borderRadius: 8,
        color: "#e2e8f0",
        fontFamily: "ui-monospace, monospace",
        fontSize: 12,
        padding: 10,
        whiteSpace: "pre-line",
      },
    }));
    const publicNodes = services.filter((s) => publicRoles.has(s.role));
    const privateNodes = services.filter((s) => !publicRoles.has(s.role));
    const edges: Edge[] = [];
    for (const pub of publicNodes) {
      for (const priv of privateNodes) {
        edges.push({
          id: `${pub.name}-${priv.name}`,
          source: pub.name,
          target: priv.name,
          style: { stroke: "#334155" },
        });
      }
    }
    return { nodes, edges };
  }, [services]);

  return (
    <div className="relative h-[420px] bg-slate-950 border border-slate-800 rounded-lg">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) =>
          setSelected(services.find((s) => s.name === node.id) ?? null)
        }
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e293b" gap={20} />
        <Controls />
        <MiniMap pannable zoomable style={{ background: "#0f172a" }} />
      </ReactFlow>
      <ServiceInspector service={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
