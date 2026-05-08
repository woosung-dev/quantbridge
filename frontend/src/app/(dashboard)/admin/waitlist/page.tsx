"use client";

// Sprint 43 W15 — Admin waitlist 내부 dashboard polish (KPI strip + filter bar + sortable table).
// Sprint 11 Phase C 의 단일 page 를 _components/ 3 모듈로 분리. App Shell 은 (dashboard)/layout.tsx 에서 wrap.
// Clerk JWT + BE WAITLIST_ADMIN_EMAILS 화이트리스트 유지. 403 안내 보존.

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { useAdminWaitlistList, useApproveWaitlist } from "@/features/waitlist/hooks";
import type { WaitlistStatus } from "@/features/waitlist/schemas";
import { ApiError } from "@/lib/api-client";

import { WaitlistFilterBar, type WaitlistFilter } from "./_components/waitlist-filter-bar";
import { WaitlistStatsStrip } from "./_components/waitlist-stats-strip";
import { WaitlistTable } from "./_components/waitlist-table";

export default function AdminWaitlistPage() {
  const [filter, setFilter] = useState<WaitlistFilter>("pending");
  const [search, setSearch] = useState("");

  // BE 는 status 단일 필터만 지원 — 검색은 클라이언트 측에서 email 부분일치.
  const query = filter === "all" ? {} : { status: filter as WaitlistStatus };
  const { data, isPending, error } = useAdminWaitlistList(query);
  const approve = useApproveWaitlist({
    onSuccess: (approved) => {
      toast.success(`초대 발송: ${approved.email}`);
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "승인 실패";
      toast.error(msg);
    },
  });

  const errStatus = error instanceof ApiError ? error.status : undefined;

  const filteredItems = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    if (!q) return data.items;
    return data.items.filter((i) => i.email.toLowerCase().includes(q));
  }, [data, search]);

  return (
    <div className="mx-auto max-w-[1200px] space-y-6 px-6 py-8">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-bold">Waitlist 관리</h1>
        <p className="text-sm text-[color:var(--text-secondary)]">
          신청자를 검토하고 Resend 로 Beta 초대를 발송합니다.
        </p>
      </header>

      {data ? (
        <WaitlistStatsStrip items={data.items} total={data.total} />
      ) : null}

      <WaitlistFilterBar
        status={filter}
        search={search}
        onStatusChange={setFilter}
        onSearchChange={setSearch}
      />

      {errStatus === 403 ? (
        <div className="rounded-[var(--radius-md)] border-l-4 border-red-500 bg-red-50 p-4 text-sm text-red-900">
          <strong>관리자 권한이 필요합니다.</strong> 이메일이 admin allowlist 에
          없습니다. QuantBridge 운영자에게 문의하세요.
        </div>
      ) : null}

      {isPending && !error ? (
        <p className="text-sm text-[color:var(--text-tertiary)]">불러오는 중…</p>
      ) : null}

      {error && errStatus !== 403 ? (
        <div className="rounded-[var(--radius-md)] border-l-4 border-red-500 bg-red-50 p-4 text-sm text-red-900">
          Waitlist 불러오기 실패: {error.message}
        </div>
      ) : null}

      {data && filteredItems.length === 0 ? (
        <div
          data-testid="waitlist-empty-state"
          className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border)] bg-[color:var(--bg-alt)]/60 px-6 py-12 text-center"
        >
          <span
            aria-hidden="true"
            className="grid h-12 w-12 place-items-center rounded-full bg-[color:var(--primary-light)] text-[color:var(--primary)]"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </span>
          <p className="text-sm font-medium text-[color:var(--text-primary)]">
            {search
              ? `"${search}" 와 일치하는 신청이 없습니다`
              : "이 필터에 해당하는 신청이 없습니다"}
          </p>
          <p className="text-xs text-[color:var(--text-tertiary)]">
            {search
              ? "검색어를 비우거나 다른 상태 필터를 선택해 보세요."
              : "다른 상태 필터를 선택하면 더 많은 신청을 볼 수 있습니다."}
          </p>
        </div>
      ) : null}

      {data && filteredItems.length > 0 ? (
        <WaitlistTable
          items={filteredItems}
          onApprove={(id) => approve.mutate(id)}
          isApproving={approve.isPending}
        />
      ) : null}

      {data ? (
        <p className="text-xs text-[color:var(--text-tertiary)]">
          전체: {data.total}
          {search ? ` · 검색 결과: ${filteredItems.length}` : null}
        </p>
      ) : null}
    </div>
  );
}
