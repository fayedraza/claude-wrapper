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

// Story 1.3 (FR-3): the "Currently configured" chip vocabulary from the UX
// mock -- deliberately distinct, informal, and unrelated to TargetCategory
// above. Never conflate the two or render target_category in a summary row.
export type ConfigKind = "rule" | "agent" | "mcp";

export interface ConfigSummaryItem {
  kind: ConfigKind;
  text: string;
  path: string;
}

export interface CurrentConfiguration {
  items: ConfigSummaryItem[];
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

/** FR-3: read-only summary of what's already configured in `.claude/`. Never writes anything. */
export async function getCurrentConfiguration(): Promise<CurrentConfiguration> {
  const response = await fetch(`${API_BASE_URL}/api/settings/current`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Loading current configuration failed (${response.status}).`));
  }

  return (await response.json()) as CurrentConfiguration;
}
