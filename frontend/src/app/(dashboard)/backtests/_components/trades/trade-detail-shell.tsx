// 거래 내역 상세 page shell — C 디자인 언어 이식(S6). 리포트 헤더 + 거래 통계 + 거래 목록.
// /backtests/[id]/trades route 의 client-side 데이터 fetching + 레이아웃.
// 전 거래를 useAllBacktestTrades 로 1회 로드(200-cap 해소) — 헤더 건수와 표 행이 일치한다.
// 상태 라벨·톤은 S4 용어 SSOT(BACKTEST_STATUS_LABEL) → CHIP_TONE_CLASS 로 파생한다.
"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AlertTriangleIcon, CheckIcon, RefreshCwIcon } from "lucide-react";

import { BACKTEST_STATUS_LABEL } from "@/features/backtest/labels";
import { useBacktest, useAllBacktestTrades } from "@/features/backtest/hooks";
import type { TradeItem } from "@/features/backtest/schemas";
import { CHIP_TONE_CLASS } from "@/lib/labels";
import { StateBox } from "@/components/state-box";

import { TradeDetailTable } from "@/app/(dashboard)/backtests/_components/trades/trade-detail-table";
import { TradeStatsStrip } from "@/app/(dashboard)/backtests/_components/trades/trade-stats-strip";

const EMPTY_TRADES: readonly TradeItem[] = [];

export function TradeDetailShell({ id }: { id: string }) {
  const detail = useBacktest(id);
  const trades = useAllBacktestTrades(id, {
    enabled: detail.data?.status === "completed",
  });

  // RQ data 를 직접 dep 로 쓰지 않도록 items reference 를 memoize (H-1 정합).
  const items = useMemo<readonly TradeItem[]>(
    () => trades.data?.items ?? EMPTY_TRADES,
    [trades.data?.items],
  );

  if (detail.isLoading) {
    return <TradeDetailSkeleton />;
  }

  if (detail.isError || !detail.data) {
    return (
      <main className="page">
        <section className="card">
          <div className="card-body">
            <StateBox
              tone="failed"
              testId="trade-detail-error"
              icon={<AlertTriangleIcon />}
              title="백테스트 정보를 불러오지 못했습니다."
              body={
                detail.error
                  ? detail.error.message
                  : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."
              }
              code={`GET /api/v1/backtests/${id}`}
            >
              <button className="btn btn-ghost" type="button" onClick={() => detail.refetch()}>
                <RefreshCwIcon aria-hidden="true" />
                다시 시도
              </button>
            </StateBox>
          </div>
        </section>
      </main>
    );
  }

  const bt = detail.data;
  const tradeCount = trades.data?.total ?? items.length;
  // 라벨·톤은 S4 용어 SSOT 에서만 온다 (원시 enum 렌더 금지 — no-raw-enum-labels 가드).
  const { label: statusLabel, tone: statusTone, showCheckIcon } =
    BACKTEST_STATUS_LABEL[bt.status];

  return (
    <main className="page">
      {/* ===== 리포트 헤더 ===== */}
      <section className="card" aria-label="거래 내역 개요">
        <div className="report">
          <div>
            <h1 className="report-title">거래 내역</h1>
            <div className="report-meta">
              <span className="chip">{bt.id.slice(0, 8)}</span>
              <span className="chip">{bt.symbol}</span>
              <span className="chip">{bt.timeframe}</span>
              <span className={CHIP_TONE_CLASS[statusTone]}>
                {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                {statusLabel}
              </span>
              <span className="chip">{tradeCount}건</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
          <div className="report-actions">
            <Link className="btn" href={`/backtests/${id}`}>
              리포트로 이동
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 01 거래 통계 ===== */}
      <section className="section" aria-label="거래 통계">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 거래 통계
          </p>
          <h2 className="section-title">이 실행의 거래를 한 줄로</h2>
          <p className="section-desc">
            아래 값은 지금 로드된 거래 {items.length}건을 집계한 것입니다. 승패는 손익 부호로
            판정하고, 평균 보유는 진입과 청산 시각의 차이입니다.
          </p>
        </header>
        <TradeStatsStrip trades={items} />
      </section>

      {/* ===== 02 거래 목록 ===== */}
      <section className="section" aria-label="거래 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 목록
          </p>
          <h2 className="section-title">한 건씩 근거까지 확인하기</h2>
          <p className="section-desc">
            행을 누르면 그 거래의 진입·청산·성과 분해가 펼쳐집니다. 진입가와 청산가는 체결 기록
            원시값이고, 수수료는 그 위에 별도로 차감됩니다.
          </p>
          {trades.data?.truncated ? (
            <p className="section-desc" data-testid="trade-truncated-notice">
              전체 {tradeCount}건 중 상한까지만 로드했습니다. 나머지는 CSV 로 확인하세요.
            </p>
          ) : null}
        </header>
        <TradeDetailTable
          trades={items}
          isLoading={trades.isLoading}
          isError={trades.isError}
          errorMessage={trades.error?.message}
          endpoint={`GET /api/v1/backtests/${id}/trades`}
          onRetry={() => trades.refetch()}
          filenamePrefix={`backtest-${id.slice(0, 8)}`}
        />
      </section>
    </main>
  );
}

// 로딩 스켈레톤 — page.tsx Suspense fallback 과 shell isLoading 이 공유한다(중복 마크업 통합).
export function TradeDetailSkeleton() {
  return (
    <main className="page" aria-busy="true" data-testid="trade-detail-skeleton">
      <section className="card" aria-hidden="true">
        <div className="report">
          <div>
            <span className="sk" style={{ display: "block", width: 180, height: 30 }} />
            <div className="report-meta">
              {Array.from({ length: 5 }).map((_, i) => (
                <span key={i} className="sk" style={{ display: "block", width: 72, height: 26 }} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section" aria-hidden="true">
        <div className="kpi-row">
          {Array.from({ length: 4 }).map((_, i) => (
            <article key={i} className="card kpi">
              <span className="sk" style={{ display: "block", width: 88, height: 12 }} />
              <span className="sk" style={{ display: "block", width: 120, height: 30, marginTop: 12 }} />
            </article>
          ))}
        </div>
      </section>

      <section className="section" aria-hidden="true">
        <div className="card">
          <div className="table-wrap">
            <table className="trades">
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 11 }).map((__, j) => (
                      <td key={j}>
                        <span className="sk sk-cell" />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
