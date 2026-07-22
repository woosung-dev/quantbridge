"use client";

// 워크스페이스 대시보드 — C 디자인 언어 이식 (S7). 프로토타입 screen-02 의 시맨틱 CSS 를
// 소비하되, 스키마가 받치는 값만 그린다(캐논 §4.9). 목업의 미실현 손익·수익률 미터·전략
// 수명주기 칩(배포됨/검증됨/초안)·per-strategy 성과는 실 스키마에 없어 렌더하지 않는다.
//  - 손익 KPI 는 라이브 세션 집계의 "실현" 손익이다(미실현 필드 부재). 라벨을 실현으로 못박는다.
//  - 전략 §04 는 수명주기 칩을 그리지 않는다(schemas.ts 에 draft/validated/deployed 0건).
//  - 실행 표는 목록 스키마(BacktestSummary)에 있는 열만 그린다(수익률/MDD 열 없음, S5 와 동일).
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
import { formatDateTime } from "@/features/backtest/utils";
import {
  useLiveSessions,
  useLiveSessionsAggregate,
} from "@/features/live-sessions";
import { useStrategies } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";
import { useExchangeAccounts } from "@/features/trading";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

import { WorkspaceEquityCard } from "./workspace-equity-card";

const RECENT_RUNS_LIMIT = 8;
const STRATEGY_FETCH_LIMIT = 100;
const RUNS_ENDPOINT = "GET /api/v1/backtests";

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

  const accountsQ = useExchangeAccounts();
  // 목록 쿼리 하나로 §04 전략 목록 + 실행표의 전략명 매핑 + KPI 카운트(.total)를 모두 얻는다.
  const strategyListQ = useStrategies({
    limit: STRATEGY_FETCH_LIMIT,
    offset: 0,
    is_archived: false,
  });
  // 실행표 + 백테스트 KPI 카운트(.total). 별도 count 쿼리를 두지 않는다.
  const backtestsQ = useBacktests({ limit: RECENT_RUNS_LIMIT, offset: 0 });

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

  const strategyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of strategyItems) map.set(s.id, s.name);
    return map;
  }, [strategyItems]);

  const equityData = useMemo<ChartPoint[]>(
    () => agg.mergedEquityCurve.map((p) => ({ time: p.time, value: p.value })),
    [agg.mergedEquityCurve],
  );

  const pnlToneClass =
    agg.totalRealizedPnl > 0 ? "pos" : agg.totalRealizedPnl < 0 ? "neg" : "";

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
              <PlusIcon aria-hidden="true" />
              새 전략
            </Link>
            <Link className="btn btn-primary" href="/backtests/new">
              <PlusIcon aria-hidden="true" />
              새 백테스트
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
            <p className="kpi-foot">
              USDT. 활성 세션 종료 거래 <span className="mono">{agg.totalClosedTrades}</span>건의
              실현 손익 합입니다.
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
        />
      </section>

      {/* ===== 03 최근 실행 ===== */}
      <section className="section rise d4" aria-label="최근 실행">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">03</span> 최근 실행
          </p>
          <h2 className="section-title">최근 백테스트 {backtestItems.length}건</h2>
          <p className="section-desc">
            백테스트 원장에서 최근 실행을 상태와 함께 가져왔습니다. 아직 끝나지 않은 실행은
            수익률을 채우지 않으므로 이 표에는 결과 열을 두지 않습니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">실행 목록</h3>
              <p className="card-sub">
                최근 {backtestItems.length}건 표시 · 전체{" "}
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
            </div>
          </div>

          {backtestsQ.isLoading ? (
            <RunsSkeleton />
          ) : backtestsQ.isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="runs-error"
                icon={<AlertTriangleIcon />}
                title="실행 목록을 불러오지 못했습니다."
                body={
                  backtestsQ.error
                    ? backtestsQ.error.message
                    : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."
                }
                code={RUNS_ENDPOINT}
              >
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => backtestsQ.refetch()}
                >
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          ) : backtestItems.length === 0 ? (
            <div className="card-body">
              <StateBox
                testId="runs-empty"
                icon={<InboxIcon />}
                title="아직 실행한 백테스트가 없습니다."
                body="전략을 선택하고 기간을 설정하면 첫 백테스트 결과를 받을 수 있습니다."
              >
                <Link className="btn btn-primary btn-xs" href="/backtests/new">
                  첫 백테스트 실행
                </Link>
              </StateBox>
            </div>
          ) : (
            <div className="table-wrap">
              <table
                className="trades runs-table"
                aria-label={`최근 백테스트 실행 ${backtestItems.length}건`}
              >
                <thead>
                  <tr>
                    <th scope="col">실행 ID</th>
                    <th scope="col">전략</th>
                    <th scope="col">심볼 · 주기</th>
                    <th scope="col">기간</th>
                    <th scope="col" className="col-status">
                      상태
                    </th>
                    <th scope="col">실행 시각</th>
                  </tr>
                </thead>
                <tbody>
                  {backtestItems.map((b) => {
                    // 라벨·톤은 S4 용어 SSOT 에서만 온다 (원시 enum 렌더 금지).
                    const { label, tone, showCheckIcon } =
                      BACKTEST_STATUS_LABEL[b.status];
                    return (
                      <tr key={b.id} data-testid={`run-row-${b.id}`} data-status={b.status}>
                        <td className="mono-l run-id">
                          <Link href={`/backtests/${b.id}`}>{b.id.slice(0, 8)}</Link>
                        </td>
                        <td>{strategyNameById.get(b.strategy_id) ?? EMPTY_CELL}</td>
                        <td className="mono-l">
                          {b.symbol} · {b.timeframe}
                        </td>
                        <td className="mono-l">
                          {formatDateTime(b.period_start)}
                          <span className="run-sub">~ {formatDateTime(b.period_end)}</span>
                        </td>
                        <td className="col-status">
                          <span className={CHIP_TONE_CLASS[tone]}>
                            {showCheckIcon ? <CheckIcon /> : null}
                            {label}
                          </span>
                        </td>
                        <td className="mono-l dim">{formatDateTime(b.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="pager">
            <span>
              백테스트 원장 상위 {backtestItems.length}건을 실행 시각 내림차순으로 보여 줍니다.
              전체는 <span className="mono">{backtestTotal}</span>건입니다.
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
            아카이브하지 않은 전략입니다. 성과는 각 전략의 백테스트 결과에서 보므로, 여기서는
            식별 정보만 보여 줍니다.
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
            <div className="table-wrap">
              <table className="trades runs-table" aria-label={`전략 목록 ${strategyItems.length}종`}>
                <thead>
                  <tr>
                    <th scope="col">전략</th>
                    <th scope="col">심볼 · 주기</th>
                    <th scope="col">태그</th>
                    <th scope="col">수정 시각</th>
                  </tr>
                </thead>
                <tbody>
                  {strategyItems.map((s) => (
                    <tr key={s.id} data-testid={`strategy-row-${s.id}`}>
                      <td className="run-id">
                        <Link href={`/strategies/${s.id}`}>{s.name}</Link>
                      </td>
                      <td className="mono-l">
                        {s.symbol ? s.symbol : EMPTY_CELL}
                        {s.timeframe ? ` · ${s.timeframe}` : ""}
                      </td>
                      <td className="dim">
                        {s.tags.length > 0 ? s.tags.join(", ") : EMPTY_CELL}
                      </td>
                      <td className="mono-l dim">{formatDateTime(s.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
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

// 다음 페이지를 불러오는 동안의 스켈레톤 — S5 backtest-list ListSkeleton 관례(.sk .sk-cell).
function RunsSkeleton({ columns = 6 }: { columns?: number }) {
  return (
    <div className="table-wrap" data-testid="runs-skeleton" aria-hidden="true">
      <table className="trades runs-table">
        <tbody>
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: columns }).map((__, j) => (
                <td key={j}>
                  <span className="sk sk-cell" />
                </td>
              ))}
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
