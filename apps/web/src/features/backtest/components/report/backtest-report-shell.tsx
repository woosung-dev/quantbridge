"use client";

// 백테스트 리포트 IA — variant-c.html 섹션 흐름 이식. 상단→하단 번호 섹션 단일 스크롤.
// 01 요약 · 02 자산 곡선 · 03 상세 지표 · 04 거래 내역 (여기까지 variant-c 순서) ·
// 05 거래 분석 · 06 심화 분석 · 07 런업&드로다운 · 08 스트레스 테스트 (variant-c 에 없는 현행
//   분석 기능을 같은 .section/.eyebrow/.card 언어로 보존 배치) ·
// 09 실행 조건 · 10 다음 단계 (variant-c 마무리 순서 유지).
// 이전 shadcn Tabs 5탭 IA 를 위 번호 섹션 구조로 재편했다.
// trades 는 useAllBacktestTrades(200-cap 해소) 1회 로드 후 전 섹션 공유.

import { useEffect, type ReactNode } from "react";
import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";
import { useAllBacktestTrades } from "@/features/backtest/hooks";
import type { BacktestDetail } from "@/features/backtest/schemas";

import { AssumptionsCard } from "@/features/backtest/components/assumptions-card";
import { StressTestPanel } from "@/features/backtest/components/stress-test-panel";
import { DetailedResultsSection } from "@/features/backtest/components/report/detailed-results-section";
import { KeyStatsStrip } from "@/features/backtest/components/report/key-stats-strip";
import { MetricGroupsSection } from "@/features/backtest/components/report/metric-groups-section";
import { PerformanceChart } from "@/features/backtest/components/report/performance-chart";
import { ReportNextSteps } from "@/features/backtest/components/report/report-next-steps";
import { RunupDrawdownSection } from "@/features/backtest/components/report/runup-drawdown-section";
import { TradeAnalyticsSection } from "@/features/backtest/components/report/trade-analytics-section";
import { TradeLedgerTable } from "@/features/backtest/components/report/trade-ledger-table";

interface BacktestReportShellProps {
  backtest: BacktestDetail;
  currentId: string;
}

const STRESS_ANCHOR = "stress-test";

function Section({
  num,
  eyebrow,
  title,
  desc,
  children,
  id,
  ariaLabel,
}: {
  num: string;
  eyebrow: string;
  title: string;
  desc: string;
  children: ReactNode;
  id?: string;
  ariaLabel: string;
}) {
  // sticky 상단바 60px + 여유 16px = 앵커 스크롤 보정 76px.
  return (
    <section className="section scroll-mt-[76px]" aria-label={ariaLabel} id={id}>
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">{num}</span> {eyebrow}
        </p>
        <h2 className="section-title">{title}</h2>
        <p className="section-desc">{desc}</p>
      </header>
      {children}
    </section>
  );
}

export function BacktestReportShell({ backtest: bt, currentId }: BacktestReportShellProps) {
  const trades = useAllBacktestTrades(currentId);
  const tradeItems = trades.data?.items;
  const truncated = trades.data?.truncated ?? false;

  // 리포트는 React Query 완료 뒤에 삽입되어, 문서 로드 시점의 네이티브 fragment
  // 위치결정이 이미 끝날 수 있다. 마운트 뒤 해시 대상이 생긴 시점에 한 번 재조정한다.
  //
  // ★vercel-react-best-practices 대조 (2026-08-10) — 이 효과는 아래 둘에 걸리지 않는다.
  //   `rerender-derived-state-no-effect` 는 **effect 안에서 setState 로 파생값을 만드는 것**을
  //   막는다. 여기는 state 를 만들지 않고 DOM 만 만진다(스크롤은 파생값이 아니다).
  //   `rerender-move-effect-to-event` 는 상호작용 로직을 다루는데, 이것은 상호작용이 아니라
  //   **최초 진입 URL** 이라는 외부 입력을 한 번 맞추는 것이라 이벤트 핸들러가 될 자리가 없다.
  //   ★이 효과를 없앨 수 있는 조건은 하나뿐이다 — **대상 엘리먼트가 최초 HTML 에 들어 있는 것**.
  //   즉 상세 라우트를 서버에서 렌더(또는 prefetch + 하이드레이션)해야 한다. 클라이언트
  //   Suspense 로 바꾸는 것만으로는 안 된다: fallback 뒤에 리포트를 꽂는 구조는 여전히
  //   fragment 위치결정 이후이기 때문이다(codex G6 가 내 첫 주석의 이 부분을 반증했다) → [BL-681].
  useEffect(() => {
    const anchor = window.location.hash.slice(1);
    if (!anchor) return;
    document.getElementById(anchor)?.scrollIntoView();
  }, []);

  const buyAndHoldPoints =
    bt.metrics?.buy_and_hold_curve?.map(([timestamp, value]) => ({
      timestamp,
      value,
    })) ?? null;

  if (!bt.metrics) {
    return null;
  }
  const metrics = bt.metrics;

  return (
    <div data-testid="backtest-report-shell">
      {/* ===== 01 요약 ===== */}
      <Section
        num="01"
        eyebrow="요약"
        title="성과 요약"
        desc="수수료와 슬리피지를 반영한 뒤의 값입니다."
        ariaLabel="성과 요약"
        id="key-stats"
      >
        <KeyStatsStrip metrics={metrics} config={bt.config} />
      </Section>

      {/* ===== 02 자산 곡선 ===== */}
      {bt.equity_curve && bt.equity_curve.length > 0 ? (
        <Section
          num="02"
          eyebrow="자산 곡선"
          title="전략 대 벤치마크"
          desc="전략 자산 곡선과 같은 기간 매수 후 보유 곡선을 겹쳐 봅니다. 아래 띠는 같은 x축의 낙폭입니다."
          ariaLabel="자산 곡선"
          id="benchmark"
        >
          <PerformanceChart
            currentId={currentId}
            equityCurve={bt.equity_curve}
            trades={tradeItems}
            initialCapital={bt.initial_capital}
            timeframe={bt.timeframe}
            mddExceedsCapital={metrics.mdd_exceeds_capital ?? null}
            buyAndHoldCurve={buyAndHoldPoints}
          />
        </Section>
      ) : null}

      {/* ===== 03 상세 지표 ===== */}
      <Section
        num="03"
        eyebrow="상세 지표"
        title="상세 지표"
        desc="수익성, 위험, 거래 통계, 실행 품질 네 묶음으로 나눠 봅니다. 값이 없는 지표는 대시로 표시합니다."
        ariaLabel="상세 지표"
        id="metrics"
      >
        <MetricGroupsSection
          metrics={metrics}
          buyAndHoldCurve={buyAndHoldPoints}
          leverage={bt.config?.leverage}
        />
      </Section>

      {/* ===== 04 거래 내역 ===== */}
      <Section
        num="04"
        eyebrow="거래 내역"
        title={`체결된 거래 ${metrics.num_trades}건`}
        desc="최근 순으로 정렬한 미리보기입니다. 전체 원장과 런업·드로다운 분해는 상세 보기에서 확인합니다."
        ariaLabel="거래 내역"
        id="trades"
      >
        {trades.isLoading ? (
          <TradeSkeleton />
        ) : trades.isError ? (
          <div className="card">
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="report-trades-error"
                icon={<AlertTriangleIcon />}
                title="거래 기록을 불러오지 못했습니다."
                body={
                  trades.error
                    ? trades.error.message
                    : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."
                }
                code={`GET /api/v1/backtests/${currentId}/trades`}
              >
                <button className="btn btn-ghost" type="button" onClick={() => trades.refetch()}>
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          </div>
        ) : (
          <TradeLedgerTable
            trades={tradeItems ?? []}
            filenamePrefix={`backtest-${currentId.slice(0, 8)}`}
          />
        )}
      </Section>

      {/* ===== 05 거래 분석 (보존) ===== */}
      <Section
        num="05"
        eyebrow="거래 분석"
        title="거래 분포와 수익 분포"
        desc="체결된 거래를 승패와 손익 크기로 나눠 봅니다."
        ariaLabel="거래 분석"
        id="distributions"
      >
        <div className="card">
          <div className="card-body">
            <TradeAnalyticsSection
              metrics={metrics}
              trades={tradeItems ?? []}
              truncated={truncated}
            />
          </div>
        </div>
      </Section>

      {/* ===== 06 심화 분석 (보존) ===== */}
      <Section
        num="06"
        eyebrow="심화 분석"
        title="수익 구조와 벤치마킹"
        desc="순손익 분해, 전략 대 매수 후 보유 범위, 월별 수익 분포를 봅니다."
        ariaLabel="심화 분석"
        id="profit-structure"
      >
        <DetailedResultsSection
          metrics={metrics}
          equityCurve={bt.equity_curve ?? null}
          buyAndHoldCurve={buyAndHoldPoints}
          initialCapital={bt.initial_capital}
          trades={tradeItems}
          tradesTruncated={truncated}
        />
      </Section>

      {/* ===== 07 런업 & 드로다운 (보존) ===== */}
      <Section
        num="07"
        eyebrow="런업 & 드로다운"
        title="상승폭과 낙폭 에피소드"
        desc="에피소드별 상승폭과 낙폭, 지속 기간과 회복을 봅니다. 인트라바 값은 봉 고저 근사입니다."
        ariaLabel="런업 드로다운"
        id="runup-drawdown"
      >
        <div className="card">
          <div className="card-body">
            <RunupDrawdownSection metrics={metrics} initialCapital={bt.initial_capital} />
          </div>
        </div>
      </Section>

      {/* ===== 08 스트레스 테스트 (보존) ===== */}
      <Section
        num="08"
        eyebrow="스트레스 테스트"
        title="가정을 흔들어 보기"
        desc="몬테카를로·워크포워드·비용 민감도·파라미터 안정성으로 결과의 견고함을 확인합니다."
        ariaLabel="스트레스 테스트"
        id={STRESS_ANCHOR}
      >
        <div className="card">
          <div className="card-body">
            <StressTestPanel backtestId={bt.id} />
          </div>
        </div>
      </Section>

      {/* ===== 09 실행 조건 ===== */}
      <Section
        num="09"
        eyebrow="실행 조건"
        title="가정과 데이터 출처"
        desc="숫자를 믿으려면 조건을 먼저 봐야 합니다. 이 실행에 적용된 가정을 그대로 적습니다."
        ariaLabel="실행 조건"
        id="assumptions"
      >
        <AssumptionsCard
          initialCapital={bt.initial_capital}
          config={bt.config}
          totalFees={metrics.total_fees}
          totalSlippage={metrics.total_slippage}
          totalFunding={metrics.total_funding}
          fundingDataIncomplete={metrics.funding_data_incomplete}
          periodStart={bt.period_start}
          periodEnd={bt.period_end}
          ranAt={bt.completed_at}
          warnings={bt.warnings}
        />
      </Section>

      {/* ===== 10 다음 단계 ===== */}
      <Section
        num="10"
        eyebrow="다음 단계"
        title="이 결과로 무엇을 할까요?"
        desc="한 번의 백테스트는 가설 하나입니다. 아래 순서대로 검증 강도를 올리는 것을 권합니다."
        ariaLabel="다음 단계"
        id="next-steps"
      >
        <ReportNextSteps stressTestAnchorId={STRESS_ANCHOR} />
      </Section>
    </div>
  );
}

// 거래 미리보기 스켈레톤 — 프로토타입 aria-busy tbody 관례(.sk .sk-cell).
function TradeSkeleton() {
  return (
    <div className="card" aria-busy="true" data-testid="report-trades-skeleton">
      <div className="table-wrap">
        <table className="trades">
          <tbody>
            {Array.from({ length: 6 }).map((_, i) => (
              <tr key={i}>
                {Array.from({ length: 10 }).map((__, j) => (
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
  );
}
