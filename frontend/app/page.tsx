"use client";

import { useState } from "react";

import SettingsDrawer from "@/components/settings/SettingsDrawer";

/**
 * App shell (Story 1.2's first real frontend surface). A persistent header
 * with the Settings entry point -- Settings opens as a drawer/overlay, not
 * a route (DESIGN.md Layout & Spacing). The two-pane task-list/canvas
 * layout and everything else in DESIGN.md's live-run default belongs to
 * later Epic 1 stories.
 */
export default function Home() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="flex flex-1 flex-col bg-bg dark:bg-bg-dark">
      <header className="flex items-center justify-between border-b border-black/5 px-space-5 py-space-4 dark:border-white/10">
        <span className="flex items-center gap-space-2 text-body font-bold text-text1 dark:text-text1-dark">
          <span className="h-2 w-2 rounded-full bg-accent" aria-hidden />
          Claude Wrapper
        </span>
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="rounded-sm border border-black/10 bg-surface px-space-4 py-space-2 text-small font-semibold text-text1 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-surface-dark dark:text-text1-dark dark:hover:bg-bg-dark"
        >
          Settings
        </button>
      </header>

      <main className="flex flex-1 items-center justify-center px-space-5 py-space-6">
        <p className="max-w-md text-center text-small text-text2 dark:text-text2-dark">
          Task list and run canvas land in a later story. Open Settings to submit a natural-language
          configuration request for <code className="font-mono">.claude/</code>.
        </p>
      </main>

      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
