"use client";

import Link from "next/link";
import { Suspense } from "react";

import { CODE_LANGUAGE_LABELS, type CodeLanguage } from "@/features/strategy/code-schemas";
import { useCodeWorkspace } from "@/features/strategy/code-hooks";
import { describeApiError } from "@/lib/api-client";
import { useAuthCtx } from "@/hooks/use-auth-ctx";

export function CodeWorkspace({ initialStrategyId }: { initialStrategyId?: string }) {
  const { uid } = useAuthCtx();
  return (
    <Suspense
      fallback={
        <main className="page" role="status">
          코드 전략을 불러오는 중…
        </main>
      }
    >
      <CodeWorkspaceContent
        key={`${uid}:${initialStrategyId ?? ""}`}
        initialStrategyId={initialStrategyId}
      />
    </Suspense>
  );
}

function CodeWorkspaceContent({ initialStrategyId }: { initialStrategyId?: string }) {
  const work = useCodeWorkspace(initialStrategyId);
  const { draft, period } = work;
  const error = work.save.error ?? work.backtest.error ?? work.demo.error;
  return (
    <main className="page">
      <section className="card" aria-labelledby="code-title">
        <div className="report">
          <div>
            <h1 className="report-title" id="code-title">
              코드 전략
            </h1>
            <p className="report-meta">원문을 검토하고 버전으로 저장한 뒤 백테스트하세요.</p>
          </div>
          <div className="report-actions">
            <Link href="/strategies" className="btn">
              전략 목록
            </Link>
            <button type="button" className="btn" disabled={work.busy} onClick={work.reset}>
              새 코드
            </button>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="code-editor-title">
        <header className="section-head">
          <h2 id="code-editor-title">1. 실행할 원문</h2>
        </header>
        <div className="card p-5">
          <fieldset disabled={work.busy} className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-label">
                전략 이름
                <input
                  className="input"
                  value={draft.name}
                  maxLength={120}
                  onChange={(event) => work.change({ name: event.target.value })}
                />
              </label>
              <label className="field-label">
                실행 언어
                <select
                  className="select"
                  value={draft.language}
                  onChange={(event) =>
                    work.change({ language: event.target.value as CodeLanguage })
                  }
                >
                  {Object.entries(CODE_LANGUAGE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field-label">
              소스 코드
              <textarea
                className="textarea mono"
                rows={16}
                spellCheck={false}
                value={draft.source}
                maxLength={131072}
                placeholder="검토한 전략 원문을 붙여 넣으세요. 출력은 hold / long / short / close 의도만 허용합니다."
                onChange={(event) => work.change({ source: event.target.value })}
              />
            </label>
            <div className="grid gap-4 md:grid-cols-3">
              <label className="field-label">
                거래 심볼
                <input
                  className="input"
                  value={draft.symbol}
                  onChange={(event) => work.change({ symbol: event.target.value })}
                />
              </label>
              <label className="field-label">
                신호 주기
                <select
                  className="select"
                  value={draft.timeframe}
                  onChange={(event) =>
                    work.change({ timeframe: event.target.value as typeof draft.timeframe })
                  }
                >
                  <option value="1h">1시간</option>
                  <option value="4h">4시간</option>
                  <option value="1d">1일</option>
                </select>
              </label>
              <label className="field-label">
                준비 봉 수
                <input
                  type="number"
                  className="input"
                  min={1}
                  max={10000}
                  value={draft.warmup}
                  onChange={(event) => work.change({ warmup: Number(event.target.value) })}
                />
              </label>
            </div>
            <label className="field-label">
              파라미터 JSON
              <textarea
                className="textarea mono"
                rows={3}
                value={draft.params}
                onChange={(event) => work.change({ params: event.target.value })}
              />
            </label>
            <label className="field-label">
              자본 배분 비율 (%)
              <input
                type="number"
                className="input"
                min={0.01}
                max={100}
                step={0.01}
                value={draft.allocation}
                onChange={(event) => work.change({ allocation: Number(event.target.value) })}
              />
            </label>
            <p className="field-hint">
              1배·다음 봉 진입을 사용합니다. 백테스트는 현재 자본, 데모는 세션 시작 기준 자본에서
              배분합니다.
            </p>
            <p className="strip-note">
              손절 1R · 1.5R에서 최초 수량 절반 익절 · 2R에서 본절과 2R 거리 추적. 원문이 수량이나
              손절 가격을 지정할 수 없습니다.
            </p>
            <div className="report-actions">
              <button
                type="button"
                className="btn btn-primary"
                disabled={!draft.source.trim() || !draft.name.trim()}
                onClick={() => work.save.mutate()}
              >
                {work.save.isPending ? "저장 중…" : work.selected ? "새 버전 저장" : "전략 저장"}
              </button>
              <span className="field-hint" role="status">
                {work.selected
                  ? work.dirty
                    ? "변경 사항이 있습니다."
                    : "저장한 원문과 일치합니다."
                  : "저장 전입니다."}
              </span>
            </div>
          </fieldset>
        </div>
      </section>

      <section className="section" aria-labelledby="code-backtest-title">
        <header className="section-head">
          <h2 id="code-backtest-title">2. 저장한 버전 백테스트</h2>
        </header>
        <div className="card p-5">
          <fieldset disabled={work.busy} className="grid gap-4 md:grid-cols-3">
            <label className="field-label">
              시작일 (UTC)
              <input
                className="input"
                type="date"
                value={period.start}
                onChange={(event) => work.changePeriod({ start: event.target.value })}
              />
            </label>
            <label className="field-label">
              종료일 (UTC·미포함)
              <input
                className="input"
                type="date"
                value={period.end}
                onChange={(event) => work.changePeriod({ end: event.target.value })}
              />
            </label>
            <label className="field-label">
              초기 자본 (USDT)
              <input
                className="input"
                inputMode="decimal"
                value={period.capital}
                onChange={(event) => work.changePeriod({ capital: event.target.value })}
              />
            </label>
            <button
              type="button"
              className="btn btn-primary"
              disabled={work.dirty || !work.selected}
              onClick={() => work.backtest.mutate()}
            >
              {work.backtest.isPending ? "요청 중…" : "백테스트 실행"}
            </button>
          </fieldset>
          <p className="field-hint">
            1분봉 실행과 수수료·슬리피지·실제 펀딩 비율을 반영합니다. 봉 내부 체결 순서는 시나리오
            가정입니다.
          </p>
        </div>
      </section>
      <section className="section" aria-labelledby="code-demo-title">
        <header className="section-head">
          <h2 id="code-demo-title">3. 저장한 버전 데모 시작</h2>
        </header>
        <div className="card p-5 grid gap-4">
          <p className="field-hint">
            1시간 전략만 지원합니다. 시작하면 선택한 Bybit Demo 계정에 자동 주문을 보냅니다. 저장된
            버전을 고정하며, 원문을 새로 저장해도 실행 중 세션은 바뀌지 않습니다.
          </p>
          <label className="field-label">
            Bybit Demo 계정
            <select
              className="select"
              value={work.accountId}
              disabled={work.busy || work.accounts.isPending}
              onChange={(event) => work.setAccountId(event.target.value)}
            >
              <option value="">계정을 선택하세요</option>
              {work.demoAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.label ?? "Bybit Demo"} · {account.api_key_masked}
                </option>
              ))}
            </select>
          </label>
          {work.accounts.error ? <p role="alert">{describeApiError(work.accounts.error)}</p> : null}
          {!work.accounts.isPending && !work.accounts.error && work.demoAccounts.length === 0 ? (
            <p className="field-hint">
              주문 권한이 확인된 계정이 없습니다.{" "}
              <Link href="/trading">트레이딩에서 계정을 연결하세요.</Link>
            </p>
          ) : null}
          {draft.timeframe !== "1h" ? (
            <p className="field-hint">4시간·1일 전략은 백테스트만 지원합니다.</p>
          ) : null}
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              work.busy ||
              work.dirty ||
              !work.selected ||
              draft.timeframe !== "1h" ||
              !work.demoAccounts.some((account) => account.id === work.accountId)
            }
            onClick={() => work.demo.mutate()}
          >
            {work.demo.isPending ? "시작 중…" : "데모 자동매매 시작"}
          </button>
        </div>
      </section>
      {error ? (
        <p className="strip-note" role="alert">
          {describeApiError(error)}
        </p>
      ) : null}
      <section className="section" aria-labelledby="saved-code-title">
        <header className="section-head">
          <h2 id="saved-code-title">저장한 코드 전략</h2>
        </header>
        <div className="card p-5">
          <ul className="grid gap-3">
            {work.items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="btn"
                  disabled={work.busy}
                  onClick={() => work.load(item)}
                >
                  {item.name} · {CODE_LANGUAGE_LABELS[item.version.language]}
                </button>
              </li>
            ))}
          </ul>
          {work.items.length === 0 ? (
            <p className="dim">아직 저장한 코드 전략이 없습니다.</p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
