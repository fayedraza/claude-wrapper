"use client";

import type { SettingAction } from "@/lib/settings-api";

export type ProposedChangeStatus = "pending" | "applying" | "applied" | "error";

interface ProposedChangeCardProps {
  action: SettingAction;
  status: ProposedChangeStatus;
  errorMessage?: string;
  onApprove: () => void;
  onReject: () => void;
}

// Mirrors mockups/key-settings.html's `.proposal-badge.action-*` colors --
// deliberately a bespoke palette per action, not the six-color node-status
// vocabulary (DESIGN.md: never reuse a status color for something that
// isn't actually that status).
const ACTION_BADGE_STYLES: Record<SettingAction["action"], string> = {
  create: "bg-[rgba(39,174,96,.14)] text-[#1F7A45]",
  update: "bg-[rgba(245,166,35,.16)] text-[#92600C]",
  revoke: "bg-[rgba(231,76,60,.14)] text-[#A93226]",
};

/** UX-DR10: target path + category chip + action badge + content preview, gated behind Approve & Apply / Reject. */
export default function ProposedChangeCard({
  action,
  status,
  errorMessage,
  onApprove,
  onReject,
}: ProposedChangeCardProps) {
  const decided = status === "applied";
  const busy = status === "applying";

  return (
    <div className="overflow-hidden rounded-md border-[1.5px] border-accent/35 bg-surface shadow-[0_2px_8px_rgba(0,0,0,.05)] dark:bg-surface-dark">
      <div className="flex flex-wrap items-center gap-space-2 border-b border-black/5 bg-accent/5 px-space-4 py-space-3 dark:border-white/10">
        <span className="font-mono text-[12.5px] font-semibold text-text1 dark:text-text1-dark">
          {action.file_path}
        </span>
        <span className="rounded-full bg-[rgba(45,156,219,.14)] px-space-2 py-[2px] text-label font-bold uppercase tracking-wide text-[#1D6FA0]">
          {action.target_category}
        </span>
        <span
          className={`rounded-full px-space-2 py-[2px] text-label font-bold uppercase tracking-wide ${ACTION_BADGE_STYLES[action.action]}`}
        >
          {action.action}
        </span>
      </div>

      <div className="px-space-4 py-space-3">
        {action.action === "revoke" ? (
          <p className="text-small italic leading-relaxed text-text2 dark:text-text2-dark">
            This file will be removed.
          </p>
        ) : (
          <div className="rounded-sm border border-l-[3px] border-black/5 border-l-accent bg-bg px-space-3 py-space-2 text-small italic leading-relaxed whitespace-pre-wrap text-text1 dark:bg-bg-dark dark:text-text1-dark">
            {action.content}
          </div>
        )}

        {status === "error" && errorMessage && (
          <p role="alert" className="mt-space-2 text-small text-status-failed dark:text-status-failed-dark">
            {errorMessage}
          </p>
        )}

        {decided ? (
          <p className="mt-space-3 text-small font-semibold text-status-completed dark:text-status-completed-dark">
            Applied
          </p>
        ) : (
          <div className="mt-space-4 flex gap-space-2">
            <button
              type="button"
              onClick={onReject}
              disabled={busy}
              className="flex-1 rounded-sm border border-black/10 bg-surface px-space-4 py-space-2 text-small font-semibold text-text2 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50 dark:border-white/10 dark:bg-surface-dark dark:text-text2-dark dark:hover:bg-bg-dark"
            >
              Reject
            </button>
            <button
              type="button"
              onClick={onApprove}
              disabled={busy}
              className="flex-1 rounded-sm bg-accent px-space-4 py-space-2 text-small font-semibold text-white shadow-[0_2px_8px_rgba(45,156,219,.28)] transition-transform active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50"
            >
              {busy ? "Applying…" : "Approve & Apply"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
