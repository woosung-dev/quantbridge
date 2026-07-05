"use client";

// 상세 결과 서브탭 공용 메트릭 테이블 — TV "메트릭 | 전체" 2컬럼 + null 정책 코드화
// nullPolicy: "dash" = "—" 표시 / "hide" = 행 제거 (Surface Trust — 가짜 값 렌더 금지)

import type { ReactNode } from "react";

export interface MetricRowSpec {
  label: string;
  /** null = 데이터 없음 → nullPolicy 적용. */
  value: string | null;
  /** 라벨 옆 보조 힌트 (예: "(bar 근사)", "(bar 수익률 기준)"). */
  hint?: string;
  tone?: "bullish" | "bearish" | "neutral";
  nullPolicy?: "dash" | "hide";
}

function toneClass(tone: MetricRowSpec["tone"]): string {
  if (tone === "bullish") return "text-[color:var(--bullish)]";
  if (tone === "bearish") return "text-[color:var(--bearish)]";
  return "text-foreground";
}

export function MetricTable({
  rows,
  caption,
}: {
  rows: readonly MetricRowSpec[];
  caption?: ReactNode;
}) {
  const visible = rows.filter(
    (r) => r.value !== null || (r.nullPolicy ?? "dash") === "dash",
  );
  if (visible.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        표시할 메트릭이 없습니다
      </p>
    );
  }
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[color:var(--border)] text-left text-xs text-muted-foreground">
            <th className="py-2 font-medium">메트릭</th>
            <th className="py-2 text-right font-medium">전체</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => (
            <tr
              key={row.label}
              className="border-b border-[color:var(--border)] last:border-b-0"
            >
              <td className="py-2.5 text-[color:var(--text-secondary)]">
                {row.label}
                {row.hint ? (
                  <span className="ml-1 text-xs text-muted-foreground">
                    {row.hint}
                  </span>
                ) : null}
              </td>
              <td
                className={`py-2.5 text-right font-mono tabular-nums ${toneClass(row.tone)}`}
              >
                {row.value ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {caption ? (
        <p className="mt-2 text-xs text-muted-foreground">{caption}</p>
      ) : null}
    </div>
  );
}
