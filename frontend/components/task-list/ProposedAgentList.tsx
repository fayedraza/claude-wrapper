"use client";

import type { AgentSpec } from "@/lib/meta-planner-api";

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
 */
export default function ProposedAgentList({ agents }: ProposedAgentListProps) {
  if (agents.length === 0) {
    return <p className="text-small text-text2 dark:text-text2-dark">No agents proposed.</p>;
  }

  return (
    <div className="flex flex-col gap-space-3">
      {agents.map((agent) => (
        <div
          key={agent.node_id}
          className="rounded-md border-[1.5px] border-dashed border-black/15 bg-surface px-space-4 py-space-3 shadow-none dark:border-white/20 dark:bg-surface-dark"
        >
          <div className="flex flex-wrap items-baseline gap-space-2">
            <span className="font-mono text-[13px] font-bold text-text1 dark:text-text1-dark">{agent.node_id}</span>
            <span className="text-label uppercase tracking-wide text-text2 dark:text-text2-dark">
              {agent.parent_id === null ? "Orchestrator" : `Reports to ${agent.parent_id}`}
            </span>
          </div>
          <p className="mt-space-1 text-small leading-relaxed text-text1 dark:text-text1-dark">
            {agent.responsibility}
          </p>
        </div>
      ))}
    </div>
  );
}
