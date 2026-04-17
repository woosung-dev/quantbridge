"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { PlusIcon, LayoutGridIcon, ListIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useStrategies } from "@/features/strategy/hooks";
import type { ParseStatus, StrategyListQuery } from "@/features/strategy/schemas";
import { StrategyCard } from "./strategy-card";
import { StrategyTable } from "./strategy-table";
import { StrategyEmptyState } from "./strategy-empty-state";

const PAGE_SIZE = 20;
type ViewMode = "grid" | "list";
type StatusFilter = "all" | ParseStatus | "archived";

export function StrategyList() {
  const [view, setView] = useState<ViewMode>("grid");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);

  const query = useMemo<StrategyListQuery>(() => {
    const q: StrategyListQuery = {
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
      is_archived: status === "archived",
    };
    if (status === "ok" || status === "unsupported" || status === "error") {
      q.parse_status = status;
    }
    return q;
  }, [page, status]);

  const { data, isLoading, isError, refetch } = useStrategies(query);

  if (isError) {
    return (
      <section className="p-8">
        <p className="text-destructive">전략 목록을 불러오지 못했습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          다시 시도
        </Button>
      </section>
    );
  }

  const totalPages = data?.total_pages ?? 0;
  const isEmpty = !isLoading && (data?.items.length ?? 0) === 0 && page === 0 && status === "all";

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      {/* 헤더 */}
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-[color:var(--text-primary)]">
            내 전략
          </h1>
          <p className="text-sm text-[color:var(--text-secondary)]">
            Pine Script 전략 관리
          </p>
        </div>
        <Button render={<Link href="/strategies/new" />}>
          <PlusIcon className="size-4" />새 전략
        </Button>
      </header>

      {/* 필터 / 뷰 토글 */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <FilterChips value={status} onChange={(s) => { setStatus(s); setPage(0); }} />
        <div className="ml-auto flex items-center gap-2">
          <Select defaultValue="updated_desc">
            <SelectTrigger className="h-9 w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated_desc">최근 수정순</SelectItem>
              <SelectItem value="updated_asc">오래된 순</SelectItem>
              <SelectItem value="name_asc">이름순</SelectItem>
            </SelectContent>
          </Select>
          <div className="hidden lg:flex rounded-md border border-[color:var(--border)]">
            <Button
              size="icon"
              variant={view === "grid" ? "default" : "ghost"}
              className="rounded-r-none"
              aria-label="그리드 뷰"
              onClick={() => setView("grid")}
            >
              <LayoutGridIcon className="size-4" />
            </Button>
            <Button
              size="icon"
              variant={view === "list" ? "default" : "ghost"}
              className="rounded-l-none"
              aria-label="목록 뷰"
              onClick={() => setView("list")}
            >
              <ListIcon className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* 로딩 / 빈 상태 / 콘텐츠 */}
      {isLoading ? (
        <ListSkeleton view={view} />
      ) : isEmpty ? (
        <StrategyEmptyState />
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {data!.items.map((s) => <StrategyCard key={s.id} strategy={s} />)}
        </div>
      ) : (
        <StrategyTable items={data!.items} />
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={data!.total}
          limit={data!.limit}
          onPage={setPage}
        />
      )}
    </div>
  );
}

// ---- local sub-components (same file) ----

function FilterChips(props: {
  value: StatusFilter;
  onChange: (v: StatusFilter) => void;
}) {
  const items: Array<{ id: StatusFilter; label: string }> = [
    { id: "all", label: "모두" },
    { id: "ok", label: "파싱 성공" },
    { id: "unsupported", label: "미지원" },
    { id: "error", label: "파싱 실패" },
    { id: "archived", label: "보관됨" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => {
        const active = it.id === props.value;
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => props.onChange(it.id)}
            aria-pressed={active}
            className={
              "rounded-full border px-3 py-1 text-xs font-medium transition " +
              (active
                ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] text-[color:var(--primary)]"
                : "border-[color:var(--border)] text-[color:var(--text-secondary)] hover:bg-[color:var(--bg-alt)]")
            }
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

function Pagination(props: {
  page: number;
  totalPages: number;
  total: number;
  limit: number;
  onPage: (p: number) => void;
}) {
  const from = props.page * props.limit + 1;
  const to = Math.min((props.page + 1) * props.limit, props.total);
  return (
    <nav className="mt-8 flex items-center justify-between" aria-label="페이지 탐색">
      <p className="text-sm text-[color:var(--text-secondary)]">
        {props.total}개 중 {from}–{to} 표시
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={props.page === 0}
          onClick={() => props.onPage(props.page - 1)}
        >
          이전
        </Button>
        <span className="text-sm font-mono">
          {props.page + 1} / {props.totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={props.page + 1 >= props.totalPages}
          onClick={() => props.onPage(props.page + 1)}
        >
          다음
        </Button>
      </div>
    </nav>
  );
}

function ListSkeleton({ view }: { view: ViewMode }) {
  return (
    <div
      className={
        view === "grid"
          ? "grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3"
          : "flex flex-col gap-2"
      }
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-36 animate-pulse rounded-[var(--radius-lg)] bg-[color:var(--bg-alt)]"
        />
      ))}
    </div>
  );
}
