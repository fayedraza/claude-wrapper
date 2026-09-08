"use client";

import { useEffect, useRef, useState } from "react";

import {
  addPermissionGrant,
  listPermissionGrants,
  revokePermissionGrant,
  updatePermissionGrant,
  type GrantScope,
  type PermissionGrant,
  type PermissionGrantKind,
} from "@/lib/permission-grants-api";
import PermissionGrantRow from "./PermissionGrantRow";

type GrantsState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "loaded"; grants: PermissionGrant[] };

interface PermissionManagerDrawerProps {
  open: boolean;
  onClose: () => void;
}

const DIALOG_HEADING_ID = "permission-manager-drawer-heading";
const FOCUSABLE_SELECTOR = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Permission Manager drawer (FR-6 + the standing half of FR-5): view, add,
 * move, and revoke permission grants -- across both `local`
 * (`.claude/settings.local.json`, personal) and `team`
 * (`.claude/settings.json`, shared, usually committed) scope. A new
 * persistent header entry next to Settings (UX-DR6) -- its own drawer +
 * component tree, reusing only Settings drawer's dialog chrome (backdrop,
 * dialog role, focus trap, Escape-to-close), never its propose/approve
 * flow.
 */
export default function PermissionManagerDrawer({ open, onClose }: PermissionManagerDrawerProps) {
  const [grantsState, setGrantsState] = useState<GrantsState>({ phase: "idle" });
  const [kind, setKind] = useState<PermissionGrantKind>("file");
  const [scope, setScope] = useState<GrantScope>("local");
  const [target, setTarget] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Sets, not single ids -- acting on a second grant while an earlier
  // action is still in flight must not make the earlier row lose its own
  // disabled/label state.
  const [revokingIds, setRevokingIds] = useState<Set<string>>(new Set());
  const [revokeError, setRevokeError] = useState<string | null>(null);
  const [movingIds, setMovingIds] = useState<Set<string>>(new Set());
  const [moveError, setMoveError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);
  // Guards against out-of-order responses, same reasoning as SettingsDrawer's
  // currentConfigRequestIdRef: only the response matching the latest call's
  // token is allowed to write state.
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
      const frame = window.requestAnimationFrame(() => {
        dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)?.focus();
      });
      return () => window.cancelAnimationFrame(frame);
    }
    previouslyFocusedRef.current?.focus();
    previouslyFocusedRef.current = null;
  }, [open]);

  useEffect(() => {
    if (!open) return;
    void loadGrants();
  }, [open]);

  if (!open) return null;

  async function loadGrants() {
    const requestId = ++requestIdRef.current;
    // Only blank the list to "Loading…" for the first fetch -- a refresh
    // after revoke/move keeps the previous rows visible instead of
    // flashing empty.
    setGrantsState((prev) => (prev.phase === "loaded" ? prev : { phase: "loading" }));
    try {
      const result = await listPermissionGrants();
      if (requestId !== requestIdRef.current) return; // a newer request already landed
      setGrantsState({ phase: "loaded", grants: result.grants });
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      setGrantsState({
        phase: "error",
        message: error instanceof Error ? error.message : "Failed to load permission grants.",
      });
    }
  }

  async function handleAddGrant() {
    const trimmed = target.trim();
    if (!trimmed) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const grant = await addPermissionGrant(kind, trimmed, scope);
      setTarget("");
      if (grantsState.phase !== "loaded") {
        // No reliable prior list to append to (e.g. the initial fetch
        // errored) -- refetch instead of fabricating a single-item list,
        // which would hide any other grants that actually exist.
        void loadGrants();
      } else {
        setGrantsState((prev) => {
          if (prev.phase !== "loaded") return prev;
          // Add is idempotent within a scope (spec) -- the backend can
          // return an already-existing grant rather than a new one; don't
          // duplicate it.
          if (prev.grants.some((existing) => existing.id === grant.id)) return prev;
          return { phase: "loaded", grants: [...prev.grants, grant] };
        });
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Failed to add this grant.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRevoke(id: string) {
    setRevokingIds((prev) => new Set(prev).add(id));
    setRevokeError(null);
    try {
      await revokePermissionGrant(id);
      setGrantsState((prev) =>
        prev.phase === "loaded" ? { phase: "loaded", grants: prev.grants.filter((g) => g.id !== id) } : prev
      );
    } catch (error) {
      setRevokeError(error instanceof Error ? error.message : "Failed to revoke this grant.");
      // I/O matrix: "Revoke unknown/already-revoked id -- error shown, list re-fetches."
      void loadGrants();
    } finally {
      setRevokingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  async function handleMove(id: string, newScope: GrantScope) {
    setMovingIds((prev) => new Set(prev).add(id));
    setMoveError(null);
    try {
      const updated = await updatePermissionGrant(id, { scope: newScope });
      setGrantsState((prev) => {
        if (prev.phase !== "loaded") return prev;
        // Moving to a scope that already has an identical grant merges
        // into it server-side (same idempotency rule as add) -- the
        // response's id may differ from the one we moved. Drop both the
        // moved-from row and any existing row for the merged-into id, then
        // add the single resulting row back.
        const withoutStale = prev.grants.filter((g) => g.id !== id && g.id !== updated.id);
        return { phase: "loaded", grants: [...withoutStale, updated] };
      });
    } catch (error) {
      setMoveError(error instanceof Error ? error.message : "Failed to move this grant.");
      void loadGrants();
    } finally {
      setMovingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close permissions"
        onClick={onClose}
        className="absolute inset-0 bg-text1/28 dark:bg-black/50"
      />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={DIALOG_HEADING_ID}
        className="relative flex h-full w-full max-w-[520px] flex-col border-l border-black/5 bg-surface shadow-[0_6px_24px_rgba(45,156,219,.10),-8px_0_32px_rgba(26,26,46,.14)] dark:border-white/10 dark:bg-surface-dark"
      >
        <div className="border-b border-black/5 px-space-5 py-space-5 dark:border-white/10">
          <div className="flex items-start justify-between gap-space-3">
            <div>
              <h1 id={DIALOG_HEADING_ID} className="text-heading-sm font-bold text-text1 dark:text-text1-dark">
                Permissions
              </h1>
              <p className="text-small text-text2 dark:text-text2-dark">Files &amp; MCP servers granted access</p>
            </div>
            <button
              type="button"
              aria-label="Close permissions"
              onClick={onClose}
              className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-sm border border-black/10 bg-bg text-text2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text2-dark"
            >
              &times;
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-space-5 py-space-5">
          <p className="mb-space-2 text-label font-bold uppercase tracking-wide text-text2 dark:text-text2-dark">
            Add a grant
          </p>
          <p className="mb-space-3 text-small leading-relaxed text-text2 dark:text-text2-dark">
            Grant Claude Wrapper standing access to a file or an MCP server. This applies to future runs
            automatically — no run required.
          </p>

          <div className="flex gap-space-2">
            <select
              value={kind}
              onChange={(event) => setKind(event.target.value as PermissionGrantKind)}
              aria-label="Grant kind"
              className="rounded-md border-[1.5px] border-black/10 bg-bg px-space-3 py-space-2 text-small text-text1 focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text1-dark"
            >
              <option value="file">File</option>
              <option value="mcp">MCP server</option>
            </select>
            <input
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !submitting) void handleAddGrant();
              }}
              placeholder={kind === "file" ? "e.g. src/config/secrets.json" : "e.g. filesystem-mcp"}
              aria-label="Grant target"
              className="min-w-0 flex-1 rounded-md border-[1.5px] border-black/10 bg-bg px-space-3 py-space-2 text-small text-text1 focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text1-dark"
            />
          </div>

          <div className="mt-space-2 flex items-center gap-space-2">
            <select
              value={scope}
              onChange={(event) => setScope(event.target.value as GrantScope)}
              aria-label="Save to"
              className="rounded-md border-[1.5px] border-black/10 bg-bg px-space-3 py-space-2 text-small text-text1 focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text1-dark"
            >
              <option value="local">Personal (not shared)</option>
              <option value="team">Team (shared)</option>
            </select>
            <p className="text-label leading-relaxed text-text2 dark:text-text2-dark">
              {scope === "team"
                ? "Saved to .claude/settings.json — shared with everyone on this project."
                : "Saved to .claude/settings.local.json — stays on this machine."}
            </p>
          </div>

          <button
            type="button"
            onClick={handleAddGrant}
            disabled={submitting || !target.trim()}
            className="mt-space-3 rounded-sm bg-accent px-space-4 py-space-2 text-small font-semibold text-white shadow-[0_2px_8px_rgba(45,156,219,.28)] transition-transform active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50"
          >
            {submitting ? "Adding…" : "Add grant"}
          </button>

          {submitError && (
            <p role="alert" className="mt-space-3 text-small text-status-failed dark:text-status-failed-dark">
              {submitError}
            </p>
          )}

          <div className="mt-space-6 border-t border-black/5 pt-space-5 dark:border-white/10">
            <p className="mb-space-2 text-label font-bold uppercase tracking-wide text-text2 dark:text-text2-dark">
              Granted
            </p>

            {revokeError && (
              <p role="alert" className="mb-space-2 text-small text-status-failed dark:text-status-failed-dark">
                {revokeError}
              </p>
            )}

            {moveError && (
              <p role="alert" className="mb-space-2 text-small text-status-failed dark:text-status-failed-dark">
                {moveError}
              </p>
            )}

            {grantsState.phase === "loading" && (
              <p className="text-small text-text2 dark:text-text2-dark">Loading…</p>
            )}

            {grantsState.phase === "error" && (
              <p role="alert" className="text-small text-status-failed dark:text-status-failed-dark">
                {grantsState.message}
              </p>
            )}

            {grantsState.phase === "loaded" && grantsState.grants.length === 0 && (
              <p className="text-small leading-relaxed text-text2 dark:text-text2-dark">
                No permission grants yet — add a file or MCP server above to grant it standing access.
              </p>
            )}

            {grantsState.phase === "loaded" && grantsState.grants.length > 0 && (
              <div className="flex flex-col gap-space-2">
                {grantsState.grants.map((grant) => (
                  <PermissionGrantRow
                    key={grant.id}
                    grant={grant}
                    revoking={revokingIds.has(grant.id)}
                    moving={movingIds.has(grant.id)}
                    onRevoke={() => handleRevoke(grant.id)}
                    onMove={(newScope) => handleMove(grant.id, newScope)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
