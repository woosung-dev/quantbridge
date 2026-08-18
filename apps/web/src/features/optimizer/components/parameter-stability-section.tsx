"use client";

// 파라미터 안정성 (screen-10 03) — GridSearchResult.cells 에서 값별 평균 목표값을 파생해 막대로
// 보여 준다. 파생 규약·검증은 features/optimizer/param-stability.ts + 그 oracle 테스트 참조.
// 한 값만 솟아 있으면 그 결과가 우연일 확률이 크다는 걸 시각화하는 것이 목적이다.

import { deriveParamStability } from "@/features/optimizer/param-stability";
import { formatObjectiveValue } from "@/features/optimizer/format";
import type { GridSearchResult } from "@/features/optimizer/schemas";
import { OBJECTIVE_METRIC_LABEL } from "@/features/optimizer/labels";
import { EMPTY_CELL } from "@/lib/labels";

export function ParameterStabilitySection({ result }: { result: GridSearchResult }) {
  const stability = deriveParamStability(result.cells, result.param_names, result.direction);
  const metricLabel = OBJECTIVE_METRIC_LABEL[result.objective_metric];
  // 목표값 단위 SSOT — 평균·스케일·요약 줄 전부 같은 분기(ratio 지표 %, sharpe 소수)를 쓴다.
  const fmt = (v: number) => formatObjectiveValue(result.objective_metric, v);

  return (
    <section className="section" aria-label="파라미터 안정성">
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">03</span> 파라미터 안정성
        </p>
        <h2 className="section-title">값 하나에 기대고 있는가</h2>
        <p className="section-desc">
          파라미터 값별로 나머지 축을 가로질러 평균 {metricLabel}을 냈습니다. 한 값만 솟아 있으면 그
          결과는 우연일 확률이 큽니다.
        </p>
      </header>

      <div className="card">
        <div className="card-head">
          <div>
            <h3 className="card-title">값별 평균 {metricLabel}</h3>
            <p className="card-sub">
              각 막대는 해당 값을 가진 셀의 산술평균 · 거래 0건 셀은 평균에서 제외 · 축은 0 에서
              시작
            </p>
          </div>
        </div>

        {!stability.hasData ? (
          <div className="card-body">
            <p className="state-note" data-testid="param-stability-nodata">
              유효한 셀이 없어 안정성을 계산할 수 없습니다. 모든 조합이 거래 0건입니다.
            </p>
          </div>
        ) : (
          <div className="pgrid" data-testid="param-stability-grid">
            {stability.params.map((param) => (
              <div className="pcol" key={param.paramName}>
                <p className="pcol-title">{param.paramName}</p>

                {param.values.map((v) => (
                  <div className={v.isBest ? "prow best" : "prow"} key={v.value}>
                    <span className="plabel">
                      {param.paramName} {v.value}
                    </span>
                    {stability.canRenderBars ? (
                      <span className="pbar" aria-hidden="true">
                        <span style={{ width: `${v.widthPct}%` }} />
                      </span>
                    ) : (
                      <span aria-hidden="true" />
                    )}
                    <span className="pval">
                      {v.average === null ? EMPTY_CELL : fmt(v.average)}
                    </span>
                  </div>
                ))}

                {stability.canRenderBars ? (
                  <div className="pscale" aria-hidden="true">
                    <span />
                    <span className="pscale-in">
                      <span>{fmt(0)}</span>
                      <span>{fmt(stability.globalMaxAverage)}</span>
                    </span>
                    <span />
                  </div>
                ) : null}

                <p className="pfoot">
                  {param.highest && param.lowest ? (
                    <>
                      최고 {fmt(param.highest.average)} ({param.paramName}{" "}
                      {param.highest.value}) · 최저 {fmt(param.lowest.average)} (
                      {param.paramName} {param.lowest.value}) · 폭 {fmt(param.spread)}.
                    </>
                  ) : null}
                  {!stability.canRenderBars
                    ? " 목표값에 음수가 있어 0 기준 막대는 생략하고 값만 비교합니다."
                    : ""}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
