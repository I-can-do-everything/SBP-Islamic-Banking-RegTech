import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type Role } from "../lib/api";

export const ROLE_LABEL: Record<Role, string> = { PREPARER: "Preparer", APPROVER: "Approver", ADMIN: "Administrator" };

// In the demo one visitor plays every person, so four eyes approval can be tried.
// In a real deployment each person signs in separately and this switch is off.
export function PersonSwitcher() {
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const switcher = useMutation({
    mutationFn: api.switchPerson,
    onSuccess: () => {
      setOpen(false);
      client.invalidateQueries();
    },
  });
  useEffect(() => {
    const close = (e: MouseEvent) => box.current && !box.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  if (!me.data) return null;
  const canSwitch = me.data.demo_personas;
  return (
    <div className="relative" ref={box}>
      <button
        onClick={() => canSwitch && setOpen(!open)}
        className="flex items-center gap-2 rounded-md border border-line px-2.5 py-1.5 text-left text-xs hover:bg-brand-soft"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Acting as ${me.data.name}. ${canSwitch ? "Switch person" : ""}`}
      >
        <UserRound size={15} className="text-brand" aria-hidden />
        <span className="hidden sm:block">
          <span className="block font-medium text-ink">{me.data.name}</span>
          <span className="block text-faint">{ROLE_LABEL[me.data.role]}</span>
        </span>
        {canSwitch && <ChevronDown size={14} className="text-faint" aria-hidden />}
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-line bg-panel p-2 shadow-lg">
          <p className="px-2 pb-2 pt-1 text-xs leading-relaxed text-muted">
            Demo mode: act as another person to try four eyes approval. In a real bank each person signs in separately.
          </p>
          {me.data.members.map((m) => (
            <button
              key={m.id}
              role="menuitem"
              disabled={m.id === me.data.member_id || switcher.isPending}
              onClick={() => switcher.mutate(m.id)}
              className="flex w-full items-start gap-3 rounded-lg px-2 py-2 text-left hover:bg-brand-soft disabled:cursor-default disabled:bg-brand-soft/60"
            >
              <UserRound size={16} className="mt-0.5 text-faint" aria-hidden />
              <span>
                <span className="block text-sm font-medium">{m.display_name} {m.id === me.data.member_id && <span className="text-xs font-normal text-brand">(you)</span>}</span>
                <span className="block text-xs text-muted">{ROLE_LABEL[m.role]}: {m.title}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
