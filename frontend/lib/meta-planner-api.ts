/**
 * Client for the Meta-Planner backend (Story 2.1).
 *
 * Mirrors `backend/brain/meta_planner/models.py` exactly -- these types are
 * the wire contract, not independently designed. Reuses `readErrorMessage`
 * from `settings-api.ts` rather than redefining the error-envelope parsing
 * logic (same precedent `permission-grants-api.ts` follows).
 */

import { readErrorMessage } from "@/lib/settings-api";

/** A subtopic node in an agent's context graph (Story 2.2). Execution/
 * telemetry fields (`status`, `telemetry`, `live_stream`, `checkpoint_ref`)
 * are pre-provisioned per AD-2 but always null from the Meta-Planner --
 * the Engine is the sole writer of those, once a run actually executes.
 *
 * Named `ContextGraphNode` (not `Node`) to avoid shadowing the DOM's global
 * `Node` type -- this does not rename the Python `Node` Pydantic model,
 * which has no such collision. */
export interface ContextGraphNode {
  node_id: string;
  topic: string;
  source: "mcp" | "local_docs" | "codebase_file" | "claude_context";
  source_ref: string | null;
  neighbors: string[];
  /** LLM-proposed (Story 2.3): whether this agent actually needs this node
   * (vs. merely supplementary). Used as-is -- unlike `flight_path` below,
   * never overwritten server-side. */
  required: boolean;
  status: string | null;
  telemetry: Record<string, unknown> | null;
  live_stream: Record<string, unknown> | null;
  checkpoint_ref: string | null;
}

export interface AgentSpec {
  node_id: string;
  parent_id: string | null;
  responsibility: string;
  depends_on: string[];
  nodes: ContextGraphNode[];
  /** Story 2.3, always server-computed: ordered node_ids of this agent's
   * `required` nodes only. */
  flight_path: string[];
  /** Story 2.3, always server-computed: total token-cost estimate across
   * `flight_path`. */
  estimated_tokens: number;
  /** Story 2.3, always server-computed: total duration estimate (seconds)
   * across `flight_path`. */
  estimated_duration_seconds: number;
  /** Story 2.3, always server-computed: dollar-cost estimate for
   * `estimated_tokens`, at a placeholder fixed rate (no per-agent model is
   * pinned yet). */
  estimated_cost_usd: number;
}

export interface DagBlueprint {
  intent: string;
  agents: AgentSpec[];
  /** Story 2.3, always server-computed: sum of every agent's own `estimated_tokens`. */
  aggregate_estimated_tokens: number;
  /** Story 2.3, always server-computed: sum of every agent's own `estimated_duration_seconds`. */
  aggregate_estimated_duration_seconds: number;
  /** Story 2.3, always server-computed: sum of every agent's own `estimated_cost_usd`. */
  aggregate_estimated_cost_usd: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Decompose a submitted intent into a `DagBlueprint` preview. Read-only: nothing executes or persists. */
export async function decomposeTask(intent: string): Promise<DagBlueprint> {
  const response = await fetch(`${API_BASE_URL}/api/meta-planner/decompose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Decomposing the task failed (${response.status}).`));
  }

  return (await response.json()) as DagBlueprint;
}
