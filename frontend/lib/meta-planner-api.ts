/**
 * Client for the Meta-Planner backend (Story 2.1).
 *
 * Mirrors `backend/brain/meta_planner/models.py` exactly -- these types are
 * the wire contract, not independently designed. Reuses `readErrorMessage`
 * from `settings-api.ts` rather than redefining the error-envelope parsing
 * logic (same precedent `permission-grants-api.ts` follows).
 */

import { readErrorMessage } from "@/lib/settings-api";

export interface AgentSpec {
  node_id: string;
  parent_id: string | null;
  responsibility: string;
  depends_on: string[];
}

export interface DagBlueprint {
  intent: string;
  agents: AgentSpec[];
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
