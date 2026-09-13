"use client";

import { useState } from "react";

import type { AgentSpec } from "@/lib/meta-planner-api";
import AgentContextGraph from "./AgentContextGraph";

interface ProposedAgentListProps {
  agents: AgentSpec[];
}

/**
 * DESIGN.md "task-list-row", planned state (`key-task-list.html`
 * `.task-card.is-planned`): dashed border, no shadow, to visually distinguish
 * "not yet running" from a live run's solid, status-tinted cards. Per spec
 * Boundaries, this Story renders identity + one-line responsibility only --
 * no status badge (nothing has a status yet -- it hasn't run) and no
 * approve/reject affordance (that's Epic 3's Pre-Flight checklist).
 *
 * Story 2.2: clicking a card toggles an inline expansion showing that
 * agent's context graph (`AgentContextGraph`) -- no new route/drawer, no
 * drawn graph lines (no UX mock exists for this screen yet).
 */
export default function ProposedAgentList({ agents }: ProposedAgentListProps) {
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null);

  // A freshly submitted decompose result may reuse a node_id from the
  // previous result -- reset expansion so a new blueprint never appears to
  // auto-expand a card just because of a coincidental node_id match.
  // Adjusted during render (React's documented pattern for resetting state
  // when a prop changes) rather than in a useEffect, so it applies before
  // this render commits instead of triggering an extra one.
  const [prevAgents, setPrevAgents] = useState(agents);
  if (prevAgents !== agents) {
    setPrevAgents(agents);
    setExpandedNodeId(null);
  }

  if (agents.length === 0) {
    return <p className="text-small text-text2 dark:text-text2-dark">No agents proposed.</p>;
  }

  return (
    <div className="flex flex-col gap-space-3">
      {agents.map((agent) => {
        const expanded = expandedNodeId === agent.node_id;
        const panelId = `agent-context-graph-${agent.node_id}`;
        return (
          <div
            key={agent.node_id}
            role="button"
            tabIndex={0}
            aria-expanded={expanded}
            aria-controls={panelId}
            onClick={() => setExpandedNodeId(expanded ? null : agent.node_id)}
            onKeyDown={(event) => {
              if (event.key !== "Enter" && event.key !== " ") return;
              event.preventDefault();
              setExpandedNodeId(expanded ? null : agent.node_id);
            }}
            className="cursor-pointer rounded-md border-[1.5px] border-dashed border-black/15 bg-surface px-space-4 py-space-3 shadow-none dark:border-white/20 dark:bg-surface-dark"
          >
            <div className="flex flex-wrap items-baseline gap-space-2">
              <span aria-hidden="true" className="text-small text-text2 dark:text-text2-dark">
                {expanded ? "▾" : "▸"}
              </span>
              <span className="font-mono text-[13px] font-bold text-text1 dark:text-text1-dark">{agent.node_id}</span>
              <span className="text-label uppercase tracking-wide text-text2 dark:text-text2-dark">
                {agent.parent_id === null ? "Orchestrator" : `Reports to ${agent.parent_id}`}
              </span>
            </div>
            <p className="mt-space-1 text-small leading-relaxed text-text1 dark:text-text1-dark">
              {agent.responsibility}
            </p>
            {expanded && (
              <div
                id={panelId}
                className="mt-space-3 border-t border-black/10 pt-space-3 dark:border-white/10"
                onClick={(event) => event.stopPropagation()}
              >
                <AgentContextGraph nodes={agent.nodes} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
