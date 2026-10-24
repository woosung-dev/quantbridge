"use client";

// 트레이딩 코크핏 — C 디자인 언어 이식 (S8). 프로토타입 screen-01 의 시맨틱 CSS(.page/.report/
// .section/.kpi/.card)를 소비하며, §02 잔고와 §03 세션별 포지션 대조는 실 API 스키마를 쓴다.
// 미실현 손익은 WS ticker와 state의 open_trades로 만든 추정치이며 §03 거래소 보고값과 다를 수 있다.
// 데이터 흐름은 도메인 훅 재사용. 실시간 스트림은 WebSocket+Zustand로 별도 배선한다.
// 프로토타입의 "총 세션" 카드는 사용자 확정 WS Tier 2 요구로 미실현 추정 KPI로 교체한다.

import { RefreshCwIcon } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { LiveSessionDetail } from "@/features/live-sessions/components/live-session-detail";
import { LiveSessionForm } from "@/features/live-sessions/components/live-session-form";
import { LiveSessionList } from "@/features/live-sessions/components/live-session-list";
import { LiveSessionTable } from "@/features/live-sessions/components/live-session-table";
import type { LiveSession } from "@/features/live-sessions/schemas";
import { ExchangeAccountsPanel } from "./exchange-accounts-panel";
import { KillSwitchPanel } from "./kill-switch-panel";
import { OrdersPanel } from "./orders-panel";
import { InfoIcon } from "@/components/info-icon";
import { StateBox } from "@/components/state-box";
import { StatValue } from "@/components/stat-value";

import { KillSwitchBanner } from "./kill-switch-banner";
import { AccountBalanceSection } from "./account-balance-section";
import { AccountPositionsTable } from "./account-positions-table";
import { OpenPositionsTable } from "./open-positions-table";
import { SessionDiagnostics } from "./session-diagnostics";
import { UnrealizedPnlKpi } from "./unrealized-pnl-kpi";
import { useTradingCockpitData } from "../use-trading-cockpit-data";

export function TradingCockpit() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("session");
  const { overview, positions, sessionTable, registration, selection, refresh } =
    useTradingCockpitData(selectedId);

  const handleSessionSelect = (session: Pick<LiveSession, "id">) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("session", session.id);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
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
              <span className={overview.accounts.isError ? "chip warn" : "chip"}>
                {overview.accounts.isError
                  ? "거래소 확인 불가"
                  : overview.accounts.count > 0
                    ? `거래소 ${overview.accounts.count}개 연결`
                    : "거래소 미등록"}
              </span>
              <span className="chip">
                활성 세션 {overview.sessions.isError ? "확인 불가" : overview.sessions.count}
              </span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
          <div className="report-actions">
            <button className="btn" type="button" onClick={refresh}>
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
              <StatValue
                isError={overview.sessions.isError}
                isPending={overview.sessions.isPending}
              >
                {overview.sessions.count}
              </StatValue>
            </p>
            <p className="kpi-foot">지금 거래를 돌리고 있는 라이브 세션 수입니다.</p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">연결된 거래소</p>
            <p className="kpi-value mono" data-testid="kpi-accounts">
              <StatValue
                isError={overview.accounts.isError}
                isPending={overview.accounts.isPending}
              >
                {overview.accounts.count}
              </StatValue>
            </p>
            <p className="kpi-foot">
              {overview.accounts.isError
                ? "계정 목록을 확인하지 못했습니다."
                : overview.accounts.count > 0
                  ? "API 키가 등록된 계정입니다."
                  : "API 키가 아직 없습니다."}
            </p>
          </article>

          <article className="card kpi">
            <p className="kpi-label">킬 스위치</p>
            <p
              className={`kpi-value mono ${!overview.killSwitch.isError && overview.killSwitch.unresolvedCount > 0 ? "neg" : ""}`}
              data-testid="kpi-kill-switch"
            >
              {overview.killSwitch.isError ? (
                <span className="kpi-na">확인 불가</span>
              ) : overview.killSwitch.isPending ? (
                <span className="kpi-na">불러오는 중</span>
              ) : (
                <>
                  {overview.killSwitch.unresolvedCount}
                  <span className="kpi-value-tag">
                    {overview.killSwitch.unresolvedCount > 0 ? "활성" : "대기"}
                  </span>
                </>
              )}
            </p>
            <p className="kpi-foot">
              {overview.killSwitch.isError
                ? "킬 스위치 상태를 확인하지 못했습니다."
                : overview.killSwitch.unresolvedCount > 0
                  ? "미해결 이벤트가 있어 자동 주문이 차단됩니다."
                  : "미해결 이벤트가 없습니다."}
            </p>
          </article>

          <UnrealizedPnlKpi sessions={positions.sessions} />
        </div>
      </section>

      {/* ===== 02 계좌 잔고 ===== */}
      <section className="section rise d3" aria-label="계좌 잔고">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 계좌 잔고
          </p>
          <h2 className="section-title">활성 세션 계정의 잔고</h2>
          <p className="section-desc">활성 Bybit 데모 세션이 참조하는 거래소 계정만 표시합니다.</p>
        </header>
        <AccountBalanceSection accounts={positions.balanceAccounts} />
      </section>

      {/* ===== 03 열린 포지션 ===== */}
      <section className="section rise d4" aria-label="열린 포지션">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">03</span> 열린 포지션
          </p>
          <h2 className="section-title">거래소 보고 포지션</h2>
          <p className="section-desc">
            운영 가능한 Bybit 데모 계정에 남은 포지션을 활성 세션과 무관하게 보여주고, 그 아래에서
            같은 계정과 심볼을 쓰는 다른 전략도 합치지 않고 세션별로 대조합니다.
          </p>
        </header>
        <AccountPositionsTable accounts={positions.accounts} />
        <OpenPositionsTable
          sessions={positions.sessions}
          demoSessionIds={positions.demoSessionIds}
          resolveStrategyName={positions.resolveStrategyName}
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
            새 계정은 Bybit 데모 전용입니다. 기존 지원 범위 밖 계정은 보존·삭제만 가능하며 API 키는
            마스킹해 보여 줍니다.
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

        <LiveSessionTable {...sessionTable} />

        <div className="session-manage">
          <div className="session-manage-col">
            <div className="card card-pad">
              <h3 className="card-title">새 라이브 세션</h3>
              <p className="card-sub session-card-sub">Bybit 데모 계정에 전략을 붙여 시작합니다.</p>
              <LiveSessionForm {...registration} onSuccess={handleSessionSelect} />
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
            {selection.status === "selected" ? (
              <div className="card card-pad">
                <LiveSessionDetail session={selection.session} />
              </div>
            ) : selection.status === "loading" ? (
              <div className="card card-pad">
                <StateBox
                  title="세션 목록을 불러오는 중입니다."
                  body="선택한 세션의 상세를 확인하고 있습니다."
                />
              </div>
            ) : selection.status === "error" ? (
              <div className="card card-pad">
                <StateBox
                  title="세션 목록을 불러오지 못했습니다."
                  body="목록을 다시 불러오면 선택한 세션의 상세를 확인할 수 있습니다."
                />
              </div>
            ) : selection.status === "missing" ? (
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
        <SessionDiagnostics session={selection.status === "selected" ? selection.session : null} />
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
