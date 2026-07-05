// 전략 목록의 검색 + 6 chip 상태 필터 + 정렬 dropdown 을 묶는 toolbar 컴포넌트
"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDownIcon, SearchIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export type StatusFilter =
  | "all"
  | "ok"
  | "unsupported"
  | "error"
  | "archived"
  | "favorite";

export type SortKey = "updated_desc" | "created_desc" | "name_asc";

const SORT_LABEL: Record<SortKey, string> = {
  updated_desc: "최근 수정순",
  created_desc: "생성일순",
  name_asc: "이름순",
};

const CHIP_TONE: Record<StatusFilter, string> = {
  all: "var(--text-muted)",
  ok: "var(--success)",
  unsupported: "var(--warning)",
  error: "var(--destructive)",
  archived: "var(--text-muted)",
  favorite: "var(--primary)",
};

const CHIPS: ReadonlyArray<{ id: StatusFilter; label: string }> = [
  { id: "all", label: "모두" },
  { id: "ok", label: "파싱 성공" },
  { id: "unsupported", label: "미지원" },
  { id: "error", label: "파싱 실패" },
  { id: "archived", label: "보관됨" },
  { id: "favorite", label: "즐겨찾기" },
];

export interface StrategyListFilterBarProps {
  status: StatusFilter;
  sort: SortKey;
  search: string;
  onStatusChange: (next: StatusFilter) => void;
  onSortChange: (next: SortKey) => void;
  onSearchChange: (next: string) => void;
  /** chip 라벨 옆 카운트. 미제공 시 미표시. */
  counts?: Partial<Record<StatusFilter, number>>;
}

/**
 * 06-strategies-list prototype §toolbar 매핑.
 * - search: 300ms debounce 후 onSearchChange 발화 (CPU loop 회피, LESSON H-1)
 * - filter chip: aria-pressed + chip-dot 토큰 색
 * - 정렬: dropdown menu (shadcn) — prototype 의 native select 대신 a11y 우수
 */
export function StrategyListFilterBar(props: StrategyListFilterBarProps) {
  const { status, sort, search, onStatusChange, onSortChange, onSearchChange, counts } =
    props;
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
      aria-label="전략 필터 및 정렬"
      className="mb-6 flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center"
    >
      {/* 검색 입력 */}
      <label
        className="flex h-10 w-full items-center gap-2 rounded-[var(--radius-md)] border border-[color:var(--border)] bg-card px-3 transition focus-within:border-[color:var(--primary)] focus-within:ring-2 focus-within:ring-[color:var(--primary-light)] md:w-[280px]"
        aria-label="전략 검색"
      >
        <SearchIcon className="size-4 text-[color:var(--text-muted)]" aria-hidden="true" />
        <input
          type="text"
          value={draft}
          onChange={(e) => handleSearchInput(e.target.value)}
          placeholder="전략 이름·심볼 검색..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-[color:var(--text-muted)]"
        />
      </label>

      {/* 필터 chip group — 모바일에서 가로 스크롤 */}
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
              // Sprint 61 T-2 (BL-339): touch target ≥44pt 보장 (min-h-11 + 모바일 px-4 확대).
              // Mobile QA 페르소나 발견: 30h 시 Apple HIG/Material 44pt 미달 → 한 손 사용자 오탑.
              className={
                "inline-flex min-h-11 flex-shrink-0 items-center gap-1.5 rounded-full border px-4 py-1.5 text-xs font-medium transition-colors duration-150 ease-out md:min-h-0 md:px-3 " +
                (active
                  ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] text-[color:var(--primary)] shadow-sm"
                  : "border-[color:var(--border)] bg-card text-[color:var(--text-secondary)] hover:border-[color:var(--border-dark)] hover:bg-[color:var(--bg-alt)]")
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

      {/* 정렬 dropdown */}
      <div className="md:ml-auto">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <button
                type="button"
                aria-label="정렬 기준"
                className="inline-flex h-9 items-center gap-1.5 rounded-[var(--radius-md)] border border-[color:var(--border)] bg-card px-3 text-xs font-medium text-[color:var(--text-secondary)] transition hover:border-[color:var(--border-dark)] hover:bg-[color:var(--bg-alt)]"
              />
            }
          >
            <span>{SORT_LABEL[sort]}</span>
            <ChevronDownIcon
              className="size-3.5 text-[color:var(--text-muted)]"
              aria-hidden="true"
            />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {(Object.keys(SORT_LABEL) as SortKey[]).map((key) => (
              <DropdownMenuItem
                key={key}
                onClick={() => onSortChange(key)}
                aria-current={sort === key ? "true" : undefined}
              >
                {SORT_LABEL[key]}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
