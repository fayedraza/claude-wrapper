import type { ReactNode } from "react";

import type { ContextGraphNode } from "@/lib/meta-planner-api";

interface AgentContextGraphProps {
  nodes: ContextGraphNode[] | null | undefined;
}

const SOURCE_LABELS: Record<ContextGraphNode["source"], string> = {
  mcp: "MCP",
  local_docs: "Local docs",
  codebase_file: "Codebase file",
  claude_context: "Claude context",
};

/** Plain-text source label for one node, e.g. "Codebase file: `path/to/file.py`"
 * (spec Tasks) -- monospace reserved for the literal `source_ref` only, never
 * the label text itself (DESIGN.md UX-DR2). Falls back to the raw `source`
 * string if it's ever a value outside `SOURCE_LABELS` (e.g. a schema/backend
 * drift), rather than rendering `undefined`. */
function sourceLabel(node: ContextGraphNode): ReactNode {
  const label = SOURCE_LABELS[node.source] ?? node.source;
  if (!node.source_ref) return label;
  return (
    <>
      {label}: <code className="font-mono text-[12px]">{node.source_ref}</code>
    </>
  );
}

/**
 * Story 2.2: one card per context-graph node -- topic, source, and neighbor
 * topics as small tags. No graph-rendering library and no drawn lines (no UX
 * mock exists for this screen yet) -- neighbors render as plain topic tags,
 * resolved by node_id against this same agent's own `nodes` list.
 */
export default function AgentContextGraph({ nodes: nodesProp }: AgentContextGraphProps) {
  const nodes = nodesProp ?? [];
  if (nodes.length === 0) {
    return <p className="text-small text-text2 dark:text-text2-dark">No context nodes for this agent.</p>;
  }

  const topicByNodeId = new Map(nodes.map((node) => [node.node_id, node.topic]));

  return (
    <div className="flex flex-col gap-space-2">
      {nodes.map((node) => (
        <div
          key={node.node_id}
          className="rounded-sm border border-black/10 bg-surface px-space-3 py-space-2 dark:border-white/10 dark:bg-surface-dark"
        >
          <p className="text-small font-bold text-text1 dark:text-text1-dark">{node.topic}</p>
          <p className="mt-space-1 text-label text-text2 dark:text-text2-dark">{sourceLabel(node)}</p>
          {node.neighbors.length > 0 && (
            <div className="mt-space-2 flex flex-wrap gap-space-1">
              {node.neighbors.map((neighborId) => (
                <span
                  key={neighborId}
                  className="rounded-full bg-black/5 px-space-2 py-[2px] text-label text-text2 dark:bg-white/10 dark:text-text2-dark"
                >
                  {topicByNodeId.get(neighborId) ?? neighborId}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
