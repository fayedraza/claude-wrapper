"use client";

import { useState } from "react";

import type { AgentSpec } from "@/lib/meta-planner-api";
import AgentContextGraph from "./AgentContextGraph";

interface ProposedAgentListProps {
  agents: AgentSpec[];
  /** Story 2.3, `DagBlueprint.aggregate_estimated_tokens` -- sum of every
   * agent's own `estimated_tokens`, rendered once above the list. */
  aggregateEstimatedTokens: number;
  /** Story 2.3, `DagBlueprint.aggregate_estimated_duration_seconds`. */
  aggregateEstimatedDurationSeconds: number;
  /** Story 2.3, `DagBlueprint.aggregate_estimated_cost_usd`. */
  aggregateEstimatedCostUsd: number;
}

/** Whole seconds/minutes, e.g. "3s" or "2m 5s" -- no fractional seconds
 * (Story 2.3's `estimated_duration_seconds` is a float estimate, not a
 * precise measurement, so sub-second precision would be misleading). */
function formatDuration(seconds: number): string {
  const rounded = Math.round(seconds);
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = rounded % 60;
  if (minutes === 0) return `${remainingSeconds}s`;
  return `${minutes}m ${remainingSeconds}s`;
}

/** e.g. "12,000 tokens" -- grouped for readability, since these are
 * potentially large aggregate sums. */
function formatTokens(tokens: number): string {
  return `${tokens.toLocaleString()} token${tokens === 1 ? "" : "s"}`;
}

/** e.g. "$0.02" or "$0.0006" for a sub-cent estimate -- a raw token count
 * alone can read as alarming to a non-technical viewer with no price
 * anchor, so this renders alongside it wherever tokens are shown. Below one
 * cent, two decimal places would silently round to "$0.00" and look like a
 * free run, so those switch to four decimal places instead. */
function formatCost(usd: number): string {
  if (usd > 0 && usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
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
 *
 * Story 2.3: each agent's server-computed token/duration/cost estimate
 * renders as a line on its (collapsed) card -- visible without expanding,
 * per AC #2 -- and one aggregate total renders above the whole list (AC
 * #3). All three are read directly off `AgentSpec`/`DagBlueprint`'s
 * server-computed fields, never recomputed client-side. The dollar-cost
 * figure is a placeholder-rate estimate (no per-agent model is pinned yet)
 * shown alongside the token count so it doesn't read as an unanchored,
 * alarming number on its own.
 */
export default function ProposedAgentList({
  agents,
  aggregateEstimatedTokens,
  aggregateEstimatedDurationSeconds,
  aggregateEstimatedCostUsd,
}: ProposedAgentListProps) {
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
      <p className="text-small text-text2 dark:text-text2-dark">
        Aggregate estimate:{" "}
        <span className="font-bold text-text1 dark:text-text1-dark">
          {formatTokens(aggregateEstimatedTokens ?? 0)}
        </span>
        {" · "}
        <span className="font-bold text-text1 dark:text-text1-dark">
          {formatDuration(aggregateEstimatedDurationSeconds ?? 0)}
        </span>
        {" · "}
        <span className="font-bold text-text1 dark:text-text1-dark">
          {formatCost(aggregateEstimatedCostUsd ?? 0)}
        </span>
      </p>
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
            <p className="mt-space-1 text-label text-text2 dark:text-text2-dark">
              {formatTokens(agent.estimated_tokens ?? 0)} ·{" "}
              {formatDuration(agent.estimated_duration_seconds ?? 0)} ·{" "}
              {formatCost(agent.estimated_cost_usd ?? 0)}
            </p>
            {expanded && (
              <div
                id={panelId}
                className="mt-space-3 border-t border-black/10 pt-space-3 dark:border-white/10"
                onClick={(event) => event.stopPropagation()}
              >
                <AgentContextGraph nodes={agent.nodes} flightPath={agent.flight_path} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
