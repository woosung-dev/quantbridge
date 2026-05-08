// Sprint 43 W15 — Waitlist 신청자 list table (sort + status badge + approve action).
// W6 strategy-table 패턴 차용. 정렬 키 = email/created/status, aria-sort 적용.
"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import type {
  WaitlistApplicationResponse,
  WaitlistStatus,
} from "@/features/waitlist/schemas";

type SortKey = "email" | "created" | "status";
type SortDir = "asc" | "desc";

const STATUS_BADGE: Record<WaitlistStatus, string> = {
  pending: "bg-amber-100 text-amber-900",
  invited: "bg-blue-100 text-blue-900",
  joined: "bg-emerald-100 text-emerald-900",
  rejected: "bg-gray-200 text-gray-800",
};

const STATUS_LABEL: Record<WaitlistStatus, string> = {
  pending: "대기중",
  invited: "초대됨",
  joined: "가입완료",
  rejected: "거절",
};

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

export function WaitlistTable({
  items,
  onApprove,
  isApproving,
}: WaitlistTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("created");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortKey === "email") return a.email.localeCompare(b.email) * dir;
      if (sortKey === "status")
        return (STATUS_ORDER[a.status] - STATUS_ORDER[b.status]) * dir;
      // created
      return (
        (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) *
        dir
      );
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
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white">
      <table className="w-full text-left text-sm" role="table">
        <thead className="bg-[color:var(--bg-alt)] text-xs uppercase tracking-wide text-[color:var(--text-secondary)]">
          <tr>
            <SortHeader
              label="이메일"
              active={sortKey === "email"}
              dir={sortDir}
              ariaSort={ariaSort("email")}
              onClick={() => handleSort("email")}
            />
            <th scope="col" className="px-4 py-3">
              TV
            </th>
            <th scope="col" className="px-4 py-3">
              자본
            </th>
            <th scope="col" className="px-4 py-3">
              Pine
            </th>
            <th scope="col" className="px-4 py-3">
              Pain Point
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
          {sorted.map((item) => (
            <tr
              key={item.id}
              className="border-t border-[color:var(--border)] align-top hover:bg-[color:var(--bg-alt)]"
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
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[item.status]}`}
                >
                  {STATUS_LABEL[item.status]}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-[color:var(--text-tertiary)]">
                {new Date(item.created_at).toLocaleDateString("ko-KR")}
              </td>
              <td className="px-4 py-3 text-right">
                {item.status === "pending" ? (
                  <Button
                    type="button"
                    size="sm"
                    disabled={isApproving}
                    onClick={() => onApprove(item.id)}
                  >
                    {isApproving ? "전송 중…" : "승인 + 초대"}
                  </Button>
                ) : (
                  <span className="text-xs text-[color:var(--text-tertiary)]">
                    —
                  </span>
                )}
              </td>
            </tr>
          ))}
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
        <span aria-hidden="true" className="text-[10px]">
          {active ? (dir === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </button>
    </th>
  );
}
