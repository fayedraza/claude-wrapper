/**
 * Client for the Permission Manager backend (FR-6 + the standing half of
 * FR-5 -- "future runs respect it automatically").
 *
 * Mirrors `backend/brain/settings_router/models.py`'s permission-grant
 * models and `backend/gateway/errors.py` exactly -- these types are the
 * wire contract, not independently designed. Grants persist only in
 * `.claude/settings.local.json`, never the team-shared `settings.json`.
 */

import { readErrorMessage } from "./settings-api";

export type PermissionGrantKind = "file" | "mcp";

export interface PermissionGrant {
  id: string;
  kind: PermissionGrantKind;
  target: string;
}

export interface PermissionGrantsList {
  grants: PermissionGrant[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** FR-6: list every grant currently persisted in `.claude/settings.local.json`. */
export async function listPermissionGrants(): Promise<PermissionGrantsList> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Loading permission grants failed (${response.status}).`));
  }

  return (await response.json()) as PermissionGrantsList;
}

/**
 * FR-6: add a grant anytime, no run required. Idempotent for an
 * already-granted `kind`+`target` pair -- the existing grant is returned,
 * not duplicated.
 */
export async function addPermissionGrant(kind: PermissionGrantKind, target: string): Promise<PermissionGrant> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, target }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Adding this grant failed (${response.status}).`));
  }

  return (await response.json()) as PermissionGrant;
}

/** FR-6: revoke one grant by id. */
export async function revokePermissionGrant(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Revoking this grant failed (${response.status}).`));
  }
}
