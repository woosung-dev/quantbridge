"use client";

import Link from "next/link";
import { ArrowRightIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function StrategyTable({ items }: { items: StrategyListItem[] }) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-card">
      <table className="w-full text-sm">
        <thead className="bg-[color:var(--bg-alt)] text-xs uppercase tracking-wide text-[color:var(--text-secondary)]">
          <tr>
            <th scope="col" className="px-4 py-3 text-left">이름</th>
            <th scope="col" className="px-4 py-3 text-left">심볼 / TF</th>
            <th scope="col" className="px-4 py-3 text-left">상태</th>
            <th scope="col" className="px-4 py-3 text-left">수정</th>
            <th scope="col" className="sr-only">액션</th>
          </tr>
        </thead>
        <tbody>
          {items.map((s) => {
            const meta = PARSE_STATUS_META[s.parse_status];
            return (
              <tr
                key={s.id}
                className="cursor-pointer border-t border-[color:var(--border)] transition-colors duration-150 hover:bg-muted"
              >
                <td className="px-4 py-3">
                  <Link href={`/strategies/${s.id}/edit`} className="font-medium hover:text-[color:var(--primary)]">
                    {s.name}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[color:var(--text-muted)]">
                  {s.symbol ?? "—"} · {s.timeframe ?? "—"} · v{s.pine_version.slice(1)}
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" data-tone={meta.tone}>{meta.label}</Badge>
                </td>
                <td className="px-4 py-3 text-xs text-[color:var(--text-muted)]">
                  {new Date(s.updated_at).toLocaleString("ko-KR")}
                </td>
                <td className="px-4 py-3 text-right">
                  {/* Sprint 62 T-2 (BL-357): 모바일 viewport 에서 touch hit area 44pt 강제.
                      텍스트 링크 38x16 → min-h-11 px-3. 데스크톱은 md: 분기 복원. */}
                  <Link
                    href={`/strategies/${s.id}/edit`}
                    className="inline-flex min-h-11 items-center gap-1 px-3 py-2 text-[color:var(--primary)] hover:underline md:px-0 md:py-0"
                  >
                    편집
                    <ArrowRightIcon aria-hidden="true" className="size-3.5" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
