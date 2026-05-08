// Sprint 43 W15 — Waitlist search + 5 chip 상태 필터 toolbar (W6 strategy filter-bar 패턴 차용).
"use client";

import { useEffect, useRef, useState } from "react";
import { SearchIcon } from "lucide-react";

import { useDebouncedValue } from "@/features/strategy/utils";
import type { WaitlistStatus } from "@/features/waitlist/schemas";

export type WaitlistFilter = WaitlistStatus | "all";

const CHIP_TONE: Record<WaitlistFilter, string> = {
  all: "var(--text-muted)",
  pending: "var(--warning)",
  invited: "var(--primary)",
  joined: "var(--success)",
  rejected: "var(--text-muted)",
};

const CHIPS: ReadonlyArray<{ id: WaitlistFilter; label: string }> = [
  { id: "all", label: "전체" },
  { id: "pending", label: "대기중" },
  { id: "invited", label: "초대됨" },
  { id: "joined", label: "가입완료" },
  { id: "rejected", label: "거절" },
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
  const [draft, setDraft] = useState(search);
  const debounced = useDebouncedValue(draft, 300);
  const lastEmittedRef = useRef(search);

  // debounce 결과만 부모로 전파 (set-state-in-effect 회피용 ref 비교, LESSON H-1).
  useEffect(() => {
    if (debounced !== lastEmittedRef.current) {
      lastEmittedRef.current = debounced;
      onSearchChange(debounced);
    }
  }, [debounced, onSearchChange]);

  return (
    <div
      role="toolbar"
      aria-label="Waitlist 필터"
      className="mb-4 flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center"
    >
      <label
        className="flex h-10 w-full items-center gap-2 rounded-[var(--radius-md)] border border-[color:var(--border)] bg-white px-3 transition focus-within:border-[color:var(--primary)] focus-within:ring-2 focus-within:ring-[color:var(--primary-light)] md:w-[280px]"
        aria-label="이메일 검색"
      >
        <SearchIcon
          className="size-4 text-[color:var(--text-muted)]"
          aria-hidden="true"
        />
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="이메일 검색..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-[color:var(--text-muted)]"
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
              className={
                "inline-flex flex-shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition " +
                (active
                  ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] text-[color:var(--primary)] shadow-sm"
                  : "border-[color:var(--border)] bg-white text-[color:var(--text-secondary)] hover:border-[color:var(--border-dark)] hover:bg-[color:var(--bg-alt)]")
              }
            >
              {chip.id !== "all" && (
                <span
                  aria-hidden="true"
                  className="size-1.5 rounded-full"
                  style={{ backgroundColor: CHIP_TONE[chip.id] }}
                />
              )}
              <span>{chip.label}</span>
              {typeof count === "number" && (
                <span className="font-mono text-[10px] tabular-nums text-[color:var(--text-muted)]">
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
