"use client";

import { KIND_CHIP_STYLES } from "@/components/settings/ConfigSummaryItem";
import type { GrantScope, PermissionGrant } from "@/lib/permission-grants-api";

interface PermissionGrantRowProps {
  grant: PermissionGrant;
  revoking: boolean;
  moving: boolean;
  onRevoke: () => void;
  onMove: (newScope: GrantScope) => void;
}

// Distinct from KIND_CHIP_STYLES -- this is a separate banner indicating
// *where* a grant lives (personal vs shared/committed file), not what kind
// of resource it grants. "team" reuses the same amber tone as the
// Settings drawer's "Proposal ready" badge, signaling a more consequential,
// shared/committed action.
const SCOPE_BADGE_STYLES: Record<GrantScope, string> = {
  local: "border-black/15 text-text2 dark:border-white/15 dark:text-text2-dark",
  team: "border-[rgba(245,166,35,.45)] text-[#92600C] dark:border-[rgba(245,166,35,.5)] dark:text-[#F5A623]",
};

const SCOPE_LABELS: Record<GrantScope, string> = {
  local: "Local",
  team: "Team",
};

const OTHER_SCOPE: Record<GrantScope, GrantScope> = {
  local: "team",
  team: "local",
};

/**
 * One row in the Permission Manager's grant list (FR-6): kind chip + scope
 * banner + target + Move/Revoke actions. Reuses ConfigSummaryItem's chip
 * color map so "file"/"mcp" render identically here and in Settings'
 * "Currently configured" summary. The scope banner distinguishes a
 * personal grant (`.claude/settings.local.json`) from a team one
 * (`.claude/settings.json`, usually committed) -- the same distinction the
 * grant's `path` carries in the Settings summary.
 */
export default function PermissionGrantRow({ grant, revoking, moving, onRevoke, onMove }: PermissionGrantRowProps) {
  const disabled = revoking || moving;

  return (
    <div className="flex items-center gap-space-2 rounded-md border border-black/5 bg-bg px-space-3 py-space-2 dark:border-white/10 dark:bg-bg-dark">
      <span
        className={`flex-shrink-0 whitespace-nowrap rounded-full px-space-2 py-[2px] text-label font-bold uppercase tracking-wide ${KIND_CHIP_STYLES[grant.kind]}`}
      >
        {grant.kind}
      </span>
      <span
        className={`flex-shrink-0 whitespace-nowrap rounded-full border px-space-2 py-[2px] text-label font-bold uppercase tracking-wide ${SCOPE_BADGE_STYLES[grant.scope]}`}
        title={grant.scope === "team" ? ".claude/settings.json (shared)" : ".claude/settings.local.json (personal)"}
      >
        {SCOPE_LABELS[grant.scope]}
      </span>
      <span
        title={grant.target}
        className="min-w-0 flex-1 truncate font-mono text-small text-text1 dark:text-text1-dark"
      >
        {grant.target}
      </span>
      <button
        type="button"
        onClick={() => onMove(OTHER_SCOPE[grant.scope])}
        disabled={disabled}
        className="flex-shrink-0 rounded-sm border border-black/10 bg-surface px-space-3 py-[4px] text-small font-semibold text-text2 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50 dark:border-white/10 dark:bg-surface-dark dark:text-text2-dark dark:hover:bg-bg-dark"
      >
        {moving ? "Moving…" : `Move to ${SCOPE_LABELS[OTHER_SCOPE[grant.scope]]}`}
      </button>
      <button
        type="button"
        onClick={onRevoke}
        disabled={disabled}
        className="flex-shrink-0 rounded-sm border border-black/10 bg-surface px-space-3 py-[4px] text-small font-semibold text-text2 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50 dark:border-white/10 dark:bg-surface-dark dark:text-text2-dark dark:hover:bg-bg-dark"
      >
        {revoking ? "Revoking…" : "Revoke"}
      </button>
    </div>
  );
}
