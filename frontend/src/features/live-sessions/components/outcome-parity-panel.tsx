"use client";

import { MetricTile, type MetricTileTone } from "@/components/metric-tile";
import { StateBox } from "@/components/state-box";
import { Badge } from "@/components/ui/badge";

import { useLiveSessionOutcomeParity } from "../hooks";
import type { OutcomeParityScope } from "../schemas";

type OutcomeParityPanelProps = {
  sessionId: string;
};

type ScopeKind = "session" | "strategy";

const UNAVAILABLE = "산출 불가";
// 이 값 미만이면 대조가 원장의 소수 위에서만 성립한다.
const MATCH_COVERAGE_WARNING_THRESHOLD = 80;

function parsedNumber(value: string | null): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function displayDecimal(value: string | null): string {
  return value ?? UNAVAILABLE;
}

function displayPercent(value: string | null): string {
  const parsed = parsedNumber(value);
  if (parsed === null) return UNAVAILABLE;

  const absolute = Math.abs(parsed);
  const fractionDigits = absolute === 0 || absolute >= 1 ? 2 : 4;
  return `${parsed.toFixed(fractionDigits)}%`;
}

function decimalTone(value: string | null): MetricTileTone {
  const parsed = parsedNumber(value);
  if (parsed === null || parsed === 0) return "neutral";
  return parsed < 0 ? "neg" : "pos";
}

function coverageTone(value: string | null): MetricTileTone {
  const parsed = parsedNumber(value);
  return parsed !== null && parsed < MATCH_COVERAGE_WARNING_THRESHOLD ? "warn" : "neutral";
}

function ScopeParity({
  kind,
  scope,
  ledgerSupported,
  strategySessionCount,
}: {
  kind: ScopeKind;
  scope: OutcomeParityScope;
  ledgerSupported: boolean;
  strategySessionCount: number;
}) {
  const scopeId = `outcome-parity-${kind}`;
  const scopeLabel = kind === "session" ? "세션 총계" : "전략 누적";
  const badgeLabel = kind === "session" ? "요청 세션" : `세션 ${strategySessionCount}건`;
  const hasPartialDecomposition = scope.decomposable_count < scope.matched_count;

  return (
    <article className="rounded-md border p-4" data-testid={`${scopeId}-scope`}>
      <div className="mb-3 flex items-center gap-2">
        <h4 className="text-sm font-medium">{scopeLabel}</h4>
        <Badge variant="outline" data-testid={`${scopeId}-scope-badge`}>
          {badgeLabel}
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <MetricTile
          label={`매칭 청산 (${scopeLabel})`}
          value={`${scope.matched_count}건`}
          size="sm"
          valueTestId={`${scopeId}-matched-count`}
        />
        <MetricTile
          label="매칭 커버리지"
          value={displayPercent(scope.match_coverage_pct)}
          tone={coverageTone(scope.match_coverage_pct)}
          size="sm"
          valueTestId={`${scopeId}-coverage`}
        />
        <MetricTile
          label={`엔진 기대 gross (${scopeLabel})`}
          value={displayDecimal(scope.expected_gross)}
          tone={decimalTone(scope.expected_gross)}
          size="sm"
          sub="전 관측 합"
          valueTestId={`${scopeId}-expected-gross-total`}
        />
        <MetricTile
          label={`거래소 확정 net (${scopeLabel})`}
          value={displayDecimal(scope.actual_net)}
          tone={decimalTone(scope.actual_net)}
          size="sm"
          sub="전 관측 합"
          valueTestId={`${scopeId}-actual-net-total`}
        />
        <MetricTile
          label="왕복 notional"
          value={displayDecimal(scope.round_trip_notional)}
          size="sm"
          valueTestId={`${scopeId}-round-trip-notional`}
        />
        <MetricTile
          label="실효 비용률 (편도)"
          value={displayPercent(scope.effective_cost_pct_per_leg)}
          size="sm"
          valueTestId={`${scopeId}-effective-cost-pct-per-leg`}
        />
        <MetricTile
          label="실효 비용률 (왕복)"
          value={displayPercent(scope.effective_cost_pct_round_trip)}
          size="sm"
          valueTestId={`${scopeId}-effective-cost-pct-round-trip`}
        />
      </div>

      {ledgerSupported ? (
        <section className="mt-4 border-t pt-4" data-testid={`${scopeId}-waterfall`}>
          <MetricTile
            label="비용 분해 커버리지"
            value={displayPercent(scope.decomposition_coverage_pct)}
            tone={coverageTone(scope.decomposition_coverage_pct)}
            size="sm"
            variant="bare"
            valueTestId={`${scopeId}-decomposition-coverage`}
          />
          {hasPartialDecomposition ? (
            <p className="text-muted-foreground mt-1 text-xs" data-testid={`${scopeId}-waterfall-note`}>
              이 막대는 매칭 {scope.matched_count}건 중 {scope.decomposable_count}건만 반영합니다.
            </p>
          ) : null}
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <h5 className="text-sm font-medium">분해 가능한 청산 워터폴</h5>
              <ol className="mt-3 space-y-2 font-mono text-sm tabular-nums">
                <li className="flex items-center justify-between gap-3">
                  <span>엔진 기대 gross (분해 가능분)</span>
                  <span data-testid={`${scopeId}-waterfall-expected`}>
                    {displayDecimal(scope.decomposable_expected_gross)}
                  </span>
                </li>
                <li className="flex items-center justify-between gap-3 border-t pt-2">
                  <span>+ 체결 격차 (분해 가능분)</span>
                  <span data-testid={`${scopeId}-waterfall-execution-gap`}>
                    {displayDecimal(scope.execution_gap)}
                  </span>
                </li>
                <li className="flex items-center justify-between gap-3 border-t pt-2">
                  <span>+ 비용 (수수료·펀딩 등 잔차)</span>
                  <span data-testid={`${scopeId}-waterfall-cost`}>{displayDecimal(scope.cost)}</span>
                </li>
                <li className="flex items-center justify-between gap-3 border-t pt-2 font-bold">
                  <span>= 거래소 확정 net (분해 가능분)</span>
                  <span data-testid={`${scopeId}-waterfall-actual-net`}>
                    {displayDecimal(scope.decomposable_actual_net)}
                  </span>
                </li>
              </ol>
              <p className="text-muted-foreground mt-3 text-xs">
                거래소 원장이 수수료와 펀딩을 나눠 주지 않아 합쳐서 표시합니다.
              </p>
            </div>
            <MetricTile
              label="매칭됐으나 비용 분해 불가"
              value={`${scope.undecomposed_count}건`}
              size="sm"
              sub={`net ${scope.undecomposed_net}. 매칭 안에 포함되어 커버리지에서 이중 차감하지 않습니다.`}
              valueTestId={`${scopeId}-undecomposed-count`}
            />
          </div>
        </section>
      ) : (
        <section className="mt-4 border-t pt-4" data-testid={`${scopeId}-ledger-unsupported`}>
          <StateBox
            testId={`${scopeId}-ledger-unsupported-message`}
            title="이 거래소는 청산 원장 적재가 아직 지원되지 않아 비용 분해를 할 수 없습니다."
          />
        </section>
      )}

      {scope.sample_sufficient ? (
        <section className="mt-4 border-t pt-4" data-testid={`${scopeId}-performance`}>
          <h5 className="text-sm font-medium">표본 기반 성과</h5>
          <p className="text-muted-foreground mt-1 text-xs">
            표본 {scope.sample_n}건 기준 근사입니다.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <MetricTile
              label="표본 평균 순손익"
              value={displayDecimal(scope.sample_mean_net)}
              tone={decimalTone(scope.sample_mean_net)}
              size="sm"
              valueTestId={`${scopeId}-sample-mean-net`}
            />
            <MetricTile
              label="표본 순손익 표준편차"
              value={displayDecimal(scope.sample_sd_net)}
              size="sm"
              valueTestId={`${scopeId}-sample-sd-net`}
            />
          </div>
        </section>
      ) : (
        <section className="mt-4 border-t pt-4" data-testid={`${scopeId}-performance-blocked`}>
          <h5 className="text-sm font-medium">표본 기반 성과</h5>
          <p className="text-muted-foreground mt-1 text-xs">
            표본 {scope.sample_n}건 기준으로는 성과 비율을 표시하지 않습니다.
          </p>
          <p className="text-muted-foreground mt-1 text-xs">
            {scope.sample_required_n === null
              ? `현재 표본 ${scope.sample_n}건. 필요 표본 수는 아직 산출할 수 없음.`
              : `현재 표본 ${scope.sample_n}건, 필요 표본 ${scope.sample_required_n}건.`}
          </p>
        </section>
      )}

      <section className="mt-4 border-t pt-4" data-testid={`${scopeId}-outside-coverage`}>
        <h5 className="text-sm font-medium">커버리지 밖 관측</h5>
        <p className="text-muted-foreground mt-1 text-xs">
          이 수치는 워터폴에 섞지 않으며, 매칭 커버리지보다 클 수 있습니다.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <MetricTile
            label="엔진만 청산"
            value={`${scope.expected_only_count}건`}
            size="sm"
            sub={`gross ${scope.expected_only_gross}. 대기 ${scope.expected_only_pending_count}건 · 실패 ${scope.expected_only_failed_count}건 · 발주 ${scope.expected_only_dispatched_count}건`}
            valueTestId={`${scopeId}-expected-only-count`}
          />
          <MetricTile
            label="거래소만 청산"
            value={`${scope.actual_only_count}건`}
            size="sm"
            sub={`net ${scope.actual_only_net}`}
            valueTestId={`${scopeId}-actual-only-count`}
          />
        </div>
      </section>
    </article>
  );
}

function scopeHasOutsideCoverage(scope: OutcomeParityScope): boolean {
  return scope.expected_only_count > 0 || scope.actual_only_count > 0;
}

export function OutcomeParityPanel({ sessionId }: OutcomeParityPanelProps) {
  const { data, isError, isLoading, refetch } = useLiveSessionOutcomeParity(sessionId);

  if (isLoading) {
    return (
      <StateBox testId="outcome-parity-loading" title="라이브 결과 대조를 불러오는 중입니다." />
    );
  }

  if (isError) {
    return (
      <StateBox
        tone="failed"
        testId="outcome-parity-error"
        title="라이브 결과 대조를 불러오지 못했습니다."
        body="네트워크 또는 서버 상태를 확인한 뒤 다시 시도하세요."
        code={`GET /api/v1/live-sessions/${sessionId}/outcome-parity`}
      >
        <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
          다시 시도
        </button>
      </StateBox>
    );
  }

  if (!data) {
    return (
      <StateBox
        testId="outcome-parity-no-data"
        title="라이브 결과 대조 데이터를 아직 받을 수 없습니다."
      />
    );
  }

  const hasMatchedClosures = data.session.matched_count > 0 || data.strategy.matched_count > 0;
  const hasOutsideCoverage =
    scopeHasOutsideCoverage(data.session) ||
    scopeHasOutsideCoverage(data.strategy) ||
    data.unattributed_count > 0;
  const strategyUnconfirmedCount = data.strategy.expected_only_count;

  if (!hasMatchedClosures && !hasOutsideCoverage) {
    return (
      <StateBox
        testId="outcome-parity-empty"
        title="아직 대조할 청산이 없습니다."
        body="엔진 청산과 거래소 확정 청산이 매칭되면 여기에서 비교합니다."
      />
    );
  }

  return (
    <section className="rounded-md border p-4" data-testid="outcome-parity-panel">
      <div className="mb-4">
        <h3 className="font-medium">라이브 세션 성과 대조</h3>
        <p className="text-muted-foreground mt-1 text-xs">
          엔진 기대값과 거래소 확정 청산을 매칭해 비교합니다. 매칭 커버리지가 낮으면 합계와
          워터폴만으로 전체 성과를 판단할 수 없습니다.
        </p>
      </div>

      {!hasMatchedClosures ? (
        <StateBox
          testId="outcome-parity-unmatched-warning"
          title={
            strategyUnconfirmedCount > 0
              ? `대조된 청산은 없고 미확정만 ${strategyUnconfirmedCount}건 있습니다.`
              : "대조된 청산은 없고 계정 원장 진단이 필요한 관측이 있습니다."
          }
          body="아래 버킷과 커버리지를 확인해 매칭되지 않은 관측을 점검하세요."
        />
      ) : null}

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ScopeParity
          kind="session"
          scope={data.session}
          ledgerSupported={data.ledger_supported}
          strategySessionCount={data.strategy_session_count}
        />
        <ScopeParity
          kind="strategy"
          scope={data.strategy}
          ledgerSupported={data.ledger_supported}
          strategySessionCount={data.strategy_session_count}
        />
      </div>

      <section className="mt-4 border-t pt-4" data-testid="outcome-parity-account-diagnostic">
        <h4 className="text-sm font-medium">계정 원장 진단</h4>
        {data.ledger_supported ? (
          <p className="text-muted-foreground mt-1 text-xs">
            미귀속 원장 행 (계정 전체, 기간 무관): {data.unattributed_count}건. 같은 청산이 계정
            행마다 중복 적재될 수 있어 실제 청산 수보다 클 수 있습니다.
          </p>
        ) : (
          <p className="text-muted-foreground mt-1 text-xs">
            미귀속 원장 행 (계정 전체, 기간 무관)은 이 거래소에서 청산 원장 적재가 지원되기 전까지
            판정할 수 없습니다.
          </p>
        )}
      </section>

      <section className="mt-4 border-t pt-4">
        <h4 className="text-sm font-medium">비용 가정 대조</h4>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricTile
            label="엔진 기본 가정 (귀하의 백테스트 설정이 아닙니다)"
            value={displayPercent(data.assumption.implied_round_trip_pct)}
            size="sm"
            sub="taker 왕복 비용"
            valueTestId="outcome-parity-assumption-cost"
          />
          <MetricTile
            label="TP 지정가 청산 maker 수수료"
            value={displayPercent(data.assumption.maker_fee_pct)}
            size="sm"
            valueTestId="outcome-parity-assumption-maker-fee"
          />
          <MetricTile
            label="세션 실효 비용률 (왕복)"
            value={displayPercent(data.session.effective_cost_pct_round_trip)}
            size="sm"
            valueTestId="outcome-parity-session-assumption-compare"
          />
          <MetricTile
            label="전략 누적 실효 비용률 (왕복)"
            value={displayPercent(data.strategy.effective_cost_pct_round_trip)}
            size="sm"
            valueTestId="outcome-parity-strategy-assumption-compare"
          />
        </div>
        <p className="text-muted-foreground mt-3 text-xs">
          TP 지정가 청산은 maker 수수료라 이 왕복 가정은 과대계상입니다.
        </p>
      </section>
    </section>
  );
}
