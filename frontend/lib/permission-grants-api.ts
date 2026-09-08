/**
 * Client for the Permission Manager backend (FR-6 + the standing half of
 * FR-5 -- "future runs respect it automatically").
 *
 * Mirrors `backend/brain/settings_router/models.py`'s permission-grant
 * models and `backend/gateway/errors.py` exactly -- these types are the
 * wire contract, not independently designed. Grants persist in one of two
 * files, chosen by `scope`: `"local"` (personal, `.claude/settings.local.json`,
 * not committed) or `"team"` (shared, `.claude/settings.json`, usually
 * committed).
 */

import { readErrorMessage } from "./settings-api";

export type PermissionGrantKind = "file" | "mcp";

// Which settings file a grant lives in -- see module docstring.
export type GrantScope = "local" | "team";

export interface PermissionGrant {
  id: string;
  kind: PermissionGrantKind;
  target: string;
  scope: GrantScope;
}

export interface PermissionGrantsList {
  grants: PermissionGrant[];
}

export interface UpdatePermissionGrantFields {
  kind?: PermissionGrantKind;
  target?: string;
  scope?: GrantScope;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** FR-6: list every grant currently persisted, across both local and team scope. */
export async function listPermissionGrants(): Promise<PermissionGrantsList> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Loading permission grants failed (${response.status}).`));
  }

  return (await response.json()) as PermissionGrantsList;
}

/**
 * FR-6: add a grant anytime, no run required, to whichever scope (`local`
 * by default). Idempotent for an already-granted `kind`+`target` pair
 * within that same scope -- the existing grant is returned, not
 * duplicated.
 */
export async function addPermissionGrant(
  kind: PermissionGrantKind,
  target: string,
  scope: GrantScope = "local"
): Promise<PermissionGrant> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, target, scope }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Adding this grant failed (${response.status}).`));
  }

  return (await response.json()) as PermissionGrant;
}

/**
 * Edit an existing grant's kind/target, and/or move it between `local` and
 * `team` scope -- regardless of which file it currently lives in. Only the
 * provided fields change.
 */
export async function updatePermissionGrant(
  id: string,
  fields: UpdatePermissionGrantFields
): Promise<PermissionGrant> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Updating this grant failed (${response.status}).`));
  }

  return (await response.json()) as PermissionGrant;
}

/** FR-6: revoke one grant by id, regardless of which scope it's in. */
export async function revokePermissionGrant(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/permission-grants/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, `Revoking this grant failed (${response.status}).`));
  }
}
