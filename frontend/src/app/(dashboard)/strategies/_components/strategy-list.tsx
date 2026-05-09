// 전략 목록 컨테이너 — 검색/필터/정렬/페이지네이션 + 그리드/리스트 뷰 토글 (06 prototype 매핑)
"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { LayoutGridIcon, ListIcon, PlusIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/skeleton";
import { useStrategies } from "@/features/strategy/hooks";
import type { ParseStatus, StrategyListItem, StrategyListQuery } from "@/features/strategy/schemas";
import { StrategyCard } from "./strategy-card";
import { StrategyEmptyState } from "./strategy-empty-state";
import {
  StrategyListFilterBar,
  type SortKey,
  type StatusFilter,
} from "./strategy-list-filter-bar";
import { StrategyTable } from "./strategy-table";

const PAGE_SIZE = 20;
type ViewMode = "grid" | "list";

export function StrategyList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // 뷰 토글 / 정렬 / 검색은 세션 한정 (URL 노출 가치 낮음).
  // 필터·페이지는 URL 단일 source — Next 16 routing convention.
  const [view, setView] = useState<ViewMode>("grid");
  const [sort, setSort] = useState<SortKey>("updated_desc");
  const [search, setSearch] = useState("");

  const status: StatusFilter = (() => {
    if (searchParams.get("favorite") === "true") return "favorite";
    if (searchParams.get("archived") === "true") return "archived";
    const ps = searchParams.get("parse_status");
    if (ps === "ok" || ps === "unsupported" || ps === "error") return ps;
    return "all";
  })();
  const page = Math.max(0, Number(searchParams.get("page") ?? "0") || 0);

  const pushStatus = (v: StatusFilter) => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("parse_status");
    params.delete("archived");
    params.delete("favorite");
    params.delete("page");
    if (v === "archived") params.set("archived", "true");
    else if (v === "favorite") params.set("favorite", "true");
    else if (v !== "all") params.set("parse_status", v);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  const pushPage = (p: number) => {
    const params = new URLSearchParams(searchParams.toString());
    if (p <= 0) params.delete("page");
    else params.set("page", String(p));
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  // BE 호출 query — favorite 필터는 BE 미지원이므로 'all' 로 fallback,
  // 클라이언트에서 다시 favorite 만 추려낸다 (placeholder 동작, 활성화는 후속 BL).
  const query = useMemo<StrategyListQuery>(() => {
    const q: StrategyListQuery = {
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
      is_archived: status === "archived",
    };
    if (status === "ok" || status === "unsupported" || status === "error") {
      q.parse_status = status as ParseStatus;
    }
    return q;
  }, [page, status]);

  const { data, isLoading, isError, refetch } = useStrategies(query);

  // 클라이언트-side 검색·정렬·즐겨찾기 필터.
  // 즐겨찾기는 BE 미지원이므로 현재 페이지 응답에서만 매치 (UI placeholder).
  const filteredItems = useMemo<StrategyListItem[]>(() => {
    let arr: StrategyListItem[] = data?.items ?? [];
    if (status === "favorite") {
      // BE 필드 부재 — 현재는 모두 비-즐겨찾기로 취급. 후속 BL 에서 sync.
      arr = [];
    }
    const q = search.trim().toLowerCase();
    if (q.length > 0) {
      arr = arr.filter((s) => {
        return (
          s.name.toLowerCase().includes(q) ||
          (s.symbol ?? "").toLowerCase().includes(q)
        );
      });
    }
    const sorted = arr.slice();
    if (sort === "name_asc") {
      sorted.sort((a, b) => a.name.localeCompare(b.name, "ko"));
    } else if (sort === "created_desc") {
      sorted.sort((a, b) => b.created_at.localeCompare(a.created_at));
    } else {
      sorted.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    }
    return sorted;
  }, [data?.items, search, sort, status]);

  const totalPages = data?.total_pages ?? 0;
  const isEmpty =
    !isLoading &&
    !isError &&
    filteredItems.length === 0 &&
    page === 0 &&
    status === "all" &&
    search.length === 0;

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      {/* 헤더 — DESIGN.md §3.2 H2 토큰은 globals.css base 에서 자동 적용 */}
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">내 전략</h1>
          <p className="text-sm text-text-secondary">
            Pine Script 전략 관리 · 백테스트 · 데모 트레이딩
          </p>
        </div>
        <Button render={<Link href="/strategies/new" />} nativeButton={false}>
          <PlusIcon className="size-4" />새 전략
        </Button>
      </header>

      {/* 필터바 (검색 + chip + 정렬) + 뷰 토글 */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start">
        <div className="flex-1 min-w-0">
          <StrategyListFilterBar
            status={status}
            sort={sort}
            search={search}
            onStatusChange={pushStatus}
            onSortChange={setSort}
            onSearchChange={setSearch}
          />
        </div>
        <div className="hidden lg:flex h-10 rounded-[var(--radius-md)] border border-[color:var(--border)]">
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

      {/* aria-live: 검색 결과 갱신 알림 */}
      <p
        role="status"
        aria-live="polite"
        className="sr-only"
      >
        {isLoading
          ? "전략 목록을 불러오는 중"
          : `전략 ${filteredItems.length}개 표시`}
      </p>

      {/* 로딩 / 에러 / 빈 상태 / 콘텐츠 */}
      {isError ? (
        <div className="rounded-[var(--radius-lg)] border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-6 text-sm">
          <p className="font-medium text-[color:var(--destructive)]">
            전략 목록을 불러오지 못했습니다.
          </p>
          <p className="mt-1 text-xs text-[color:var(--text-secondary)]">
            네트워크 또는 인증 문제가 있을 수 있습니다.
          </p>
          <Button variant="outline" className="mt-4" onClick={() => refetch()}>
            다시 시도
          </Button>
        </div>
      ) : isLoading ? (
        <ListSkeleton view={view} />
      ) : isEmpty ? (
        <StrategyEmptyState />
      ) : filteredItems.length === 0 ? (
        <NoResultsHint search={search} status={status} />
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 gap-5 motion-safe:animate-[fadeInUp_200ms_ease-out_both] md:grid-cols-2 xl:grid-cols-3">
          {filteredItems.map((s) => (
            <StrategyCard key={s.id} strategy={s} />
          ))}
        </div>
      ) : (
        <div className="motion-safe:animate-[fadeInUp_200ms_ease-out_both]">
          <StrategyTable items={filteredItems} />
        </div>
      )}

      {/* 페이지네이션 — BE 페이지 기준 (클라 필터 적용 전) */}
      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={data!.total}
          limit={data!.limit}
          onPage={pushPage}
        />
      )}
    </div>
  );
}

// ---- local sub-components ----

function NoResultsHint({ search, status }: { search: string; status: StatusFilter }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-dark)] bg-white p-10 text-center text-sm">
      <p className="font-medium text-[color:var(--text-primary)]">
        {status === "favorite"
          ? "즐겨찾기 한 전략이 없습니다."
          : `'${search}' 검색 결과가 없습니다.`}
      </p>
      <p className="mt-1 text-xs text-[color:var(--text-secondary)]">
        다른 키워드로 검색하거나 필터를 해제해 보세요.
      </p>
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
        <Skeleton key={i} variant="card" />
      ))}
    </div>
  );
}
