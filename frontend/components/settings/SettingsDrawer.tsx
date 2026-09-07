"use client";

import { useEffect, useRef, useState } from "react";

import { applySettingsChange, proposeSettingsChange, type SettingAction } from "@/lib/settings-api";
import ProposedChangeCard, { type ProposedChangeStatus } from "./ProposedChangeCard";

interface CardState {
  id: string;
  action: SettingAction;
  status: ProposedChangeStatus;
  errorMessage?: string;
}

type RequestState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "result"; userSummary: string };

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
}

const DIALOG_HEADING_ID = "settings-drawer-heading";
const FOCUSABLE_SELECTOR = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** Settings drawer (FR-1/FR-2): natural-language request box + proposed-change card list + approval gate. */
export default function SettingsDrawer({ open, onClose }: SettingsDrawerProps) {
  const [requestText, setRequestText] = useState("");
  const [requestState, setRequestState] = useState<RequestState>({ phase: "idle" });
  const [cards, setCards] = useState<CardState[]>([]);

  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  // Docked slide-over drawer over a dimmed backdrop (DESIGN.md) -- Escape closes it (matching the
  // rest of the drawer family) and Tab is trapped inside the dialog while it's open.
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

  // Move focus into the dialog on open, and restore it to whatever triggered
  // the drawer on close (accessibility floor: full keyboard navigation).
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

  if (!open) return null;

  async function handleSubmit() {
    const trimmed = requestText.trim();
    if (!trimmed) return;

    setRequestState({ phase: "loading" });
    setCards([]);
    try {
      const output = await proposeSettingsChange(trimmed);
      setRequestState({ phase: "result", userSummary: output.user_summary });
      setCards(
        output.updates.map((action) => ({
          id: crypto.randomUUID(),
          action,
          status: "pending",
        }))
      );
    } catch (error) {
      setRequestState({ phase: "error", message: error instanceof Error ? error.message : "Something went wrong." });
    }
  }

  // Cards are identified by a stable id, not array position -- rejecting one card
  // shrinks the array, and an approve already in flight for a different card must
  // still land on the right element when its promise resolves.
  function updateCard(id: string, patch: Partial<CardState>) {
    setCards((prev) => prev.map((card) => (card.id === id ? { ...card, ...patch } : card)));
  }

  function handleReject(id: string) {
    // FR-2: rejecting touches no files -- there is no backend call at all, the card is just discarded.
    setCards((prev) => prev.filter((card) => card.id !== id));
  }

  async function handleApprove(id: string) {
    const card = cards.find((c) => c.id === id);
    if (!card) return;

    updateCard(id, { status: "applying", errorMessage: undefined });
    try {
      await applySettingsChange(card.action);
      updateCard(id, { status: "applied" });
    } catch (error) {
      updateCard(id, {
        status: "error",
        errorMessage: error instanceof Error ? error.message : "Failed to apply this change.",
      });
    }
  }

  const hasSubmittedAnything = requestState.phase !== "idle";
  const showEmptyState = requestState.phase === "result" && cards.length === 0;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close settings"
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
                Settings
              </h1>
              <p className="text-small text-text2 dark:text-text2-dark">Project rules &amp; configuration</p>
            </div>
            <button
              type="button"
              aria-label="Close settings"
              onClick={onClose}
              className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-sm border border-black/10 bg-bg text-text2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text2-dark"
            >
              &times;
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-space-5 py-space-5">
          <p className="mb-space-2 text-label font-bold uppercase tracking-wide text-text2 dark:text-text2-dark">
            Add a rule or preference
          </p>
          <p className="mb-space-3 text-small leading-relaxed text-text2 dark:text-text2-dark">
            Describe it in plain language. Claude Wrapper figures out which{" "}
            <code className="rounded-[5px] bg-accent/10 px-[5px] py-[1px] font-mono text-[0.93em] text-text1 dark:text-text1-dark">
              .claude/
            </code>{" "}
            file it belongs in and shows you the exact change before writing anything.
          </p>

          <textarea
            value={requestText}
            onChange={(event) => setRequestText(event.target.value)}
            rows={3}
            placeholder="e.g. always use pytest, never commit .env files"
            className="w-full rounded-md border-[1.5px] border-black/10 bg-bg px-space-3 py-space-3 font-sans text-small text-text1 focus-visible:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 dark:border-white/10 dark:bg-bg-dark dark:text-text1-dark"
          />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={requestState.phase === "loading" || !requestText.trim()}
            className="mt-space-3 rounded-sm bg-accent px-space-4 py-space-2 text-small font-semibold text-white shadow-[0_2px_8px_rgba(45,156,219,.28)] transition-transform active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:opacity-50"
          >
            {requestState.phase === "loading" ? "Thinking…" : "Submit request"}
          </button>

          {requestState.phase === "error" && (
            <p role="alert" className="mt-space-3 text-small text-status-failed dark:text-status-failed-dark">
              {requestState.message}
            </p>
          )}

          {requestState.phase === "result" && cards.length > 0 && (
            <span className="mt-space-4 inline-flex items-center gap-space-2 rounded-full border border-[rgba(245,166,35,.40)] bg-[rgba(245,166,35,.15)] px-space-3 py-[4px] text-label font-bold text-[#92600C]">
              <span className="h-[7px] w-[7px] rounded-full bg-[#F5A623]" />
              Proposal ready — not yet applied
            </span>
          )}

          {requestState.phase === "result" && (
            <p className="mt-space-3 text-small leading-relaxed text-text1 dark:text-text1-dark">
              {requestState.userSummary}
            </p>
          )}

          {showEmptyState && (
            <p className="mt-space-2 text-small leading-relaxed text-text2 dark:text-text2-dark">
              Nothing to change — try describing a specific rule, permission, or persona.
            </p>
          )}

          {cards.length > 0 && (
            <div className="mt-space-4 flex flex-col gap-space-3">
              {cards.map((card) => (
                <ProposedChangeCard
                  key={card.id}
                  action={card.action}
                  status={card.status}
                  errorMessage={card.errorMessage}
                  onApprove={() => handleApprove(card.id)}
                  onReject={() => handleReject(card.id)}
                />
              ))}
            </div>
          )}

          {!hasSubmittedAnything && (
            <p className="mt-space-5 text-small text-text2 dark:text-text2-dark">
              Nothing submitted yet — describe a rule or preference above to get started.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
