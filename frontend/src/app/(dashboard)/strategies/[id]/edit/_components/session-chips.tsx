"use client";

// 거래 세션 토글 칩 — Precision Instrument: 이모지 대신 lucide 아이콘 (DESIGN.md §1 이모지 금지)

import { Building2Icon, GlobeIcon, LandmarkIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// 표시용 레이블 — UTC 시간은 사용자 안내용(비즈니스 필터링은 BE 전담)
const SESSIONS = [
  { value: "asia", label: "Asia", sub: "UTC 00–07", icon: GlobeIcon },
  { value: "london", label: "London", sub: "UTC 08–16", icon: Building2Icon },
  { value: "ny", label: "New York", sub: "UTC 13–20", icon: LandmarkIcon },
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
      {SESSIONS.map(({ value: v, label, sub, icon: Icon }) => {
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
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-text-secondary hover:border-primary hover:text-primary",
            )}
          >
            <span className="flex items-center gap-1.5">
              <Icon className="size-3.5 shrink-0" aria-hidden />
              {label}
            </span>
            <span className="text-xs opacity-70">{sub}</span>
          </button>
        );
      })}
    </div>
  );
}
