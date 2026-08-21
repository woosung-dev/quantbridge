"use client";

// 트레이딩 코크핏 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 의 시맨틱 CSS(.page/.report/
// .section/.kpi/.card)를 소비하며, §02 잔고와 §03 세션별 포지션 대조는 실 API 스키마를 쓴다.
// 미실현 손익은 WS ticker와 state의 open_trades로 만든 추정치이며 §03 거래소 보고값과 다를 수 있다.
// 데이터 흐름은 도메인 훅 재사용. 실시간 스트림은 WebSocket+Zustand로 별도 배선한다.
// 프로토타입의 "총 세션" 카드는 사용자 확정 WS Tier 2 요구로 미실현 추정 KPI로 교체한다.

import { useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCwIcon } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  LiveSessionDetail,
  LiveSessionForm,
  LiveSessionList,
  LiveSessionTable,
  liveSessionKeys,
  useLiveSessions,
  type LiveSession,
} from "@/features/live-sessions";
import { strategyKeys, useStrategies } from "@/features/strategy/hooks";
import type { StrategyListItem } from "@/features/strategy/schemas";
import {
  ExchangeAccountsPanel,
  KillSwitchPanel,
  OrdersPanel,
  tradingKeys,
  useExchangeAccounts,
  useKillSwitchEvents,
} from "@/features/trading";
import { alertRuleKeys } from "@/features/alert-rules/query-keys";
import { useAuthCtx } from "@/hooks/use-auth-ctx";
import type { ExchangeAccount, KillSwitchEvent } from "@/features/trading/schemas";
import { InfoIcon } from "@/components/info-icon";
import { StateBox } from "@/components/state-box";
import { StatValue } from "@/components/stat-value";

import { KillSwitchBanner } from "./kill-switch-banner";
import { AccountBalanceSection } from "./account-balance-section";
import { AccountPositionsTable } from "./account-positions-table";
import { OpenPositionsTable } from "./open-positions-table";
import { SessionDiagnostics } from "./session-diagnostics";
import { UnrealizedPnlKpi } from "./unrealized-pnl-kpi";

const STRATEGY_FETCH_LIMIT = 100;

export function TradingCockpit() {
  const queryClient = useQueryClient();
  const { uid } = useAuthCtx();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // BL-423 — `true`(비활성 포함). 아래 LiveSessionList 도 `useLiveSessions(true)` 를 쓰므로
  // 여기서 `false` 를 쓰면 queryKey 가 갈려(`list` vs `listWithInactive`) **같은 화면이 목록을
  // 두 번 fetch** 한다. 키를 일치시켜 RQ 캐시가 한 요청으로 dedupe 하게 한다.
  // 부수 효과가 아니라 목적: `sessionItems` 에 종료 세션이 들어오면서 LiveSessionTable 의
  // PAUSED 칩과 active-first 정렬이 처음으로 도달 가능해진다. 활성만 필요한 소비자는
  // 아래 `activeSessions` 를 계속 쓴다.
  const sessionsQ = useLiveSessions(true);
  const accountsQ = useExchangeAccounts();
  const ksQ = useKillSwitchEvents();
  const strategyListQ = useStrategies({
    limit: STRATEGY_FETCH_LIMIT,
    offset: 0,
    is_archived: false,
  });

  const selectedId = searchParams.get("session");

  // H-1 준수 — RQ data 객체를 dep 로 직접 쓰지 않고 .items/array 참조를 memoize.
  const sessionItems = useMemo<readonly LiveSession[]>(
    () => sessionsQ.data?.items ?? [],
    [sessionsQ.data?.items],
  );
  // BL-533 — 종료 세션용 미러 state 를 두지 않는다. `useLiveSessions(true)` 가 비활성까지
  // 실어 오므로 `sessionItems` 하나로 찾힌다. 미러는 코크핏이 `useLiveSessions()`(활성만)를
  // 쓰던 시절 목록에 없는 세션을 붙들기 위한 우회였고, 키를 통일한 지금은 같은 사실을
  // 두 곳에 두어 어긋날 수 있게 만들 뿐이다.
  const selected = useMemo(
    () => sessionItems.find((session) => session.id === selectedId) ?? null,
    [sessionItems, selectedId],
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
  // ★vercel-react-best-practices 대조 (2026-08-10) — `useCallback` 을 씌우지 않는다.
  //   `rerender-memo` 의 이득은 **자식이 memo 일 때**만 생기는데 `LiveSessionList` 도
  //   `LiveSessionForm` 도 memo 가 아닌 평범한 함수 컴포넌트다. 씌우면 이득 없는 배선만 는다.
  //   종전 판도 렌더마다 새 함수였으므로 이 축에서 나빠진 것도 없다.
  const handleSessionSelect = (session: Pick<LiveSession, "id">) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("session", session.id);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
  const demoSessionIds = useMemo(() => {
    const demoAccountIds = new Set(
      accountItems.filter((account) => account.mode === "demo").map((account) => account.id),
    );
    return new Set(
      activeSessions
        .filter((session) => demoAccountIds.has(session.exchange_account_id))
        .map((session) => session.id),
    );
  }, [accountItems, activeSessions]);
  // BL-663 — 미실현 손익 추정은 `<UnrealizedPnlKpi>` 안으로 내렸다. 그 훅이 WS ticker 를
  // 구독하므로 여기서 부르면 활성 세션 심볼이 틱할 때마다 §01~§08 전체가 재조정된다.
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
  // BL-498 — 계정 스코프 포지션은 **모든** 등록 계정을 순회한다. 활성 세션 기준으로
  // 좁히면 세션이 0건일 때 잔여 노출이 다시 화면에서 사라진다.
  const allAccountTargets = useMemo(
    () =>
      accountItems.map((account) => ({
        id: account.id,
        label: accountLabelById.get(account.id) ?? account.id.slice(0, 8),
        exchangeUid: account.exchange_uid,
        readOnly: account.read_only,
      })),
    [accountItems, accountLabelById],
  );
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
        read_only: a.read_only,
      })),
    [accountItems],
  );

  // BL-664 — 인자 없는 `invalidateQueries()` 는 **앱 캐시 전체**를 stale 로 만들어 마운트된 활성
  // 쿼리를 모두 동시에 재요청시킨다(백테스트 목록·옵티마이저 실행 등 이 화면과 무관한 것 포함).
  // 이 코크핏이 실제로 소비하는 도메인은 **넷**이다:
  //   trading(계정·킬스위치·주문·잔고) · live-sessions(목록·상세·상태·포지션) ·
  //   strategies(§07 폼/표의 전략명 매핑) · alert-rules(§08 진단의 세션 알림 규칙).
  // ★alert-rules 는 codex 적대 리뷰가 잡았다 — 첫 판에서 빠뜨렸고, 종전의 무필터 호출은
  //   그것까지 갱신하고 있었으므로 빠뜨린 채로 두면 **무효화 범위를 좁힌 것이 아니라 기능을 깬다.**
  //   ⇒ 도메인을 하나 추가할 때는 §01~§08 자식이 부르는 훅을 전수로 다시 세라.
  // ★키는 하드코딩하지 않고 도메인 팩토리 루트를 쓴다(apps/web/AGENTS.md §3).
  const handleRefresh = () => {
    for (const queryKey of [
      tradingKeys.all(uid),
      liveSessionKeys.all(uid),
      strategyKeys.all(uid),
      alertRuleKeys.all(uid),
    ]) {
      void queryClient.invalidateQueries({ queryKey });
    }
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

          <UnrealizedPnlKpi sessions={activeSessions} />
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
            활성 라이브 세션이 참조하는 거래소 계정만 표시합니다. 지원하지 않는 계정도 이유를 숨기지
            않습니다.
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
            먼저 계정에 남아 있는 포지션을 활성 세션과 무관하게 보여주고, 그 아래에서 같은 계정과
            심볼을 쓰는 다른 전략도 합치지 않고 세션별로 대조합니다.
          </p>
        </header>
        <AccountPositionsTable accounts={allAccountTargets} />
        <OpenPositionsTable
          sessions={activeSessions}
          demoSessionIds={demoSessionIds}
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
                onSuccess={handleSessionSelect}
              />
            </div>
            <div className="card card-pad">
              {/* BL-423 — 이 카드는 활성 세션과 최근 종료된 세션을 함께 담는다. */}
              <h3 className="card-title">세션 목록</h3>
              <p className="card-sub session-card-sub">
                지금 돌고 있는 세션을 고르면 오른쪽에 상세가 열립니다. 안전 점검이 세션을 자동으로
                중단하면 아래 &ldquo;최근 종료된 세션&rdquo; 으로 내려가고 종료 사유가 함께
                붙습니다.
              </p>
              <LiveSessionList onSelect={handleSessionSelect} selectedId={selectedId} />
            </div>
          </div>
          <div className="session-manage-col">
            {selected ? (
              <div className="card card-pad">
                <LiveSessionDetail session={selected} />
              </div>
            ) : selectedId && (sessionsQ.isPending || sessionsQ.isFetching) ? (
              <div className="card card-pad">
                <StateBox
                  title="세션 목록을 불러오는 중입니다."
                  body="선택한 세션의 상세를 확인하고 있습니다."
                />
              </div>
            ) : selectedId && sessionsQ.isError ? (
              <div className="card card-pad">
                <StateBox
                  title="세션 목록을 불러오지 못했습니다."
                  body="목록을 다시 불러오면 선택한 세션의 상세를 확인할 수 있습니다."
                />
              </div>
            ) : selectedId ? (
              <div className="card card-pad">
                <StateBox
                  title="이 세션은 목록에서 밀려났습니다."
                  body="최근 종료된 세션은 20건까지만 목록에 남습니다. 그보다 오래된 세션이라 상세를 열 수 없습니다. 종료 사유는 목록에 남아 있는 동안 세션 카드와 상세 배지에서 볼 수 있습니다."
                  testId="live-session-stopped-notice"
                />
              </div>
            ) : (
              <div className="card card-pad">
                <StateBox
                  title="세션을 선택하세요."
                  body="왼쪽 목록에서 활성 세션이나 최근 종료된 세션을 고르면 체결 이력과 활동 타임라인을 봅니다."
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
