import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meeting Reality Engine",
  description:
    "Transform meeting recordings into structured, verifiable intelligence.",
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  themeColor: "#0A0A0C",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="antialiased">
        {/* App shell — single-page, no nav needed yet */}
        <div className="min-h-dvh flex flex-col bg-[var(--bg)]">
          {/* Top bar */}
          <header className="h-12 flex items-center px-6 border-b border-[var(--border)] shrink-0">
            <span className="font-display text-sm font-medium tracking-[-0.01em] text-[var(--text-primary)]">
              meeting-reality
            </span>
            <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-[var(--surface)] text-[var(--text-secondary)] border border-[var(--border)]">
              alpha
            </span>
          </header>

          {/* Main content area — grows to fill viewport */}
          <main className="flex-1 flex flex-col">{children}</main>

          {/* Footer */}
          <footer className="h-8 flex items-center justify-center px-6 border-t border-[var(--border)] shrink-0">
            <span className="text-[10px] text-[var(--text-disabled)] font-mono">
              v0.1.0-alpha
            </span>
          </footer>
        </div>
      </body>
    </html>
  );
}
