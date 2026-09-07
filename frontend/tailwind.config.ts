import type { Config } from "tailwindcss";

// DESIGN.md tokens ("Flight Tracker" theme) wired into the Tailwind theme.
// Source: _bmad-output/planning-artifacts/ux-designs/ux-claude-wrapper-2026-08-30/DESIGN.md
// Loaded into Tailwind v4's CSS-first config via the `@config` directive in
// app/globals.css. Do not hand-roll these values elsewhere — reference the
// Tailwind classes generated from this file (e.g. `bg-bg`, `text-text1`,
// `rounded-md`, `p-space-4`) instead.
//
// The spacing scale uses a `space-` prefix (space-1..space-6) rather than
// bare numbers to avoid colliding with Tailwind's default numeric spacing
// scale (e.g. default `4`=16px vs DESIGN.md `4`=16px agree, but default
// `6`=24px vs DESIGN.md `6`=32px do not — bare numeric keys would silently
// override defaults out of step with DESIGN.md and invert the ordering).
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#FFF8F0",
        surface: "#FFFFFF",
        accent: "#2D9CDB",
        text1: "#1A1A2E",
        text2: "#6B6B7D",
        "status-waiting-input": "#F5A623",
        "status-executing": "#2D9CDB",
        "status-trouble": "#FF8C42",
        "status-completed": "#27AE60",
        "status-cancelled": "#9B9BAA",
        "status-failed": "#E74C3C",
        "bg-dark": "#1E1B2E",
        "surface-dark": "#2A2640",
        "accent-dark": "#5AB8F5",
        "text1-dark": "#F5F0FF",
        "text2-dark": "#B0A8C9",
        "status-waiting-input-dark": "#FFC15E",
        "status-executing-dark": "#5AB8F5",
        "status-trouble-dark": "#FF9A5C",
        "status-completed-dark": "#4ADE80",
        "status-cancelled-dark": "#8B84A8",
        "status-failed-dark": "#FF6B6B",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        label: "12px",
        small: "14px",
        body: "16px",
        "heading-sm": "20px",
        "heading-lg": "28px",
      },
      spacing: {
        "space-1": "4px",
        "space-2": "8px",
        "space-3": "12px",
        "space-4": "16px",
        "space-5": "24px",
        "space-6": "32px",
      },
      borderRadius: {
        sm: "8px",
        md: "16px",
        lg: "20px",
        full: "999px",
      },
    },
  },
} satisfies Config;
