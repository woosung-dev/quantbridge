// Sprint 37 BL-183: Monte Carlo 요약 통계 테이블.
// fan chart 와 책임 분리 — 4 통계 (CI 95% 하한/상한, median final equity, MDD p95)
// 를 숫자 테이블로 노출. 사용자가 fan chart 만 보고 시각 추정하던 한계를 해소.
//
// LESSON-004: presentational component, render body 에서 ref/state 변경 없음.
// props (mcResult) → 파생 row 만 useMemo 없이 직접 계산 (4 row 라 비용 무시).

import type { MonteCarloResult } from "@/features/backtest/schemas";
import { formatCurrency, formatPercent } from "@/features/backtest/utils";

export interface MonteCarloSummaryTableProps {
  /** Monte Carlo 실행 결과. null/undefined 시 미실행 안내 표시. */
  readonly mcResult: MonteCarloResult | null | undefined;
}

interface SummaryRow {
  readonly label: string;
  readonly value: string;
  readonly title: string;
}

export function MonteCarloSummaryTable({
  mcResult,
}: MonteCarloSummaryTableProps) {
  if (mcResult == null) {
    return (
      <section
        aria-label="Monte Carlo 요약 통계"
        className="rounded-xl border bg-muted/30 px-4 py-3"
      >
        <p className="text-xs text-muted-foreground">
          Monte Carlo 미실행
        </p>
      </section>
    );
  }

  const rows: readonly SummaryRow[] = [
    {
      label: "CI 95% 하한 (final equity)",
      value: `${formatCurrency(mcResult.ci_lower_95)} USDT`,
      title:
        "1000 시뮬레이션 final equity 의 5 percentile — 하위 5% 시나리오 컷오프",
    },
    {
      label: "CI 95% 상한 (final equity)",
      value: `${formatCurrency(mcResult.ci_upper_95)} USDT`,
      title:
        "1000 시뮬레이션 final equity 의 95 percentile — 상위 5% 시나리오 컷오프",
    },
    {
      label: "Median final equity",
      value: `${formatCurrency(mcResult.median_final_equity)} USDT`,
      title: "1000 시뮬레이션 final equity 의 중앙값 (50 percentile)",
    },
    {
      label: "MDD p95 (Maximum Drawdown 95 percentile)",
      value: formatPercent(mcResult.max_drawdown_p95, 2),
      title:
        "최대 낙폭 95 percentile — 시뮬레이션 중 95% 가 이보다 작은 손실폭을 경험",
    },
  ];

  return (
    <section
      aria-label="Monte Carlo 요약 통계"
      className="rounded-xl border bg-muted/30 px-4 py-3"
    >
      <header className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium">Monte Carlo 요약 통계</h3>
        <span className="text-xs text-muted-foreground">
          samples {mcResult.samples.toLocaleString("en-US")}
        </span>
      </header>
      <table className="w-full text-xs">
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.label}
              className="border-b border-border/40 last:border-b-0"
            >
              <th
                scope="row"
                className="py-1.5 pr-2 text-left font-normal text-muted-foreground"
                title={row.title}
              >
                {row.label}
              </th>
              <td className="py-1.5 text-right font-mono font-medium tabular-nums">
                {row.value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
