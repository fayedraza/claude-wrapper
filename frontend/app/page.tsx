"use client";

import { useState } from "react";

import PermissionManagerDrawer from "@/components/permission-manager/PermissionManagerDrawer";
import SettingsDrawer from "@/components/settings/SettingsDrawer";
import ProposedAgentList from "@/components/task-list/ProposedAgentList";
import { decomposeTask, type DagBlueprint } from "@/lib/meta-planner-api";

type DecomposeState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "result"; blueprint: DagBlueprint };

/**
 * App shell (Story 1.2's first real frontend surface). A persistent header
 * with the Settings and Permissions entry points -- each opens as its own
 * drawer/overlay, not a route (DESIGN.md Layout & Spacing; UX-DR6: a
 * persistent header entry next to Settings). Story 2.1 replaces the
 * placeholder `<main>` with the Meta-Planner preview (EXPERIENCE.md "Task
 * List (planned)"): submit an intent, see the proposed agent breakdown --
 * read-only, nothing executes. The full two-pane task-list/canvas live-run
 * layout belongs to later Epic 2/3 stories.
 */
export default function Home() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [permissionsOpen, setPermissionsOpen] = useState(false);
  const [intent, setIntent] = useState("");
  const [decomposeState, setDecomposeState] = useState<DecomposeState>({ phase: "idle" });

  async function handleSubmit() {
    const trimmed = intent.trim();
    if (!trimmed) return;

    setDecomposeState({ phase: "loading" });
    try {
      const blueprint = await decomposeTask(trimmed);
      setDecomposeState({ phase: "result", blueprint });
    } catch (error) {
      setDecomposeState({
        phase: "error",
        message: error instanceof Error ? error.message : "Something went wrong.",
      });
    }
  }

  return (
    <div className="flex flex-1 flex-col bg-bg dark:bg-bg-dark">
      <header className="flex items-center justify-between border-b border-black/5 px-space-5 py-space-4 dark:border-white/10">
        <span className="flex items-center gap-space-2 text-body font-bold text-text1 dark:text-text1-dark">
          <span className="h-2 w-2 rounded-full bg-accent" aria-hidden />
          Claude Wrapper
        </span>
        <div className="flex items-center gap-space-2">
          <button
            type="button"
            onClick={() => {
              // Only one drawer at a time -- both are full-screen z-50
              // overlays with their own Escape/Tab keydown listeners, which
              // must never both be mounted together.
              setPermissionsOpen(true);
              setSettingsOpen(false);
            }}
            className="rounded-sm border border-black/10 bg-surface px-space-4 py-space-2 text-small font-semibold text-text1 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-surface-dark dark:text-text1-dark dark:hover:bg-bg-dark"
          >
            Permissions
          </button>
          <button
            type="button"
            onClick={() => {
              setSettingsOpen(true);
              setPermissionsOpen(false);
            }}
            className="rounded-sm border border-black/10 bg-surface px-space-4 py-space-2 text-small font-semibold text-text1 transition-colors hover:bg-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-surface-dark dark:text-text1-dark dark:hover:bg-bg-dark"
          >
            Settings
          </button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-space-5 py-space-6">
        <h1 className="text-heading-sm font-bold text-text1 dark:text-text1-dark">What do you want to get done?</h1>
        <p className="mt-space-2 text-small leading-relaxed text-text2 dark:text-text2-dark">
          Describe a task in plain language. Claude Wrapper decomposes it into a main orchestrator and
          subagents and shows you the breakdown before anything runs.
        </p>

        <label htmlFor="intent-textarea" className="sr-only">
          Describe the task you want to get done
        </label>
        <textarea
          id="intent-textarea"
          value={intent}
          onChange={(event) => setIntent(event.target.value)}
          rows={4}
          placeholder="e.g. add OAuth2 login to the app"
          className="mt-space-4 w-full rounded-md border-[1.5px] border-black/10 bg-bg px-space-3 py-space-3 font-sans text-small text-text1 focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text1-dark"
        />

        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={decomposeState.phase === "loading" || !intent.trim()}
          className="mt-space-3 self-start rounded-sm bg-accent px-space-4 py-space-2 text-small font-semibold text-white shadow-[0_2px_8px_rgba(45,156,219,.28)] transition-transform active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50"
        >
          {decomposeState.phase === "loading" ? "Decomposing…" : "Decompose task"}
        </button>

        {decomposeState.phase === "error" && (
          <p role="alert" className="mt-space-3 text-small text-status-failed dark:text-status-failed-dark">
            {decomposeState.message}
          </p>
        )}

        {decomposeState.phase === "result" && (
          <div className="mt-space-5">
            <p className="mb-space-2 text-label font-bold uppercase tracking-wide text-text2 dark:text-text2-dark">
              Proposed agents
            </p>
            <ProposedAgentList
              agents={decomposeState.blueprint.agents}
              aggregateEstimatedTokens={decomposeState.blueprint.aggregate_estimated_tokens}
              aggregateEstimatedDurationSeconds={decomposeState.blueprint.aggregate_estimated_duration_seconds}
              aggregateEstimatedCostUsd={decomposeState.blueprint.aggregate_estimated_cost_usd}
            />
          </div>
        )}

        {decomposeState.phase === "idle" && (
          <p className="mt-space-5 text-small text-text2 dark:text-text2-dark">
            Open Settings to submit a natural-language configuration request for{" "}
            <code className="font-mono">.claude/</code>, or open Permissions to view, add, or revoke
            permission grants.
          </p>
        )}
      </main>

      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <PermissionManagerDrawer open={permissionsOpen} onClose={() => setPermissionsOpen(false)} />
    </div>
  );
}
