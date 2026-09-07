"use client";

import type { ConfigSummaryItem as ConfigSummaryItemData } from "@/lib/settings-api";

interface ConfigSummaryItemProps {
  item: ConfigSummaryItemData;
}

// Mirrors mockups/key-settings.html's `.config-kind.*` chip colors -- a
// distinct, informal kind vocabulary (rule/agent/mcp) from ProposedChangeCard's
// target_category chip, per spec Boundaries: never conflate the two.
const KIND_CHIP_STYLES: Record<ConfigSummaryItemData["kind"], string> = {
  rule: "bg-[rgba(45,156,219,.14)] text-[#1D6FA0] dark:bg-[rgba(90,184,245,.18)] dark:text-[#5AB8F5]",
  agent: "bg-[rgba(39,174,96,.14)] text-[#1F7A45] dark:bg-[rgba(74,222,128,.18)] dark:text-[#4ADE80]",
  mcp: "bg-[rgba(155,155,170,.20)] text-[#5C5C6E] dark:bg-[rgba(176,168,201,.20)] dark:text-[#B0A8C9]",
};

/**
 * Read-only row for the "Currently configured" summary (FR-3): kind chip +
 * one-line text + file path. Unlike ProposedChangeCard, this has no actions
 * and no content preview -- it's purely informational.
 */
export default function ConfigSummaryItem({ item }: ConfigSummaryItemProps) {
  return (
    <div className="flex items-start gap-space-2 rounded-md border border-black/5 bg-bg px-space-3 py-space-2 dark:border-white/10 dark:bg-bg-dark">
      <span
        className={`mt-[1px] flex-shrink-0 whitespace-nowrap rounded-full px-space-2 py-[2px] text-label font-bold uppercase tracking-wide ${KIND_CHIP_STYLES[item.kind]}`}
      >
        {item.kind}
      </span>
      <div className="min-w-0">
        <div className="text-small leading-relaxed text-text1 dark:text-text1-dark">{item.text}</div>
        <div className="mt-[2px] truncate font-mono text-[11px] text-text2 dark:text-text2-dark">{item.path}</div>
      </div>
    </div>
  );
}
