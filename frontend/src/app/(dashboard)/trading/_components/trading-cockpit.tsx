"use client";

// 트레이딩 코크핏 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 의 시맨틱 CSS(.page/.report/
// .section/.kpi/.card)를 소비하며, §02 잔고와 §03 세션별 포지션 대조는 실 API 스키마를 쓴다.
// 미실현 손익은 WS ticker와 state의 open_trades로 만든 추정치이며 §03 거래소 보고값과 다를 수 있다.
// 데이터 흐름은 도메인 훅 재사용. 실시간 스트림은 WebSocket+Zustand로 별도 배선한다.
// 프로토타입의 "총 세션" 카드는 사용자 확정 WS Tier 2 요구로 미실현 추정 KPI로 교체한다.

import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCwIcon } from "lucide-react";

import {
  LiveSessionDetail,
  LiveSessionForm,
  LiveSessionList,
  LiveSessionTable,
  useLiveSessions,
  useUnrealizedPnlEstimate,
  type LiveSession,
} from "@/features/live-sessions";
import { useStrategies } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";
import {
  ExchangeAccountsPanel,
  KillSwitchPanel,
  OrdersPanel,
  useExchangeAccounts,
  useKillSwitchEvents,
} from "@/features/trading";
import type { ExchangeAccount, KillSwitchEvent } from "@/features/trading/schemas";
import { InfoIcon } from "@/components/info-icon";
import { StateBox } from "@/components/state-box";
import { StatValue } from "@/components/stat-value";

import { KillSwitchBanner } from "./kill-switch-banner";
import { AccountBalanceSection } from "./account-balance-section";
import { OpenPositionsTable } from "./open-positions-table";
import { SessionDiagnostics } from "./session-diagnostics";

const STRATEGY_FETCH_LIMIT = 100;
const TICKER_STALE_MS = 15_000;

function useNowTick(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
}

function formatEstimatedPnl(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} USDT`;
}

export function TradingCockpit() {
  const queryClient = useQueryClient();

  const sessionsQ = useLiveSessions();
  const accountsQ = useExchangeAccounts();
  const ksQ = useKillSwitchEvents();
  const strategyListQ = useStrategies({
    limit: STRATEGY_FETCH_LIMIT,
    offset: 0,
    is_archived: false,
  });

  const [selected, setSelected] = useState<LiveSession | null>(null);

  // H-1 준수 — RQ data 객체를 dep 로 직접 쓰지 않고 .items/array 참조를 memoize.
  const sessionItems = useMemo<readonly LiveSession[]>(
    () => sessionsQ.data?.items ?? [],
    [sessionsQ.data?.items],
  );
  const accountItems = useMemo<readonly ExchangeAccount[]>(
    () => accountsQ.data ?? [],
    [accountsQ.data],
  );
  const ksItems = useMemo<readonly KillSwitchEvent[]>(
    () => ksQ.data?.items ?? [],
    [ksQ.data?.items],
  );
  const strategyItems = useMemo<readonly StrategyListItem[]>(
    () => strategyListQ.data?.items ?? [],
    [strategyListQ.data?.items],
  );

  const activeSessions = useMemo(() => sessionItems.filter((s) => s.is_active), [sessionItems]);
  const unrealized = useUnrealizedPnlEstimate(activeSessions);
  const now = useNowTick(5_000);
  const isTickerStale = unrealized.latestTs !== null && now - unrealized.latestTs > TICKER_STALE_MS;
  const accountsCount = accountItems.length;
  const unresolvedKs = ksItems.filter((e) => e.resolved_at == null).length;

  const strategyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of strategyItems) map.set(s.id, s.name);
    return map;
  }, [strategyItems]);
  const accountLabelById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of accountItems) map.set(a.id, a.label ?? `${a.exchange} ${a.mode}`);
    return map;
  }, [accountItems]);
  const activeAccountTargets = useMemo(() => {
    const ids = new Set(
      activeSessions
        .map((session) => session.exchange_account_id)
        .filter((id): id is string => typeof id === "string" && id.length > 0),
    );
    return [...ids].map((id) => ({
      id,
      label: accountLabelById.get(id) ?? id.slice(0, 8),
    }));
  }, [accountLabelById, activeSessions]);
  const strategyNameBySessionId = useMemo(() => {
    const map = new Map<string, string>();
    for (const session of activeSessions) {
      const strategyId = session.strategy_id;
      map.set(
        session.id,
        typeof strategyId === "string"
          ? (strategyNameById.get(strategyId) ?? strategyId.slice(0, 8))
          : session.id.slice(0, 8),
      );
    }
    return map;
  }, [activeSessions, strategyNameById]);

  const formStrategies = useMemo(
    () => strategyItems.map((s) => ({ id: s.id, name: s.name })),
    [strategyItems],
  );
  const formAccounts = useMemo(
    () =>
      accountItems.map((a) => ({
        id: a.id,
        exchange: a.exchange,
        mode: a.mode,
        label: a.label,
      })),
    [accountItems],
  );

  const handleRefresh = () => {
    // 폴링 스냅샷을 즉시 갱신 — 활성 쿼리 전부 invalidate.
    void queryClient.invalidateQueries();
  };

  return (
    <main className="page">
      {/* Kill Switch 안전 경고 — S7 이 /dashboard 에서 제거한 노출을 여기서 재도입한다. */}
      <KillSwitchBanner />

      {/* ===== 세션 헤더 ===== */}
      <section className="card rise d1" aria-label="트레이딩 개요">
        <div className="report">
          <div>
            <h1 className="report-title">트레이딩 코크핏</h1>
            <div className="report-meta">
              <span className={accountsQ.isError ? "chip warn" : "chip"}>
                {accountsQ.isError
                  ? "거래소 확인 불가"
                  : accountsCount > 0
                    ? `거래소 ${accountsCount}개 연결`
                    : "거래소 미등록"}
              </span>
              <span className="chip">
                활성 세션 {sessionsQ.isError ? "확인 불가" : activeSessions.length}
              </span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
          <div className="report-actions">
            <button className="btn" type="button" onClick={handleRefresh}>
              <RefreshCwIcon aria-hidden="true" />
              새로고침
            </button>
          </div>
        </div>
      </section>

      {/* ===== 01 현황 ===== */}
      <section className="section rise d2" aria-label="트레이딩 현황">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 현황
          </p>
          <h2 className="section-title">지금 트레이딩 상태</h2>
          <p className="section-desc">
            무엇이 돌고 있고 어떤 안전장치가 살아 있는지 네 가지로 봅니다. 숫자는 각 원장이 보고한
            값을 그대로 받아 적습니다.
          </p>
        </header>

        <div className="kpi-row">
          <article className="card kpi">
            <p className="kpi-label">활성 세션</p>
            <p className="kpi-value mono" data-testid="kpi-active-sessions">
              <StatValue isError={sessionsQ.isError} isPending={sessionsQ.isPending}>
                {activeSessions.length}
              </StatValue>
            </p>
            <p className="kpi-foot">지금 거래를 돌리고 있는 라이브 세션 수입니다.</p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">연결된 거래소</p>
            <p className="kpi-value mono" data-testid="kpi-accounts">
              <StatValue isError={accountsQ.isError} isPending={accountsQ.isPending}>
                {accountsCount}
              </StatValue>
            </p>
            <p className="kpi-foot">
              {accountsQ.isError
                ? "계정 목록을 확인하지 못했습니다."
                : accountsCount > 0
                  ? "API 키가 등록된 계정입니다."
                  : "API 키가 아직 없습니다."}
            </p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">킬 스위치</p>
            <p
              className={`kpi-value mono ${!ksQ.isError && unresolvedKs > 0 ? "neg" : ""}`}
              data-testid="kpi-kill-switch"
            >
              {ksQ.isError ? (
                <span className="kpi-na">확인 불가</span>
              ) : ksQ.isPending ? (
                <span className="kpi-na">불러오는 중</span>
              ) : (
                <>
                  {unresolvedKs}
                  <span className="kpi-value-tag">{unresolvedKs > 0 ? "활성" : "대기"}</span>
                </>
              )}
            </p>
            <p className="kpi-foot">
              {ksQ.isError
                ? "킬 스위치 상태를 확인하지 못했습니다."
                : unresolvedKs > 0
                  ? "미해결 이벤트가 있어 자동 주문이 차단됩니다."
                  : "미해결 이벤트가 없습니다."}
            </p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">미실현 손익 · 추정</p>
            <p className="kpi-value mono" data-testid="kpi-unrealized-pnl">
              {unrealized.total === null ? (
                <span className="kpi-na">시세 수신 대기</span>
              ) : (
                <>
                  {formatEstimatedPnl(unrealized.total)}
                  {isTickerStale ? <span className="kpi-value-tag">시세 지연</span> : null}
                </>
              )}
            </p>
            <p className="kpi-foot">
              실시간 마크가격 × 미청산 수량 추정치. §03 거래소 보고값(/positions)과 다를 수 있습니다.
            </p>
          </article>
        </div>
      </section>

      {/* ===== 02 계좌 잔고 ===== */}
      <section className="section rise d3" aria-label="계좌 잔고">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 계좌 잔고
          </p>
          <h2 className="section-title">활성 세션 계정의 잔고</h2>
          <p className="section-desc">
            활성 라이브 세션이 참조하는 거래소 계정만 표시합니다. 지원하지 않는 계정도 이유를 숨기지 않습니다.
          </p>
        </header>
        <AccountBalanceSection accounts={activeAccountTargets} />
      </section>

      {/* ===== 03 열린 포지션 ===== */}
      <section className="section rise d4" aria-label="열린 포지션">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">03</span> 열린 포지션
          </p>
          <h2 className="section-title">거래소 보고 포지션</h2>
          <p className="section-desc">
            같은 계정과 심볼을 쓰는 다른 전략도 합치지 않고 세션별로 대조합니다.
          </p>
        </header>
        <OpenPositionsTable
          sessions={activeSessions}
          resolveStrategyName={(sessionId, fallback) =>
            strategyNameBySessionId.get(sessionId) ?? fallback
          }
        />
      </section>

      {/* ===== 04 리스크 가드 ===== */}
      <section className="section rise d5" aria-label="리스크 가드">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">04</span> 리스크 가드
          </p>
          <h2 className="section-title">지금 걸려 있는 제한</h2>
          <p className="section-desc">
            주문을 내기 전에 어떤 제한이 살아 있는지 확인하는 자리입니다. 킬 스위치가 활성이면 자동
            주문이 차단됩니다.
          </p>
        </header>
        <KillSwitchPanel />
      </section>

      {/* ===== 05 주문 원장 ===== */}
      <section className="section rise d6" aria-label="주문 원장">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">05</span> 주문 원장
          </p>
          <h2 className="section-title">최근 주문</h2>
          <p className="section-desc">
            라이브·데모 세션이 실행한 주문을 최신순으로 봅니다. 대기와 전송, 취소, 거부까지 상태를
            그대로 담습니다.
          </p>
        </header>
        <OrdersPanel />
      </section>

      {/* ===== 06 거래소 계좌 ===== */}
      <section className="section rise d7" aria-label="거래소 계좌">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">06</span> 거래소 계좌
          </p>
          <h2 className="section-title">연결된 거래소</h2>
          <p className="section-desc">
            세션이 주문을 낼 거래소 계정입니다. 데모와 라이브를 모드로 구분하고 API 키는 마스킹해
            보여 줍니다.
          </p>
        </header>
        <ExchangeAccountsPanel />
      </section>

      {/* ===== 07 라이브 세션 ===== */}
      <section className="section rise d8" aria-label="라이브 세션">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">07</span> 라이브 세션
          </p>
          <h2 className="section-title">자동 실행 세션</h2>
          <p className="section-desc">
            전략을 거래소 계정에 붙여 바 단위로 신호를 평가하는 세션입니다. 전체 요약을 먼저 보고,
            아래에서 새로 시작하거나 활성 세션을 관리합니다.
          </p>
        </header>

        <LiveSessionTable
          sessions={sessionItems}
          resolveStrategyName={(id) => strategyNameById.get(id) ?? id.slice(0, 8)}
          resolveExchangeLabel={(id) => accountLabelById.get(id) ?? id.slice(0, 8)}
        />

        <div className="session-manage">
          <div className="session-manage-col">
            <div className="card card-pad">
              <h3 className="card-title">새 라이브 세션</h3>
              <p className="card-sub session-card-sub">Bybit 데모 계정에 전략을 붙여 시작합니다.</p>
              <LiveSessionForm
                strategies={formStrategies}
                exchangeAccounts={formAccounts}
                activeSessionsCount={activeSessions.length}
                onSuccess={(s) => setSelected(s)}
              />
            </div>
            <div className="card card-pad">
              <h3 className="card-title">활성 세션</h3>
              <p className="card-sub session-card-sub">
                지금 돌고 있는 세션을 고르면 오른쪽에 상세가 열립니다.
              </p>
              <LiveSessionList onSelect={setSelected} selectedId={selected?.id ?? null} />
            </div>
          </div>
          <div className="session-manage-col">
            {selected ? (
              <div className="card card-pad">
                <LiveSessionDetail session={selected} />
              </div>
            ) : (
              <div className="card card-pad">
                <StateBox
                  title="세션을 선택하세요."
                  body="왼쪽 활성 세션 목록에서 하나를 고르면 체결 이력과 활동 타임라인을 봅니다."
                />
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ===== 08 진단 ===== */}
      <section className="section rise d9" aria-label="진단">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">08</span> 진단
          </p>
          <h2 className="section-title">연결과 알림 상태</h2>
          <p className="section-desc">
            아직 연결되지 않았거나 실패했거나 비어 있는 항목도 감추지 않고 그대로 보여줍니다.
          </p>
        </header>
        <SessionDiagnostics session={selected} />
      </section>

      <p className="disclaimer">
        <InfoIcon />
        <span>
          데모 계정은 Bybit 데모 환경의 주문 결과이며 실자금이 아닙니다. 데모는 실거래와 같은 코드
          경로를 쓰지만 슬리피지와 체결 지연은 다르게 나타납니다. 이 화면에서 잘 도는 것이
          실자금에서도 그대로 된다는 뜻은 아닙니다.
        </span>
      </p>

      <footer className="foot">
        <span>QuantBridge · 트레이딩 코크핏</span>
        <span>실시간 = WebSocket + Zustand · 이 코크핏 = 폴링 스냅샷</span>
      </footer>
    </main>
  );
}
