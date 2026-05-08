"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function StrategyTable({ items }: { items: StrategyListItem[] }) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white">
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
                className="cursor-pointer border-t border-[color:var(--border)] transition-colors duration-150 hover:bg-slate-50/60"
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
                  <Link href={`/strategies/${s.id}/edit`} className="text-[color:var(--primary)] hover:underline">
                    편집 →
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
