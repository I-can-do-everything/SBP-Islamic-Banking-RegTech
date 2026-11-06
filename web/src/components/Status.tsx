import { AlertTriangle, CheckCircle2, CircleDashed, Info, OctagonX } from "lucide-react";
import type { Status } from "../lib/api";

// Status is never shown by colour alone: every badge has an icon and a word.
const META: Record<Status, { label: string; icon: typeof Info; cls: string }> = {
  PASS: { label: "Pass", icon: CheckCircle2, cls: "text-pass bg-pass-soft border-pass/30" },
  WARNING: { label: "Warning", icon: AlertTriangle, cls: "text-warn bg-warn-soft border-warn/30" },
  FAIL: { label: "Breach", icon: OctagonX, cls: "text-fail bg-fail-soft border-fail/30" },
  INFO: { label: "Info", icon: Info, cls: "text-info bg-info-soft border-info/30" },
  NOT_AVAILABLE: { label: "Not available", icon: CircleDashed, cls: "text-faint bg-surface border-line" },
};

export function StatusBadge({ status, compact = false }: { status: Status; compact?: boolean }) {
  const m = META[status] ?? META.INFO;
  const Icon = m.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${m.cls}`}>
      <Icon size={13} aria-hidden />
      {!compact && m.label}
      {compact && <span className="sr-only">{m.label}</span>}
    </span>
  );
}

export function StatusIcon({ status, size = 16 }: { status: Status; size?: number }) {
  const m = META[status] ?? META.INFO;
  const Icon = m.icon;
  return <Icon size={size} className={m.cls.split(" ")[0]} aria-label={m.label} />;
}

export function VerificationBadge({ value }: { value?: string }) {
  const v = value ?? "assumption";
  const cls =
    v.startsWith("primary")
      ? "text-pass border-pass/30 bg-pass-soft"
      : v === "secondary"
        ? "text-info border-info/30 bg-info-soft"
        : v === "principle"
          ? "text-brand border-brand/30 bg-brand-soft"
          : "text-warn border-warn/30 bg-warn-soft";
  const label = v.startsWith("primary") ? `Primary source${v.includes("translated") ? " (translated)" : ""}` : v === "secondary" ? "Secondary source" : v === "principle" ? "Shariah principle" : "Demo assumption";
  return <span className={`rounded border px-1.5 py-0.5 text-[11px] font-medium ${cls}`}>{label}</span>;
}
