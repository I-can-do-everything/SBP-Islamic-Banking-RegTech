import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router";
import { PersonSwitcher } from "./PersonSwitcher";

function useTheme() {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem("daleel.theme");
      if (saved) return saved === "dark";
    } catch {
      /* storage blocked */
    }
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("daleel.theme", dark ? "dark" : "light");
    } catch {
      /* storage blocked */
    }
  }, [dark]);
  return [dark, setDark] as const;
}

/** The mark: an eight point star (a common motif in Islamic geometry) around a single point of evidence. */
export function Mark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <path d="M32 6 L41 23 L58 32 L41 41 L32 58 L23 41 L6 32 L23 23 Z" fill="none" stroke="var(--signal)" strokeWidth="5" strokeLinejoin="round" />
      <circle cx="32" cy="32" r="7" fill="var(--signal)" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <Link to="/" className="group flex items-center gap-2" aria-label="Daleel home">
      <Mark className="h-6 w-6" />
      <span className="text-lg font-semibold tracking-tight text-ink">Daleel</span>
      <span className="text-base text-accent" lang="ar" dir="rtl">دليل</span>
    </Link>
  );
}

export function Layout() {
  const [dark, setDark] = useTheme();
  const nav = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-brand-soft text-brand font-medium" : "text-muted hover:text-ink"}`;
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-line bg-panel/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4">
          <div className="flex items-center gap-6">
            <Wordmark />
            <nav className="hidden items-center gap-1 sm:flex" aria-label="Main">
              <NavLink to="/demo" className={nav}>Demo</NavLink>
              <NavLink to="/rulebook" className={nav}>Rulebook</NavLink>
              <NavLink to="/how-it-works" className={nav}>How it works</NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden rounded border border-line px-2 py-0.5 text-xs text-muted lg:inline">Synthetic demo data</span>
            <PersonSwitcher />
            <button
              onClick={() => setDark(!dark)}
              className="rounded-md p-2 text-muted hover:bg-brand-soft hover:text-ink"
              aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </div>
        <nav className="flex gap-1 border-t border-line px-4 py-1 sm:hidden" aria-label="Main mobile">
          <NavLink to="/demo" className={nav}>Demo</NavLink>
          <NavLink to="/rulebook" className={nav}>Rulebook</NavLink>
          <NavLink to="/how-it-works" className={nav}>How it works</NavLink>
        </nav>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-panel">
        <div className="mx-auto max-w-7xl px-4 py-5 text-xs leading-relaxed text-muted">
          Daleel is a portfolio project. The demo uses synthetic data for a fictional bank, Example Islamic Bank Ltd.
          Results are not certified by the State Bank of Pakistan or any compliance, legal or Shariah adviser.
        </div>
      </footer>
    </div>
  );
}
