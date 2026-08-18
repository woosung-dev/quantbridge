// Sprint 43 W15 — Waitlist search + 5 chip 상태 필터 toolbar (W6 strategy filter-bar 패턴 차용).
"use client";

import { useEffect, useRef, useState } from "react";
import { SearchIcon } from "lucide-react";

import { WAITLIST_STATUS_LABEL } from "@/features/waitlist/labels";
import type { WaitlistStatus } from "@/features/waitlist/schemas";

export type WaitlistFilter = WaitlistStatus | "all";

// 상태 라벨은 용어 SSOT(labels.ts)에서 파생 — 표 배지와 같은 문자열.
const CHIPS: ReadonlyArray<{ id: WaitlistFilter; label: string }> = [
  { id: "all", label: "전체" },
  { id: "pending", label: WAITLIST_STATUS_LABEL.pending.label },
  { id: "invited", label: WAITLIST_STATUS_LABEL.invited.label },
  { id: "joined", label: WAITLIST_STATUS_LABEL.joined.label },
  { id: "rejected", label: WAITLIST_STATUS_LABEL.rejected.label },
];

export interface WaitlistFilterBarProps {
  status: WaitlistFilter;
  search: string;
  onStatusChange: (next: WaitlistFilter) => void;
  onSearchChange: (next: string) => void;
  counts?: Partial<Record<WaitlistFilter, number>>;
}

export function WaitlistFilterBar(props: WaitlistFilterBarProps) {
  const { status, search, onStatusChange, onSearchChange, counts } = props;
  // draft 는 input 즉시 반응용. 부모 전파는 이벤트 핸들러 내 300ms debounce
  // (상호작용 로직을 effect 로 두지 않는다 — you-might-not-need-an-effect).
  const [draft, setDraft] = useState(search);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchInput = (value: string) => {
    setDraft(value);
    if (debounceTimerRef.current !== null) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => onSearchChange(value), 300);
  };

  // unmount 시 대기 중 타이머 정리 (setState-after-unmount 계열 방지).
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current !== null) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return (
    <div
      role="toolbar"
      aria-label="Waitlist 필터"
      className="mb-4 flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center"
    >
      <label
        className="bg-card flex h-10 w-full items-center gap-2 rounded-[var(--radius-md)] border border-[color:var(--border)] px-3 transition focus-within:border-[color:var(--primary)] md:w-[280px]"
        aria-label="이메일 검색"
      >
        <SearchIcon className="size-4 text-[color:var(--text-muted)]" aria-hidden="true" />
        <input
          type="text"
          value={draft}
          onChange={(e) => handleSearchInput(e.target.value)}
          placeholder="이메일 검색..."
          className="flex-1 bg-transparent text-sm placeholder:text-[color:var(--text-muted)]"
        />
      </label>

      <div
        role="radiogroup"
        aria-label="상태 필터"
        className="-mx-2 flex flex-nowrap gap-2 overflow-x-auto px-2 md:mx-0 md:flex-wrap md:overflow-visible md:px-0"
      >
        {CHIPS.map((chip) => {
          const active = chip.id === status;
          const count = counts?.[chip.id];
          return (
            <button
              key={chip.id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onStatusChange(chip.id)}
              data-active={active || undefined}
              className={
                // Precision Instrument: 플랫 + 1px 보더 — chipPop/hover lift/shadow 폐기, 색 변화만.
                // v3 캐논 — pill 반경 폐기, 태그 반경(radius-sm 4px)으로 타이트닝 (DESIGN.md §5/§7.4).
                "inline-flex flex-shrink-0 items-center gap-1.5 rounded-[var(--radius-sm)] border px-3 py-1.5 text-xs font-medium transition-colors duration-200 ease-out " +
                (active
                  ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] text-[color:var(--primary)]"
                  : "bg-card border-[color:var(--border)] text-[color:var(--text-secondary)] hover:border-[color:var(--border-dark)] hover:bg-[color:var(--bg-alt)]")
              }
            >
              <span>{chip.label}</span>
              {typeof count === "number" && (
                <span className="font-mono text-[10px] text-[color:var(--text-muted)] tabular-nums">
                  ({count})
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
