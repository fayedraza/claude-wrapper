"use client";

import { KIND_CHIP_STYLES } from "@/components/settings/ConfigSummaryItem";
import type { PermissionGrant } from "@/lib/permission-grants-api";

interface PermissionGrantRowProps {
  grant: PermissionGrant;
  revoking: boolean;
  onRevoke: () => void;
}

/**
 * One row in the Permission Manager's grant list (FR-6): kind chip + target
 * + Revoke button. Reuses ConfigSummaryItem's chip color map so "file"/"mcp"
 * render identically here and in Settings' "Currently configured" summary.
 */
export default function PermissionGrantRow({ grant, revoking, onRevoke }: PermissionGrantRowProps) {
  return (
    <div className="flex items-center gap-space-2 rounded-md border border-black/5 bg-bg px-space-3 py-space-2 dark:border-white/10 dark:bg-bg-dark">
      <span
        className={`flex-shrink-0 whitespace-nowrap rounded-full px-space-2 py-[2px] text-label font-bold uppercase tracking-wide ${KIND_CHIP_STYLES[grant.kind]}`}
      >
        {grant.kind}
      </span>
      <span
        title={grant.target}
        className="min-w-0 flex-1 truncate font-mono text-small text-text1 dark:text-text1-dark"
      >
        {grant.target}
      </span>
      <button
        type="button"
        onClick={onRevoke}
        disabled={revoking}
        className="flex-shrink-0 rounded-sm border border-black/10 bg-surface px-space-3 py-[4px] text-small font-semibold text-text2 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50 dark:border-white/10 dark:bg-surface-dark dark:text-text2-dark dark:hover:bg-bg-dark"
      >
        {revoking ? "Revoking…" : "Revoke"}
      </button>
    </div>
  );
}
