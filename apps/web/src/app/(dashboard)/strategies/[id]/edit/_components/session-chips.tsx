"use client";

// 거래 세션 토글 칩 — C 디자인 언어. 상호배타 아님(다중 선택)이라 .tab 이 아니라 aria-pressed
// 토글 버튼이다. 선택 시 코퍼 활성, 아니면 중립. 이모지 대신 lucide 아이콘.

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
              "flex flex-col items-center rounded-[var(--r)] border px-4 py-2 text-sm font-medium transition-colors",
              selected
                ? "border-[color:var(--copper-line)] bg-[color:var(--copper-soft)] text-[color:var(--copper)]"
                : "border-[color:var(--line)] text-[color:var(--ink-2)] hover:border-[color:var(--line-2)] hover:text-[color:var(--ink)]",
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
