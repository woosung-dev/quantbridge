"use client";

// 워크스페이스 대시보드 — C 디자인 언어 이식 (S7). 프로토타입 screen-02 의 시맨틱 CSS 를
// 소비하되, 스키마가 받치는 값만 그린다(캐논 §4.9). 최근 실행은 백테스트·최적화 원장을 함께
// 보이고, 전략 성과는 목록의 latest_backtest projection을 재사용한다.
//  - 손익 KPI 는 라이브 세션 집계의 "실현" 손익이며, WS ticker 기반 미실현 추정치는 foot에만 부기한다.
//  - 전략 §04 는 수명주기 칩을 그리지 않는다(schemas.ts 에 draft/validated/deployed 0건).
// 데이터 흐름은 S3 셸과의 중복 페치를 걷어냈다(주문 페치 제거 → transition-toast 이중 발화 차단,
// 카운트는 목록 쿼리의 total 로 파생 → 코크핏당 도메인 쿼리 1개). 상세는 context-notes 참조.

import { useMemo } from "react";
import Link from "next/link";
import { PlusIcon, RefreshCwIcon } from "lucide-react";

import { InfoIcon } from "@/components/info-icon";
import { StateBox } from "@/components/state-box";
import { StatValue } from "@/components/stat-value";
import type { ChartPoint } from "@/components/charts/trading-chart";
import { useBacktests } from "@/features/backtest/hooks";
import { BACKTEST_STATUS_LABEL } from "@/features/backtest/labels";
import type { BacktestSummary } from "@/features/backtest/schemas";
import { formatDateTime, formatPercent } from "@/features/backtest/utils";
import { describeSharpe } from "@/features/backtest/sharpe-convention";
// BL-662 — 배럴(`@/features/live-sessions`)이 아니라 직접 경로로 받는다. 이 화면은 훅만 쓰고
// 배럴이 함께 내보내는 세션 컴포넌트 4종을 하나도 렌더하지 않는다.
// ★`useUnrealizedPnlEstimate` 는 `hooks` 가 아니라 `unrealized` 에 있다(배럴이 두 파일을 합친다).
import { useLiveSessions, useLiveSessionsAggregate } from "@/features/live-sessions/hooks";
import { useUnrealizedPnlEstimate } from "@/features/live-sessions/unrealized";
import { useStrategies } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { useOptimizationRuns } from "@/features/optimizer/hooks";
import { OPTIMIZATION_STATUS_LABEL } from "@/features/optimizer/labels";
import type { OptimizationRunResponse } from "@/features/optimizer/schemas";
// BL-662 — 같은 이유. `@/features/trading` 배럴은 패널·다이얼로그 5종을 함께 내보낸다.
import { useExchangeAccounts } from "@/features/trading/hooks";
// BL-458 — 출처 어휘 SSOT. 블로터 칩·세션 상세 칩과 같은 두 단어를 쓴다.
import {
  ORDER_REALIZED_PNL_SOURCE_HINT,
  ORDER_REALIZED_PNL_SOURCE_LABEL,
} from "@/features/trading/labels";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

import { WorkspaceEquityCard } from "./workspace-equity-card";

const RECENT_RUNS_LIMIT = 8;
const STRATEGY_FETCH_LIMIT = 100;
const RUNS_ENDPOINT = "GET /api/v1/backtests";
// ★실제 경로다 — `main.py:428` 이 optimizer 라우터를 `/api/v1` 프리픽스로 마운트하고
//   `optimizer/router.py:97` 이 `/runs` 를 낸다. 2026-08-30 까지 여기 적힌 값은
//   `/api/v1/optimizations` 였는데 **그런 경로는 없다** — 장애 때 사람을 엉뚱한 곳으로 보냈다.
const OPTIMIZATION_RUNS_ENDPOINT = "GET /api/v1/optimizer/runs";
const METER_CAP_PCT = 150;
const RECENT_RUN_TYPE_LABEL = {
  backtest: "백테스트",
  optimization: "최적화",
} as const;

type RecentRun =
  | { type: "backtest"; createdAt: string; run: BacktestSummary }
  | { type: "optimization"; createdAt: string; run: OptimizationRunResponse };

/** 부호 + 천단위 + 소수 2자리. USDT 이므로 통화 기호를 붙이지 않는다. */
function formatSignedUsd(n: number): string {
  const abs = Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}${abs}`;
}

export function DashboardCockpit() {
  const sessionsQ = useLiveSessions();
  const sessionItems = sessionsQ.data?.items;
  const activeSessions = useMemo(
    () => (sessionItems ?? []).filter((s) => s.is_active),
    [sessionItems],
  );
  const agg = useLiveSessionsAggregate(activeSessions);
  const unrealized = useUnrealizedPnlEstimate(activeSessions);

  const accountsQ = useExchangeAccounts();
  // 목록 쿼리 하나로 §04 전략 목록 + 실행표의 전략명 매핑 + KPI 카운트(.total)를 모두 얻는다.
  const strategyListQ = useStrategies({
    limit: STRATEGY_FETCH_LIMIT,
    offset: 0,
    is_archived: false,
  });
  // 실행표 + 백테스트 KPI 카운트(.total). 별도 count 쿼리를 두지 않는다.
  const backtestsQ = useBacktests({ limit: RECENT_RUNS_LIMIT, offset: 0 });
  const optimizationsQ = useOptimizationRuns({ limit: RECENT_RUNS_LIMIT, offset: 0 });

  const accounts = accountsQ.data?.length ?? 0;
  const strategyItems = useMemo<readonly StrategyListItem[]>(
    () => strategyListQ.data?.items ?? [],
    [strategyListQ.data?.items],
  );
  const strategyCount = strategyListQ.data?.total ?? 0;
  const backtestTotal = backtestsQ.data?.total ?? 0;
  const backtestItems = useMemo<readonly BacktestSummary[]>(
    () => backtestsQ.data?.items ?? [],
    [backtestsQ.data?.items],
  );
  const optimizationItems = useMemo<readonly OptimizationRunResponse[]>(
    () => optimizationsQ.data?.items ?? [],
    [optimizationsQ.data?.items],
  );
  const recentRuns = useMemo<readonly RecentRun[]>(() => {
    const merged: RecentRun[] = [
      ...backtestItems.map((run) => ({
        type: "backtest" as const,
        createdAt: run.created_at,
        run,
      })),
      ...optimizationItems.map((run) => ({
        type: "optimization" as const,
        createdAt: run.created_at,
        run,
      })),
    ];
    return merged
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, RECENT_RUNS_LIMIT);
  }, [backtestItems, optimizationItems]);

  const strategyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of strategyItems) map.set(s.id, s.name);
    return map;
  }, [strategyItems]);

  const equityData = useMemo<ChartPoint[]>(
    () => agg.mergedEquityCurve.map((p) => ({ time: p.time, value: p.value })),
    [agg.mergedEquityCurve],
  );

  const pnlToneClass = agg.totalRealizedPnl > 0 ? "pos" : agg.totalRealizedPnl < 0 ? "neg" : "";

  return (
    <main className="page">
      {/* ===== 워크스페이스 헤더 ===== */}
      <section className="card rise d1" aria-label="워크스페이스 개요">
        <div className="report">
          <div>
            <h1 className="report-title">워크스페이스</h1>
            <div className="report-meta">
              <span className={accountsQ.isError ? "chip warn" : "chip"}>
                {accountsQ.isError
                  ? "거래소 확인 불가"
                  : accounts > 0
                    ? `거래소 ${accounts}개 연결`
                    : "거래소 미등록"}
              </span>
              <span className="chip">
                활성 세션 {sessionsQ.isError ? "확인 불가" : activeSessions.length}
              </span>
            </div>
          </div>
          <div className="report-actions">
            <Link className="btn" href="/strategies/new">
              <PlusIcon aria-hidden="true" />새 전략
            </Link>
            <Link className="btn btn-primary" href="/backtests/new">
              <PlusIcon aria-hidden="true" />새 백테스트
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 01 현황 ===== */}
      <section className="section rise d2" aria-label="워크스페이스 현황">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 현황
          </p>
          <h2 className="section-title">지금 워크스페이스 상태</h2>
          <p className="section-desc">
            무엇을 만들어 뒀고, 데모 세션이 지금 얼마를 실현했는지 네 가지로 봅니다. 숫자는 각
            원장이 보고한 값을 그대로 받아 적습니다.
          </p>
        </header>

        <div className="kpi-row">
          <article className="card kpi">
            <p className="kpi-label">전략</p>
            <p className="kpi-value mono" data-testid="kpi-strategies">
              <StatValue isError={strategyListQ.isError} isPending={strategyListQ.isPending}>
                {strategyCount}
              </StatValue>
            </p>
            <p className="kpi-foot">아카이브 제외 등록 전략 수입니다.</p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">백테스트</p>
            <p className="kpi-value mono" data-testid="kpi-backtests">
              <StatValue isError={backtestsQ.isError} isPending={backtestsQ.isPending}>
                {backtestTotal}
              </StatValue>
            </p>
            <p className="kpi-foot">바 단위 이벤트 루프 엔진으로 실행합니다.</p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">데모 실현 손익 · 합산</p>
            {/* 형제 KPI 와 같은 규율(StatValue) — 세션 목록/집계 조회가 실패·미수신이면
                합산 손익을 성공-0 처럼 그리지 않는다. 손익은 목록(어떤 세션인지)과 세션별
                state(합산 대상)에 모두 의존하므로 두 쿼리 상태를 OR 로 본다. */}
            <p className={`kpi-value mono ${pnlToneClass}`} data-testid="kpi-pnl">
              <StatValue
                isError={sessionsQ.isError || agg.isError}
                isPending={sessionsQ.isPending || agg.isPending}
              >
                {formatSignedUsd(agg.totalRealizedPnl)}
              </StatValue>
            </p>
            {/* BL-424 — 내용을 **하나의 자식**으로 싼다. `.kpi-foot` 은 `display:flex` 라
                (globals.css, KITPORT 정본 구간) 여러 줄 산문을 직접 넣으면 텍스트 노드마다
                익명 flex item 이 생겨 좌우로 흩어지고 `<br />` 이 줄바꿈으로 작동하지 않는다.
                2026-08-09 375px 실측 — 「건의 실현 손익 합입니다.」와 「미실현(추정)」이
                본문 오른쪽에 붙어 한 덩어리로 뭉쳤다(BL-424 가 「밀착」이라 적은 그 모양).
                flex item 이 하나면 그 안은 보통의 인라인 흐름이라 `<br />` 이 되살아난다.
                ★`.kpi-foot` 자체는 못 고친다 — KITPORT 센티넬 안이라 무결성 가드가 막는다. */}
            <p className="kpi-foot">
              <span>
                USDT. 활성 세션 종료 거래 <span className="mono">{agg.totalClosedTrades}</span>건의
                실현 손익 합입니다.
                <br />
                미실현(추정) {unrealized.total === null ? "—" : formatSignedUsd(unrealized.total)}
                {/* BL-458 — 이 합계의 신뢰 등급. 채워진 세션 중 하나라도 소계를 안
                    보고하면 집계가 null 이라 아무것도 그리지 않는다 — 반쪽 분할을
                    전체인 것처럼 보여주지 않는다. */}
                {agg.confirmedRealizedPnl != null && agg.estimatedRealizedPnl != null ? (
                  <>
                    <br />이 중 {ORDER_REALIZED_PNL_SOURCE_LABEL.confirmed}{" "}
                    {formatSignedUsd(agg.confirmedRealizedPnl)} ·{" "}
                    {ORDER_REALIZED_PNL_SOURCE_LABEL.estimated}{" "}
                    {formatSignedUsd(agg.estimatedRealizedPnl)} 입니다.{" "}
                    {ORDER_REALIZED_PNL_SOURCE_HINT.estimated}.
                  </>
                ) : null}
              </span>
            </p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">활성 세션</p>
            <p className="kpi-value mono" data-testid="kpi-sessions">
              <StatValue isError={sessionsQ.isError} isPending={sessionsQ.isPending}>
                {activeSessions.length}
              </StatValue>
            </p>
            <p className="kpi-foot">지금 거래를 돌리고 있는 라이브 세션 수입니다.</p>
          </article>
        </div>
      </section>

      {/* ===== 02 데모 계좌 자산 곡선 ===== */}
      <section className="section rise d3" aria-label="데모 계좌 자산 곡선">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 데모 계좌
          </p>
          <h2 className="section-title">자산 곡선</h2>
          <p className="section-desc">
            활성 세션들이 시간에 따라 실현한 손익을 합쳐서 봅니다. 세션이 자산 곡선을 보고하기
            전에는 곡선을 그리지 않습니다.
          </p>
        </header>

        <WorkspaceEquityCard
          data={equityData}
          isLoading={agg.isLoading}
          activeSessionCount={activeSessions.length}
          latestValue={agg.totalRealizedPnl}
          hasProvenanceSplit={agg.confirmedRealizedPnl != null && agg.estimatedRealizedPnl != null}
        />
      </section>

      {/* ===== 03 최근 실행 ===== */}
      <section className="section rise d4" aria-label="최근 실행">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">03</span> 최근 실행
          </p>
          <h2 className="section-title">최근 실행 {recentRuns.length}건</h2>
          <p className="section-desc">
            백테스트와 최적화 원장을 각각 최근 순으로 가져와 합쳤습니다. 최적화 결과의 성과는
            상세에서 확인합니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">실행 목록</h3>
              <p className="card-sub">
                최근 {recentRuns.length}건 표시 · 백테스트 전체{" "}
                <span className="mono">{backtestTotal}</span>건.
              </p>
            </div>
            <div className="chart-head-actions">
              <button
                className="btn btn-ghost btn-xs"
                type="button"
                onClick={() => backtestsQ.refetch()}
              >
                <RefreshCwIcon aria-hidden="true" />
                새로고침
              </button>
              <button
                className="btn btn-ghost btn-xs"
                type="button"
                onClick={() => optimizationsQ.refetch()}
              >
                최적화 새로고침
              </button>
            </div>
          </div>

          <div className="report-meta">
            {backtestsQ.isError ? <span className="chip warn">백테스트 확인 불가</span> : null}
            {optimizationsQ.isError ? <span className="chip warn">최적화 확인 불가</span> : null}
          </div>

          {backtestsQ.isLoading && optimizationsQ.isLoading ? (
            <RunsSkeleton columns={8} />
          ) : recentRuns.length === 0 && backtestsQ.isError && optimizationsQ.isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="runs-error"
                icon={<AlertTriangleIcon />}
                title="실행 원장을 불러오지 못했습니다."
                body="백테스트와 최적화 원장이 모두 확인 불가입니다."
                code={`${RUNS_ENDPOINT} · ${OPTIMIZATION_RUNS_ENDPOINT}`}
              >
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => {
                    void backtestsQ.refetch();
                    void optimizationsQ.refetch();
                  }}
                >
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          ) : recentRuns.length === 0 ? (
            <div className="card-body">
              <StateBox
                testId="runs-empty"
                icon={<InboxIcon />}
                title="아직 실행한 작업이 없습니다."
                body="전략을 선택하고 기간을 설정하면 첫 백테스트 또는 최적화를 실행할 수 있습니다."
              >
                <Link className="btn btn-primary btn-xs" href="/backtests/new">
                  첫 백테스트 실행
                </Link>
              </StateBox>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="trades runs-table" aria-label={`최근 실행 ${recentRuns.length}건`}>
                <thead>
                  <tr>
                    <th scope="col">실행 ID</th>
                    <th scope="col">유형</th>
                    <th scope="col">전략</th>
                    <th scope="col">심볼 · 주기</th>
                    <th scope="col" className="num">
                      수익률
                    </th>
                    <th scope="col" className="num">
                      MDD
                    </th>
                    <th scope="col" className="col-status">
                      상태
                    </th>
                    <th scope="col">실행 시각</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRuns.map((recent) => (
                    <RecentRunRow
                      key={`${recent.type}-${recent.run.id}`}
                      recent={recent}
                      strategyNameById={strategyNameById}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="pager">
            <span>
              각 원장의 상위 {RECENT_RUNS_LIMIT}건을 실행 시각 내림차순으로 합쳐 보여 줍니다.
              백테스트 전체는 <span className="mono">{backtestTotal}</span>건입니다.
            </span>
            <Link className="btn btn-ghost btn-xs" href="/backtests">
              백테스트 전체 보기
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 04 전략 ===== */}
      <section className="section rise d5" aria-label="전략 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">04</span> 전략
          </p>
          <h2 className="section-title">등록한 전략 {strategyCount}종</h2>
          <p className="section-desc">
            각 전략의 가장 최근 완료 백테스트 결과입니다. 어떤 실행의 값인지 실행 ID와 완료 시각을
            함께 밝힙니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">전략 목록</h3>
              <p className="card-sub">최근 {strategyItems.length}종 표시.</p>
            </div>
          </div>

          {strategyListQ.isLoading ? (
            <RunsSkeleton columns={4} />
          ) : strategyListQ.isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="strategies-error"
                icon={<AlertTriangleIcon />}
                title="전략 목록을 불러오지 못했습니다."
                body={
                  strategyListQ.error
                    ? strategyListQ.error.message
                    : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."
                }
                code="GET /api/v1/strategies"
              >
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => strategyListQ.refetch()}
                >
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          ) : strategyItems.length === 0 ? (
            <div className="card-body">
              <StateBox
                testId="strategies-empty"
                icon={<InboxIcon />}
                title="아직 등록한 전략이 없습니다."
                body="Pine Script 전략을 등록하면 백테스트와 라이브 세션에서 쓸 수 있습니다."
              >
                <Link className="btn btn-primary btn-xs" href="/strategies/new">
                  첫 전략 등록
                </Link>
              </StateBox>
            </div>
          ) : (
            <div>
              {strategyItems.map((strategy) => (
                <StrategyPerformanceRow key={strategy.id} strategy={strategy} />
              ))}
            </div>
          )}
        </div>
      </section>

      <p className="disclaimer">
        <InfoIcon />
        <span>
          데모 계좌는 Bybit 데모 환경의 주문 결과이며 실자금이 아닙니다. 자산 곡선은 활성 세션이
          실현한 손익만 반영하고, 미실현 손익과 수수료 이후 잔고는 포함하지 않습니다.
        </span>
      </p>

      <footer className="foot">
        <span>QuantBridge · 워크스페이스 대시보드</span>
        <span>바 단위 이벤트 루프 엔진</span>
      </footer>
    </main>
  );
}

function RecentRunRow({
  recent,
  strategyNameById,
}: {
  recent: RecentRun;
  strategyNameById: ReadonlyMap<string, string>;
}) {
  if (recent.type === "optimization") {
    const { label, tone, showCheckIcon } = OPTIMIZATION_STATUS_LABEL[recent.run.status];
    const strategyName = recent.run.strategy_id
      ? (strategyNameById.get(recent.run.strategy_id) ?? EMPTY_CELL)
      : EMPTY_CELL;
    const symbolTimeframe = recent.run.backtest_symbol
      ? `${recent.run.backtest_symbol} · ${recent.run.backtest_timeframe ?? EMPTY_CELL}`
      : EMPTY_CELL;
    return (
      <tr data-testid={`run-row-${recent.run.id}`} data-status={recent.run.status}>
        <td className="mono-l run-id">
          <Link href={`/optimizer/${recent.run.id}`}>{recent.run.id.slice(0, 8)}</Link>
        </td>
        <td>{RECENT_RUN_TYPE_LABEL.optimization}</td>
        <td>{strategyName}</td>
        <td className="mono-l">{symbolTimeframe}</td>
        {/* BL-429 — best 조합의 백테스트 metric. 백테스트 행과 같은 열·같은 의미의 숫자다.
            값이 없는 실행(RUNNING·FAILED·best 미확정)은 MetricValue 가 빈칸으로 그린다. */}
        <MetricValue value={recent.run.best_total_return} format={formatPercent} />
        <MetricValue value={recent.run.best_max_drawdown} format={formatPercent} />
        <td className="col-status">
          <span className={CHIP_TONE_CLASS[tone]}>
            {showCheckIcon ? <CheckIcon /> : null}
            {label}
          </span>
        </td>
        <td className="mono-l dim">{formatDateTime(recent.run.created_at)}</td>
      </tr>
    );
  }

  const { label, tone, showCheckIcon } = BACKTEST_STATUS_LABEL[recent.run.status];
  return (
    <tr data-testid={`run-row-${recent.run.id}`} data-status={recent.run.status}>
      <td className="mono-l run-id">
        <Link href={`/backtests/${recent.run.id}`}>{recent.run.id.slice(0, 8)}</Link>
      </td>
      <td>{RECENT_RUN_TYPE_LABEL.backtest}</td>
      <td>{strategyNameById.get(recent.run.strategy_id) ?? EMPTY_CELL}</td>
      <td className="mono-l">
        {recent.run.symbol} · {recent.run.timeframe}
      </td>
      <MetricValue value={recent.run.metrics_summary?.total_return} format={formatPercent} />
      <MetricValue value={recent.run.metrics_summary?.max_drawdown} format={formatPercent} />
      <td className="col-status">
        <span className={CHIP_TONE_CLASS[tone]}>
          {showCheckIcon ? <CheckIcon /> : null}
          {label}
        </span>
      </td>
      <td className="mono-l dim">{formatDateTime(recent.run.created_at)}</td>
    </tr>
  );
}

function MetricValue({
  value,
  format,
}: {
  value: number | null | undefined;
  format: (value: number) => string;
}) {
  return <td className="num">{value == null ? EMPTY_CELL : format(value)}</td>;
}

function StrategyPerformanceRow({ strategy }: { strategy: StrategyListItem }) {
  const latest = strategy.latest_backtest;
  const metrics = latest?.metrics;
  const totalReturn = metrics?.total_return;
  // 컨벤션 SSOT 경유 — raw `.toFixed(2)` 는 degenerate 실행(`unavailable`)을
  // 자신만만한 `0.00` 으로 인쇄한다. 엔진은 그 경우 의도적으로 Decimal("0") 을
  // 반환하므로(`engine/metrics.py:76-103`) null 검사로는 걸러지지 않는다.
  const sharpe = describeSharpe(metrics?.sharpe_convention, metrics?.sharpe_ratio);
  const returnPct = totalReturn == null ? null : totalReturn * 100;
  const meterPct = returnPct == null ? null : Math.max(0, Math.min(returnPct, METER_CAP_PCT));
  const meterWidth = meterPct == null ? 0 : (meterPct / METER_CAP_PCT) * 100;
  const basis =
    meterPct == null
      ? null
      : `${returnPct!.toFixed(2)} / ${METER_CAP_PCT.toFixed(2)} = ${meterWidth.toFixed(1)}%`;

  return (
    <div className="perf-row" data-testid={`strategy-row-${strategy.id}`}>
      <div className="perf-id">
        <Link className="perf-name" href={`/strategies/${strategy.id}/edit`}>
          {strategy.name}
        </Link>
        <div className="perf-meta">
          <span className="chip">
            {strategy.symbol ?? EMPTY_CELL} · {strategy.timeframe ?? EMPTY_CELL}
          </span>
          {latest ? <span className="chip">{latest.backtest_id.slice(0, 8)}</span> : null}
          {latest?.completed_at ? (
            <span className="chip">{formatDateTime(latest.completed_at)}</span>
          ) : null}
        </div>
      </div>
      <div className="perf-figure" title={latest == null ? "완료 실행 없음" : undefined}>
        <span className="k">최근 수익률</span>
        <span
          className={`v ${totalReturn != null && totalReturn > 0 ? "pos" : totalReturn != null && totalReturn < 0 ? "neg" : ""}`}
        >
          {totalReturn == null ? EMPTY_CELL : formatPercent(totalReturn)}
        </span>
      </div>
      <div className="perf-figure" title={latest == null ? "완료 실행 없음" : sharpe.foot}>
        <span className="k">샤프</span>
        <span className="v">{sharpe.display}</span>
      </div>
      <div className="perf-bar" title={latest == null ? "완료 실행 없음" : undefined}>
        {meterPct == null ? (
          <p className="perf-note">완료 실행 없음</p>
        ) : (
          <>
            <div className="meter bull">
              <span style={{ width: `${meterWidth}%` }} />
            </div>
            <p className="perf-basis">{basis}</p>
          </>
        )}
      </div>
    </div>
  );
}

// 다음 페이지를 불러오는 동안의 스켈레톤 — S5 backtest-list ListSkeleton 관례(.sk .sk-cell).
function RunsSkeleton({ columns = 6 }: { columns?: number }) {
  return (
    <div className="table-wrap" data-testid="runs-skeleton" aria-hidden="true">
      <table className="trades runs-table">
        <tbody>
          {Array.from({ length: 6 }, (_, row) => `row-${row}`).map((rowKey) => (
            <tr key={rowKey}>
              {Array.from({ length: columns }, (_, column) => `${rowKey}-column-${column}`).map(
                (cellKey) => (
                  <td key={cellKey}>
                    <span className="sk sk-cell" />
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function AlertTriangleIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <line x1="12" y1="9" x2="12" y2="13.5" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function InboxIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
      <path d="M5.5 6.5 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-5.5A2 2 0 0 0 16.8 5H7.2a2 2 0 0 0-1.7 1.5z" />
    </svg>
  );
}
