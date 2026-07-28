"use client";

import { MetricTile, type MetricTileTone } from "@/components/metric-tile";
import { StateBox } from "@/components/state-box";

import { useLiveSessionOutcomeParity } from "../hooks";
import type { OutcomeParityScope } from "../schemas";

type OutcomeParityPanelProps = {
  sessionId: string;
};

type ScopeKind = "session" | "strategy";

const UNAVAILABLE = "산출 불가";

function displayDecimal(value: string | null): string {
  return value ?? UNAVAILABLE;
}

function displayPercent(value: string | null): string {
  return value === null ? UNAVAILABLE : `${value}%`;
}

function decimalTone(value: string | null): MetricTileTone {
  if (value === null || value === "0" || value === "0.0") return "neutral";
  return value.startsWith("-") ? "neg" : "pos";
}

function ScopeParity({
  kind,
  title,
  scope,
}: {
  kind: ScopeKind;
  title: string;
  scope: OutcomeParityScope;
}) {
  const scopeId = `outcome-parity-${kind}`;

  return (
    <article className="rounded-md border p-4" data-testid={`${scopeId}-scope`}>
      <div className="mb-3">
        <h4 className="text-sm font-medium">{title}</h4>
        <p className="text-muted-foreground mt-1 text-xs">
          매칭 청산 {scope.matched_count}건의 전 관측 합입니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <MetricTile
          label="매칭 청산"
          value={`${scope.matched_count}건`}
          size="sm"
          valueTestId={`${scopeId}-matched-count`}
        />
        <MetricTile
          label="대조 커버리지"
          value={displayPercent(scope.coverage_pct)}
          size="sm"
          valueTestId={`${scopeId}-coverage`}
        />
        <MetricTile
          label="엔진 기대 gross"
          value={displayDecimal(scope.expected_gross)}
          tone={decimalTone(scope.expected_gross)}
          size="sm"
          sub="전 관측 합"
          valueTestId={`${scopeId}-expected-gross-total`}
        />
        <MetricTile
          label="거래소 확정 net"
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
          label="실효 비용률"
          value={displayPercent(scope.effective_cost_pct)}
          size="sm"
          valueTestId={`${scopeId}-effective-cost-pct`}
        />
      </div>

      <section className="mt-4 border-t pt-4" data-testid={`${scopeId}-waterfall`}>
        <h5 className="text-sm font-medium">분해 가능한 청산 워터폴</h5>
        <p className="text-muted-foreground mt-1 text-xs">
          비용을 분해할 수 있는 {scope.decomposable_count}건만 사용합니다.
        </p>
        <ol className="mt-3 space-y-2 font-mono text-sm tabular-nums">
          <li className="flex items-center justify-between gap-3">
            <span>엔진 기대 gross</span>
            <span data-testid={`${scopeId}-waterfall-expected`}>
              {displayDecimal(scope.decomposable_expected_gross)}
            </span>
          </li>
          <li className="flex items-center justify-between gap-3 border-t pt-2">
            <span>+ 체결 격차</span>
            <span data-testid={`${scopeId}-waterfall-execution-gap`}>
              {displayDecimal(scope.execution_gap)}
            </span>
          </li>
          <li className="flex items-center justify-between gap-3 border-t pt-2">
            <span>+ 비용</span>
            <span data-testid={`${scopeId}-waterfall-cost`}>{displayDecimal(scope.cost)}</span>
          </li>
          <li className="flex items-center justify-between gap-3 border-t pt-2 font-bold">
            <span>= 거래소 확정 net</span>
            <span data-testid={`${scopeId}-waterfall-actual-net`}>
              {displayDecimal(scope.decomposable_actual_net)}
            </span>
          </li>
        </ol>
      </section>

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

      <section className="mt-4 border-t pt-4">
        <h5 className="text-sm font-medium">커버리지 밖 관측</h5>
        <p className="text-muted-foreground mt-1 text-xs">
          이 수치는 워터폴에 섞지 않으며, 커버리지보다 클 수 있습니다.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <MetricTile
            label="엔진만 청산"
            value={`${scope.expected_only_count}건`}
            size="sm"
            sub={`gross ${scope.expected_only_gross}`}
            valueTestId={`${scopeId}-expected-only-count`}
          />
          <MetricTile
            label="거래소만 청산"
            value={`${scope.actual_only_count}건`}
            size="sm"
            sub={`net ${scope.actual_only_net}`}
            valueTestId={`${scopeId}-actual-only-count`}
          />
          <MetricTile
            label="비용 미분해 청산"
            value={`${scope.undecomposed_count}건`}
            size="sm"
            sub={`net ${scope.undecomposed_net}`}
            valueTestId={`${scopeId}-undecomposed-count`}
          />
          <MetricTile
            label="미귀속 원장 행"
            value={`${scope.unattributed_count}건`}
            size="sm"
            valueTestId={`${scopeId}-unattributed-count`}
          />
        </div>
      </section>
    </article>
  );
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

  if (data.session.matched_count === 0 && data.strategy.matched_count === 0) {
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
          엔진 기대값과 거래소 확정 청산을 매칭해 비교합니다. 커버리지가 낮으면 합계와 워터폴만으로
          전체 성과를 판단할 수 없습니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ScopeParity kind="session" title="세션 총계" scope={data.session} />
        <ScopeParity kind="strategy" title="전략 누적" scope={data.strategy} />
      </div>

      <section className="mt-4 border-t pt-4">
        <h4 className="text-sm font-medium">비용 가정 대조</h4>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <MetricTile
            label="백테스트 기본 왕복 비용"
            value={displayPercent(data.assumption.implied_round_trip_pct)}
            size="sm"
            sub="house default"
            valueTestId="outcome-parity-assumption-cost"
          />
          <MetricTile
            label="세션 실효 비용률"
            value={displayPercent(data.session.effective_cost_pct)}
            size="sm"
            valueTestId="outcome-parity-session-assumption-compare"
          />
          <MetricTile
            label="전략 누적 실효 비용률"
            value={displayPercent(data.strategy.effective_cost_pct)}
            size="sm"
            valueTestId="outcome-parity-strategy-assumption-compare"
          />
        </div>
        <p className="text-muted-foreground mt-3 text-xs">
          이 기본값은 귀하의 백테스트 설정과 다를 수 있습니다.
        </p>
      </section>
    </section>
  );
}
