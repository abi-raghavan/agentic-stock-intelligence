import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Agentic Stock Intelligence",
  description: "Evidence-backed multi-agent stock intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-white/10 bg-black/20 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              Agentic Stock Intelligence
            </Link>
            <nav className="flex gap-4 text-sm text-[var(--muted)]">
              <Link href="/" className="hover:text-white">
                Analyze
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 pb-8 text-xs text-[var(--muted)]">
          Not financial advice. Intelligence and risk analysis only — not price prediction.
        </footer>
      </body>
    </html>
  );
}
