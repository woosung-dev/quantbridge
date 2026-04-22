"use client";

import { cn } from "@/lib/utils";

// 표시용 레이블 — UTC 시간은 사용자 안내용(비즈니스 필터링은 BE 전담)
const SESSIONS = [
  { value: "asia", label: "🌏 Asia", sub: "UTC 00–07" },
  { value: "london", label: "🇬🇧 London", sub: "UTC 08–16" },
  { value: "ny", label: "🗽 New York", sub: "UTC 13–20" },
] as const;

type SessionValue = (typeof SESSIONS)[number]["value"];

interface SessionChipsProps {
  value: string[];
  onChange: (next: string[]) => void;
}

export function SessionChips({ value, onChange }: SessionChipsProps) {
  function toggle(session: SessionValue) {
    onChange(
      value.includes(session)
        ? value.filter((s) => s !== session)
        : [...value, session],
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {SESSIONS.map(({ value: v, label, sub }) => {
        const selected = value.includes(v);
        return (
          <button
            key={v}
            type="button"
            onClick={() => toggle(v)}
            aria-pressed={selected}
            className={cn(
              "flex flex-col items-center rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              selected
                ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white"
                : "border-[color:var(--border)] text-[color:var(--text-secondary)] hover:border-[color:var(--primary)] hover:text-[color:var(--primary)]",
            )}
          >
            <span>{label}</span>
            <span className="text-xs opacity-70">{sub}</span>
          </button>
        );
      })}
    </div>
  );
}
