import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Claude Wrapper",
  description: "AI agent orchestration and hand-off, replacing the terminal.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
