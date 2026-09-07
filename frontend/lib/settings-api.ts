/**
 * Client for the Settings Router backend (FR-1/FR-2).
 *
 * Mirrors `backend/brain/settings_router/models.py` and
 * `backend/gateway/errors.py` exactly -- these types are the wire contract,
 * not independently designed. The frontend never calls Claude directly; it
 * only ever talks to these two gateway endpoints.
 */

// The 8 PRD target_category values verbatim -- rendered as-is in the UI,
// never relabeled (spec Boundaries: "Category chip renders the literal
// target_category string").
export type TargetCategory =
  | "team_instructions"
  | "local_instructions"
  | "settings.json"
  | "settings.local.json"
  | "rule"
  | "skill"
  | "command"
  | "agent";

export type ActionKind = "create" | "update" | "revoke";

export interface SettingAction {
  target_category: TargetCategory;
  file_path: string;
  content: string;
  action: ActionKind;
}

export interface SettingsRouterOutput {
  user_summary: string;
  updates: SettingAction[];
}

export interface ErrorEnvelope {
  error_code: string;
  message: string;
  node_id: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as Partial<ErrorEnvelope>;
    return body.message ?? fallback;
  } catch {
    return fallback;
  }
}

/** FR-1: classify a natural-language request into proposed `.claude/` changes. Writes nothing. */
export async function proposeSettingsChange(request: string): Promise<SettingsRouterOutput> {
  const response = await fetch(`${API_BASE_URL}/api/settings/propose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Settings request failed (${response.status}).`));
  }

  return (await response.json()) as SettingsRouterOutput;
}

/** FR-2: write/update/revoke exactly one approved change. Call only after explicit user approval. */
export async function applySettingsChange(action: SettingAction): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/settings/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(action),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Applying the change failed (${response.status}).`));
  }
}
