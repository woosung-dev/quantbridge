"use client";

import dynamic from "next/dynamic";
import { TableScrollRegion } from "@/components/table-scroll-region";
import { formatCurrency, formatDateTime, formatPercent } from "@/features/backtest/utils";
import { describeSharpe } from "@/features/backtest/sharpe-convention";
import type { PythonRun } from "../schemas";

const EquityChart = dynamic(
  () =>
    import("@/features/backtest/components/charts/equity-chart-v2").then(
      (module) => module.EquityChartV2,
    ),
  {
    ssr: false,
    loading: () => <p className="p-4 text-muted-foreground">자산 곡선 불러오는 중…</p>,
  },
);
const EMPTY_TRADES = [] as const;
export const PYTHON_RUN_LABEL = {
  pending: "대기 중",
  running: "실행 중",
  completed: "완료",
  failed: "실패",
  cancelled: "취소됨",
} as const;
const DIRECTION_LABEL = { long: "매수", short: "매도" } as const;
const TRADE_STATUS_LABEL = { open: "보유 중", closed: "청산" } as const;

function metric(value: string | null, percent = false) {
  if (value === null) return "—";
  return percent ? formatPercent(Number(value)) : formatCurrency(Number(value));
}

export function RunResult({
  run,
  isCancelling,
  cancelError,
  onCancel,
}: {
  run: PythonRun;
  isCancelling: boolean;
  cancelError: string | null;
  onCancel: () => void;
}) {
  const active = run.status === "pending" || run.status === "running";
  const result = run.result;
  const sharpe = describeSharpe(
    result?.metrics.sharpe_convention,
    result?.metrics.sharpe_ratio == null ? null : Number(result.metrics.sharpe_ratio),
  );
  return (
    <section className="card" aria-label="Python 실행 결과">
      <div className="card-head">
        <div>
          <h2 className="card-title">실행 결과</h2>
          <p className="card-sub">
            {run.request.symbol} 무기한 · {run.request.timeframe} · {formatDateTime(run.created_at)}{" "}
            UTC
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip" role="status">
            {PYTHON_RUN_LABEL[run.status]}
          </span>
          {active ? (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onCancel}
              disabled={isCancelling}
            >
              {isCancelling ? "취소 요청 중…" : "실행 취소"}
            </button>
          ) : null}
        </div>
      </div>
      <div className="card-body space-y-5">
        <p className="text-sm text-muted-foreground">
          평가 기간 {formatDateTime(run.request.period_start)} ~{" "}
          {formatDateTime(run.request.period_end)} UTC (종료 미포함)
          <br />
          초기 자본 {formatCurrency(Number(run.request.initial_capital))} USDT · 편도 수수료{" "}
          {formatPercent(Number(run.request.fees), 3)} · 슬리피지{" "}
          {formatPercent(Number(run.request.slippage), 3)}
        </p>
        <p className="strip-note">
          <span>
            <strong>단일 백테스트 · 후보 검증 미완료.</strong> 이 결과만으로 선별 기준 통과나 미래
            수익을 판단하지 않습니다. 이 화면에서는 자동매매를 실행하지 않습니다.
          </span>
        </p>
        <p className="break-all text-sm text-muted-foreground">
          실행 버전 <code>{run.version_id}</code> · 실행 ID <code>{run.id}</code>
        </p>
        {active ? (
          <p className="text-sm text-muted-foreground">
            2초마다 상태를 확인합니다. 완료되면 지표와 거래 내역이 표시됩니다.
          </p>
        ) : null}
        {run.error ? (
          <p className="field-error" role="alert">
            {run.error}
          </p>
        ) : null}
        {cancelError ? (
          <p className="field-error" role="alert">
            {cancelError}
          </p>
        ) : null}
        {result && run.status === "completed" ? (
          <>
            <dl className="grid min-w-0 grid-cols-2 gap-5 md:grid-cols-4">
              <div>
                <dt className="text-sm text-muted-foreground">비용 차감 수익률</dt>
                <dd className="mono mt-1 text-xl">{metric(result.metrics.total_return, true)}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">최대 낙폭</dt>
                <dd className="mono mt-1 text-xl">{metric(result.metrics.max_drawdown, true)}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">수익 팩터</dt>
                <dd className="mono mt-1 text-xl">{metric(result.metrics.profit_factor)}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">완료 거래</dt>
                <dd className="mono mt-1 text-xl">{result.metrics.num_trades}회</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">샤프</dt>
                <dd className="mono mt-1" title={sharpe.foot}>
                  {sharpe.display}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">수수료 (USDT)</dt>
                <dd className="mono mt-1">{metric(result.metrics.total_fees)}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">슬리피지 (USDT)</dt>
                <dd className="mono mt-1">{metric(result.metrics.total_slippage)}</dd>
              </div>
              <div>
                <dt
                  className="text-sm text-muted-foreground"
                  title="양수는 지불, 음수는 수취입니다"
                >
                  펀딩 (USDT)
                </dt>
                <dd className="mono mt-1">{metric(result.metrics.total_funding ?? null)}</dd>
              </div>
            </dl>
            {result.equity_curve.length > 0 ? (
              <div className="min-w-0">
                <h3 className="card-title mb-3">자산 곡선</h3>
                <EquityChart
                  equityCurve={result.equity_curve.map((point) => ({
                    ...point,
                    value: Number(point.value),
                  }))}
                  trades={EMPTY_TRADES}
                  initialCapital={Number(run.request.initial_capital)}
                  timeframe={run.request.timeframe}
                />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">자산 곡선 데이터가 없습니다.</p>
            )}
            <div>
              <h3 className="card-title mb-3">거래 내역</h3>
              {result.trades.length === 0 ? (
                <p className="text-sm text-muted-foreground">발생한 거래가 없습니다.</p>
              ) : (
                <TableScrollRegion label="Python 백테스트 거래 내역">
                  <table className="trades">
                    <thead>
                      <tr>
                        <th scope="col">거래</th>
                        <th scope="col">방향</th>
                        <th scope="col">상태</th>
                        <th scope="col">진입 봉</th>
                        <th scope="col">청산 봉</th>
                        <th scope="col">진입가</th>
                        <th scope="col">청산가</th>
                        <th scope="col">손익 (USDT)</th>
                        <th scope="col">거래 비용</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trades.slice(0, 200).map((trade) => (
                        <tr key={trade.trade_index}>
                          <td className="mono">{trade.trade_index + 1}</td>
                          <td>{DIRECTION_LABEL[trade.direction]}</td>
                          <td>{TRADE_STATUS_LABEL[trade.status]}</td>
                          <td className="mono">{trade.entry_bar_index}</td>
                          <td className="mono">{trade.exit_bar_index ?? "—"}</td>
                          <td className="mono">{metric(trade.entry_price)}</td>
                          <td className="mono">{metric(trade.exit_price)}</td>
                          <td className="mono">{metric(trade.pnl)}</td>
                          <td className="mono">{metric(trade.fees)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableScrollRegion>
              )}
              {result.trades.length > 200 ? (
                <p className="text-sm text-muted-foreground">
                  전체 {result.trades.length}건 중 앞의 200건을 표시합니다.
                </p>
              ) : null}
            </div>
            <details>
              <summary className="cursor-pointer text-sm text-muted-foreground">
                데이터·코드 재현 정보
              </summary>
              <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-md border p-3 font-mono text-xs">
                {JSON.stringify(result.provenance, null, 2)}
              </pre>
            </details>
          </>
        ) : null}
      </div>
    </section>
  );
}
