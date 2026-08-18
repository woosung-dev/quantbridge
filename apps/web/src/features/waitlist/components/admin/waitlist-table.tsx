// Sprint 43 W15 — Waitlist 신청자 list table (sort + status badge + approve action).
// W6 strategy-table 패턴 차용. 정렬 키 = email/created/status, aria-sort 적용.
"use client";

import { ChevronDown, ChevronsUpDown, ChevronUp, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { formatDate } from "@/features/backtest/utils";
import { WAITLIST_ACTION_EMPTY_REASON, WAITLIST_STATUS_LABEL } from "@/features/waitlist/labels";
import type { WaitlistApplicationResponse, WaitlistStatus } from "@/features/waitlist/schemas";
import { CHIP_TONE_CLASS, EMPTY_CELL, statusLabelOf } from "@/lib/labels";

type SortKey = "email" | "created" | "status";
type SortDir = "asc" | "desc";

const STATUS_ORDER: Record<WaitlistStatus, number> = {
  pending: 0,
  invited: 1,
  joined: 2,
  rejected: 3,
};

interface WaitlistTableProps {
  items: readonly WaitlistApplicationResponse[];
  onApprove: (id: string) => void;
  isApproving: boolean;
}

export function WaitlistTable({ items, onApprove, isApproving }: WaitlistTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("created");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "email") return a.email.localeCompare(b.email) * dir;
      if (sortKey === "status") return (STATUS_ORDER[a.status] - STATUS_ORDER[b.status]) * dir;
      // created
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * dir;
    });
    return copy;
  }, [items, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "created" ? "desc" : "asc");
    }
  };

  const ariaSort = (key: SortKey): "ascending" | "descending" | "none" => {
    if (sortKey !== key) return "none";
    return sortDir === "asc" ? "ascending" : "descending";
  };

  return (
    <div className="bg-card overflow-x-auto rounded-[var(--radius-lg)] border border-[color:var(--border)]">
      <table className="w-full text-left text-sm" role="table">
        <thead className="bg-[color:var(--bg-alt)] text-xs tracking-wide text-[color:var(--text-secondary)] uppercase">
          <tr>
            <SortHeader
              label="이메일"
              active={sortKey === "email"}
              dir={sortDir}
              ariaSort={ariaSort("email")}
              onClick={() => handleSort("email")}
            />
            <th scope="col" className="px-4 py-3">
              TV 구독
            </th>
            <th scope="col" className="px-4 py-3">
              자본
            </th>
            <th scope="col" className="px-4 py-3">
              Pine 경험
            </th>
            <th scope="col" className="px-4 py-3">
              풀고 싶은 문제
            </th>
            <SortHeader
              label="상태"
              active={sortKey === "status"}
              dir={sortDir}
              ariaSort={ariaSort("status")}
              onClick={() => handleSort("status")}
            />
            <SortHeader
              label="신청일"
              active={sortKey === "created"}
              dir={sortDir}
              ariaSort={ariaSort("created")}
              onClick={() => handleSort("created")}
            />
            <th scope="col" className="px-4 py-3 text-right">
              액션
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => {
            // 라벨·톤은 용어 SSOT(labels.ts)에서만 온다 — 필터 칩과 같은 문자열.
            const status = statusLabelOf(WAITLIST_STATUS_LABEL, item.status, "waitlist.status");
            return (
              <tr
                key={item.id}
                className="hover:bg-muted/50 border-t border-[color:var(--border)] align-top transition-colors duration-200 ease-out"
              >
                <td className="px-4 py-3 font-medium">{item.email}</td>
                <td className="px-4 py-3 text-xs text-[color:var(--text-secondary)]">
                  {item.tv_subscription}
                </td>
                <td className="px-4 py-3 text-xs text-[color:var(--text-secondary)]">
                  {item.exchange_capital}
                </td>
                <td className="px-4 py-3 text-xs text-[color:var(--text-secondary)]">
                  {item.pine_experience}
                </td>
                <td className="px-4 py-3">
                  <span className="line-clamp-3 block max-w-[280px] text-xs text-[color:var(--text-secondary)]">
                    {item.pain_point}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {/* v3 캐논 — pill 반경 폐기. 트레이딩 쪽과 같은 .chip 어휘로 그린다. */}
                  <span className={CHIP_TONE_CLASS[status.tone]}>{status.label}</span>
                </td>
                <td className="px-4 py-3 text-xs text-[color:var(--text-muted)]">
                  {formatDate(item.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  {item.status === "pending" ? (
                    <Button
                      type="button"
                      size="sm"
                      disabled={isApproving}
                      onClick={() => onApprove(item.id)}
                    >
                      {isApproving ? (
                        <span className="inline-flex items-center gap-1.5">
                          {/* 수제 SVG 대신 lucide 스피너 — 형제 컴포넌트 관례. */}
                          <Loader2 className="size-3 motion-safe:animate-spin" aria-hidden="true" />
                          전송 중…
                        </span>
                      ) : (
                        "승인 + 초대"
                      )}
                    </Button>
                  ) : (
                    <span
                      className="text-xs text-[color:var(--text-muted)]"
                      title={WAITLIST_ACTION_EMPTY_REASON[item.status]}
                    >
                      {EMPTY_CELL}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

interface SortHeaderProps {
  label: string;
  active: boolean;
  dir: SortDir;
  ariaSort: "ascending" | "descending" | "none";
  onClick: () => void;
}

function SortHeader({ label, active, dir, ariaSort, onClick }: SortHeaderProps) {
  return (
    <th scope="col" className="px-4 py-3" aria-sort={ariaSort}>
      <button
        type="button"
        onClick={onClick}
        className={
          "inline-flex items-center gap-1 transition hover:text-[color:var(--text-primary)] " +
          (active ? "text-[color:var(--primary)]" : "")
        }
      >
        <span>{label}</span>
        {active ? (
          dir === "asc" ? (
            <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
          )
        ) : (
          <ChevronsUpDown className="text-muted-foreground h-3.5 w-3.5" aria-hidden="true" />
        )}
      </button>
    </th>
  );
}
