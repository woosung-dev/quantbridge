// 옵티마이저 실행 상세 — C 디자인 언어 이식 (W3-C, screen-10).
// 셸(.page/.report/.section/.card) + 실행 조건 + (grid) KPI·리더보드·히트맵 이중 렌더 + OOS 검증.
// grid 는 리더보드+히트맵 동일값 이중 렌더, bayesian/genetic 은 W1 라벨 경유 반복 이력 유지.
// 라벨은 전부 W1 용어 SSOT 경유(원시 enum 렌더 금지). 스키마가 받치지 않는 값은 그리지 않는다(§4.9).
"use client";

import { CheckIcon, AlertTriangleIcon, RefreshCwIcon, StarIcon } from "lucide-react";

import { extractBestParams } from "@/features/optimizer/best-params";
import { formatPercent } from "@/features/backtest/utils";
import { useOptimizationRun } from "@/features/optimizer/hooks";
import {
  BAYESIAN_PHASE_LABEL,
  BAYESIAN_PRIOR_LABEL,
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
  OPTIMIZATION_KIND_LABEL,
  OPTIMIZATION_STATUS_LABEL,
  OPTIMIZER_CELL_HEADER,
  OPTIMIZER_EMPTY_REASON,
  PARAM_FIELD_KIND_LABEL,
} from "@/features/optimizer/labels";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL, statusLabelOf } from "@/lib/labels";
import type {
  BayesianSearchResult,
  GeneticSearchResult,
  GridSearchResult,
  OptimizationRunResponse,
} from "@/features/optimizer/schemas";

import { BayesianBestParamsTable } from "./bayesian-best-params-table";
import { BayesianIterationChart } from "./bayesian-iteration-chart";
import { GeneticBestParamsTable } from "./genetic-best-params-table";
import { GeneticGenerationChart } from "./genetic-generation-chart";
import { GridSearchPairSelector } from "./grid-search-pair-selector";
import { OptimizerOosEvaluation } from "./optimizer-oos-evaluation";
import { ParameterStabilitySection } from "./parameter-stability-section";

const DETAIL_ENDPOINT = "GET /api/v1/optimizer/runs";

// 손익 톤 — 손익 데이터 전용 규율(양수 pos / 음수 neg / 0 중립). KPI 와 표 셀이 공유한다.
function pnlTone(v: number): string {
  if (v > 0) return " pos";
  if (v < 0) return " neg";
  return "";
}

// 손익 셀 색 — 표 셀(.num) 전용. 톤 규약은 pnlTone 하나로 통일.
function pnlClass(v: number): string {
  return `num${pnlTone(v)}`;
}

export function OptimizerRunDetail({ runId }: { runId: string }) {
  const { data, isLoading, error, refetch } = useOptimizationRun(runId);

  if (isLoading) {
    return (
      <main className="page">
        <div className="card">
          <div className="card-body" aria-busy="true">
            <span className="sk sk-line" style={{ width: "40%" }} />
            <span className="sk sk-line" style={{ width: "72%" }} />
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page">
        <div className="card">
          <div className="card-body">
            <StateBox
              tone="failed"
              testId="optimizer-detail-error"
              icon={<AlertTriangleIcon />}
              title="실행 상세를 불러오지 못했습니다."
              body="잠시 후 다시 시도해 주세요. 리더보드 숫자는 마지막으로 성공한 응답 이후 갱신되지 않았습니다."
              code={`${DETAIL_ENDPOINT}/${runId} · 503`}
            >
              <button className="btn btn-ghost btn-xs" type="button" onClick={() => refetch()}>
                <RefreshCwIcon aria-hidden="true" />
                다시 시도
              </button>
            </StateBox>
          </div>
        </div>
      </main>
    );
  }

  if (data == null) return null;

  const { label: statusLabel, tone: statusTone, showCheckIcon } = statusLabelOf(
    OPTIMIZATION_STATUS_LABEL,
    data.status,
  );
  const bestParams = data.status === "completed" ? extractBestParams(data.result) : null;

  return (
    <main className="page">
      {/* ===== 실행 헤더 ===== */}
      <section className="card" aria-label="최적화 실행 개요">
        <div className="report">
          <div>
            <h1 className="report-title">{OPTIMIZATION_KIND_LABEL[data.kind]}</h1>
            <div className="report-meta">
              <span className={CHIP_TONE_CLASS[statusTone]}>
                {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                {statusLabel}
              </span>
              <span className="chip">{OPTIMIZATION_KIND_LABEL[data.kind]}</span>
              <span className="chip">
                {OBJECTIVE_METRIC_LABEL[data.param_space.objective_metric]} ·{" "}
                {OBJECTIVE_DIRECTION_LABEL[data.param_space.direction]}
              </span>
              <span className="chip accent">바 단위 이벤트 루프</span>
              <span className="chip">{data.id.slice(0, 8)}</span>
              <span className="chip">{data.backtest_id.slice(0, 8)}</span>
            </div>
          </div>
        </div>
        {data.error_message ? (
          <p className="notice-inline" style={{ margin: "0 22px 18px" }} role="alert">
            <AlertTriangleIcon aria-hidden="true" />
            <span>{data.error_message}</span>
          </p>
        ) : null}
      </section>

      {/* ===== 01 실행 조건 (파라미터 공간 + 하이퍼파라미터) ===== */}
      <section className="section" aria-label="실행 조건">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 실행 조건
          </p>
          <h2 className="section-title">파라미터 공간</h2>
          <p className="section-desc">
            이 실행이 훑은 입력 변수 범위입니다. 목표 함수와 탐색 방식은 이 조건 아래에서
            평가됩니다.
          </p>
        </header>
        <div className="card">
          <div className="opt-param-space">
            {Object.entries(data.param_space.parameters).map(([name, field]) => (
              <div className="trust-row" key={name}>
                <span className="trust-key">{name}</span>
                <span className="trust-val">{describeField(field)}</span>
              </div>
            ))}
            {data.kind === "bayesian" ? (
              <>
                <div className="trust-row">
                  <span className="trust-key">획득 함수</span>
                  <span className="trust-val">
                    {data.param_space.bayesian_acquisition ?? EMPTY_CELL}
                  </span>
                </div>
                <div className="trust-row">
                  <span className="trust-key">초기 랜덤 탐색</span>
                  <span className="trust-val">
                    {data.param_space.bayesian_n_initial_random ?? EMPTY_CELL}
                  </span>
                </div>
                <div className="trust-row">
                  <span className="trust-key">최대 평가 횟수</span>
                  <span className="trust-val">{data.param_space.max_evaluations}</span>
                </div>
              </>
            ) : null}
            {data.kind === "genetic" ? (
              <>
                <div className="trust-row">
                  <span className="trust-key">개체군 크기</span>
                  <span className="trust-val">
                    {data.param_space.population_size ?? EMPTY_CELL}
                  </span>
                </div>
                <div className="trust-row">
                  <span className="trust-key">세대 수</span>
                  <span className="trust-val">
                    {data.param_space.n_generations ?? EMPTY_CELL}
                  </span>
                </div>
                <div className="trust-row">
                  <span className="trust-key">돌연변이율</span>
                  <span className="trust-val">
                    {data.param_space.mutation_rate ?? EMPTY_CELL}
                  </span>
                </div>
                <div className="trust-row">
                  <span className="trust-key">교차율</span>
                  <span className="trust-val">
                    {data.param_space.crossover_rate ?? EMPTY_CELL}
                  </span>
                </div>
                <div className="trust-row">
                  <span className="trust-key">최대 평가 횟수</span>
                  <span className="trust-val">{data.param_space.max_evaluations}</span>
                </div>
              </>
            ) : null}
          </div>
        </div>
      </section>

      {/* ===== 결과 (kind 분기) ===== */}
      {data.status === "completed" && data.result?.kind === "grid_search" ? (
        <>
          <GridResult result={data.result} />
          {/* 03 파라미터 안정성 — grid_search 완료 결과에만 (screen-10). */}
          <ParameterStabilitySection result={data.result} />
        </>
      ) : null}

      {data.status === "completed" && data.result?.kind === "bayesian" ? (
        <BayesianResult result={data.result} />
      ) : null}

      {data.status === "completed" && data.result?.kind === "genetic" ? (
        <GeneticResult result={data.result} />
      ) : null}

      {/* WFO 는 best_params 를 쓰지 않고 fold별 재최적화하지만, "옵티마이저가 유효 winner 를 찾음"
          휴리스틱 게이트로 best_params 존재를 사용(전 cell degenerate 시 OOS 무의미). */}
      {bestParams && Object.keys(bestParams).length > 0 ? (
        <OptimizerOosEvaluation
          backtestId={data.backtest_id}
          paramSpace={data.param_space}
          kind={data.kind}
          sectionNum={data.result?.kind === "grid_search" ? "04" : "03"}
        />
      ) : null}
    </main>
  );
}

// 파라미터 필드를 W1 라벨 경유 문자열로 변환 — 원시 kind 문자열 인쇄 금지.
function describeField(field: OptimizationRunResponse["param_space"]["parameters"][string]): string {
  if (field.kind === "integer" || field.kind === "decimal") {
    return `${PARAM_FIELD_KIND_LABEL[field.kind]} ${field.min} .. ${field.max} · 간격 ${field.step}`;
  }
  if (field.kind === "bayesian") {
    const scale = field.log_scale ? " · 로그 스케일" : "";
    return `${PARAM_FIELD_KIND_LABEL.bayesian} ${field.min} .. ${field.max} · 사전분포 ${BAYESIAN_PRIOR_LABEL[field.prior]}${scale}`;
  }
  return `${PARAM_FIELD_KIND_LABEL.categorical} ${field.values.join(", ")}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Grid 결과 — KPI + 리더보드(전 셀) + 히트맵 이중 렌더 (screen-10 01/02/04).
// ─────────────────────────────────────────────────────────────────────────────

function GridResult({ result }: { result: GridSearchResult }) {
  const bestIdx = result.best_cell_index;
  const bestCell = bestIdx !== null ? result.cells[bestIdx] : null;

  // 목표값 내림차순(최대화) / 오름차순(최소화). 축퇴(목표값 null)는 항상 맨 아래.
  const ranked = result.cells
    .map((cell, index) => ({ cell, index }))
    .sort((a, b) => {
      const av = a.cell.objective_value;
      const bv = b.cell.objective_value;
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return result.direction === "minimize" ? av - bv : bv - av;
    });

  return (
    <section className="section" aria-label="그리드 탐색 결과">
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">02</span> 결과
        </p>
        <h2 className="section-title">조합 {result.cells.length}개 전체 순위</h2>
        <p className="section-desc">
          목표 함수는 {OBJECTIVE_METRIC_LABEL[result.objective_metric]}입니다. 아래 KPI 는 최적
          셀 기준이고, 리더보드와 히트맵은 같은 값을 두 방식으로 보여 줍니다.
        </p>
      </header>

      {/* KPI — 최적 셀 기준 (스키마가 받치는 값만, 가짜 표시 상한 미터 없음). */}
      {bestCell ? (
        <div className="kpi-row">
          <article className="card kpi">
            <p className="kpi-label">최적 목표값</p>
            <p className="kpi-value mono">
              {bestCell.objective_value === null
                ? EMPTY_CELL
                : bestCell.objective_value.toFixed(2)}
            </p>
            <p className="kpi-foot">
              {OBJECTIVE_METRIC_LABEL[result.objective_metric]} ·{" "}
              {OBJECTIVE_DIRECTION_LABEL[result.direction]}
            </p>
          </article>
          <article className="card kpi">
            <p className="kpi-label">최적 셀 샤프 지수</p>
            <p className="kpi-value mono">
              {bestCell.sharpe === null ? EMPTY_CELL : bestCell.sharpe.toFixed(2)}
            </p>
            <p className="kpi-foot">거래 {bestCell.num_trades}건</p>
          </article>
          <article className="card kpi">
            <p className="kpi-label">최적 셀 총 수익률</p>
            {/* 엔진 ratio 컨벤션(-0.25 = -25%) — raw ratio 인쇄 금지, % 변환은 formatPercent SSOT. */}
            <p className={`kpi-value mono${pnlTone(bestCell.total_return)}`}>
              {formatPercent(bestCell.total_return)}
            </p>
            <p className="kpi-foot">초기 자본 대비</p>
          </article>
          <article className="card kpi">
            <p className="kpi-label">최적 셀 최대 낙폭</p>
            {/* 낙폭은 음수 또는 0 — pnlTone 규약(0 중립)으로 무낙폭이 neg 로 칠해지지 않는다. */}
            <p className={`kpi-value mono${pnlTone(bestCell.max_drawdown)}`}>
              {formatPercent(bestCell.max_drawdown)}
            </p>
            <p className="kpi-foot">최대 자본 하락폭</p>
          </article>
        </div>
      ) : null}

      {/* 02 리더보드 — 전 셀 순위 (축퇴 셀은 무데이터 + 맨 아래). */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-head">
          <div>
            <h3 className="card-title">조합 순위표</h3>
            <p className="card-sub">
              전체 {result.cells.length}행 · 같은 데이터, 같은 기간, 같은 실행 가정
            </p>
          </div>
        </div>
        <div className="table-wrap">
          <table
            className="trades"
            aria-label={`조합 순위표 ${result.cells.length}행`}
          >
            <thead>
              <tr>
                <th scope="col">{OPTIMIZER_CELL_HEADER.displayOrder}</th>
                {result.param_names.map((name) => (
                  <th scope="col" className="num" key={name}>
                    {name}
                  </th>
                ))}
                <th scope="col" className="num">
                  {OPTIMIZER_CELL_HEADER.sharpe}
                </th>
                <th scope="col" className="num">
                  {OPTIMIZER_CELL_HEADER.totalReturn}
                </th>
                <th scope="col" className="num">
                  {OPTIMIZER_CELL_HEADER.maxDrawdown}
                </th>
                <th scope="col" className="num">
                  {OPTIMIZER_CELL_HEADER.numTrades}
                </th>
              </tr>
            </thead>
            <tbody>
              {ranked.map(({ cell, index }, order) => {
                const isBest = index === bestIdx;
                const isDegenerate = cell.is_degenerate || cell.num_trades === 0;
                return (
                  <tr
                    key={index}
                    className={isBest ? "row-best" : isDegenerate ? "row-nodata" : undefined}
                    data-testid={`leaderboard-row-${index}`}
                  >
                    <td className="mono-l">
                      <span className="lb-rank">
                        {isDegenerate ? (
                          <span
                            className="dim"
                            title={OPTIMIZER_EMPTY_REASON.degenerateNoRank}
                          >
                            {EMPTY_CELL}
                          </span>
                        ) : (
                          <span className="lb-no">{order + 1}</span>
                        )}
                        {isBest ? (
                          <span className="chip accent">
                            <StarIcon aria-hidden="true" />
                            최적
                          </span>
                        ) : null}
                      </span>
                    </td>
                    {result.param_names.map((name) => (
                      <td className="num" key={name}>
                        {cell.param_values[name] ?? EMPTY_CELL}
                      </td>
                    ))}
                    <td className="num">
                      {cell.sharpe === null ? (
                        <span className="dim" title={OPTIMIZER_EMPTY_REASON.degenerateNoSharpe}>
                          {EMPTY_CELL}
                        </span>
                      ) : (
                        cell.sharpe.toFixed(2)
                      )}
                    </td>
                    {/* 수익률·낙폭은 raw ratio — formatPercent 로 % 인쇄 (KPI 와 동일 표기). */}
                    <td className={pnlClass(cell.total_return)}>{formatPercent(cell.total_return)}</td>
                    <td className={pnlClass(cell.max_drawdown)}>{formatPercent(cell.max_drawdown)}</td>
                    <td className="num">{cell.num_trades}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 04 히트맵 — 같은 값을 히트맵 배치로 다시 본다 (이중 렌더). */}
      <div className="card" style={{ marginTop: 16 }}>
        <details>
          <summary className="hm-sum">
            <svg
              className="hm-chev"
              viewBox="0 0 24 24"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="9 6 15 12 9 18" />
            </svg>
            히트맵 펼치기
            <span className="hm-tail">
              값 = {OBJECTIVE_METRIC_LABEL[result.objective_metric]}
            </span>
          </summary>
          <div className="hm-body">
            <GridSearchPairSelector result={result} />
          </div>
        </details>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Bayesian / Genetic 결과 — 반복 이력 유지 (W1 라벨 경유, C 표로 재스킨).
// ─────────────────────────────────────────────────────────────────────────────

function BayesianResult({ result }: { result: BayesianSearchResult }) {
  return (
    <section className="section" aria-label="베이지안 반복 이력">
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">02</span> 결과
        </p>
        <h2 className="section-title">베이지안 반복 이력</h2>
        <p className="section-desc">
          누적 최고값이 반복마다 어떻게 개선되는지 봅니다. 초기 랜덤 탐색 이후 획득 함수 단계로
          진입합니다.
        </p>
      </header>
      <div className="card">
        <div className="card-body">
          <BayesianIterationChart result={result} />
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-body">
          <BayesianBestParamsTable result={result} />
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="table-wrap">
          <table className="trades" aria-label={`베이지안 반복 ${result.iterations.length}행`}>
            <thead>
              <tr>
                <th scope="col" className="num">
                  #
                </th>
                <th scope="col">단계</th>
                <th scope="col">파라미터</th>
                <th scope="col" className="num">
                  목표값
                </th>
                <th scope="col" className="num">
                  누적 최고
                </th>
              </tr>
            </thead>
            <tbody>
              {result.iterations.map((it) => (
                <tr key={it.idx} className={it.idx === result.best_iteration_idx ? "row-best" : undefined}>
                  <td className="num">{it.idx}</td>
                  <td>{BAYESIAN_PHASE_LABEL[it.phase]}</td>
                  <td className="mono-l">
                    {Object.entries(it.params)
                      .map(([k, v]) => `${k}=${Number(v).toFixed(4)}`)
                      .join(", ")}
                  </td>
                  <td className="num">
                    {it.objective_value === null ? EMPTY_CELL : it.objective_value.toFixed(4)}
                  </td>
                  <td className="num">
                    {it.best_so_far === null ? EMPTY_CELL : it.best_so_far.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function GeneticResult({ result }: { result: GeneticSearchResult }) {
  return (
    <section className="section" aria-label="유전 알고리즘 세대 이력">
      <header className="section-head">
        <p className="eyebrow">
          <span className="num">02</span> 결과
        </p>
        <h2 className="section-title">유전 알고리즘 세대 이력</h2>
        <p className="section-desc">
          세대가 진행되며 누적 최고값이 어떻게 수렴하는지 봅니다.
        </p>
      </header>
      <div className="card">
        <div className="card-body">
          <GeneticGenerationChart result={result} />
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-body">
          <GeneticBestParamsTable result={result} />
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="table-wrap">
          <table className="trades" aria-label={`유전 알고리즘 반복 ${result.iterations.length}행`}>
            <thead>
              <tr>
                <th scope="col" className="num">
                  #
                </th>
                <th scope="col" className="num">
                  세대
                </th>
                <th scope="col">파라미터</th>
                <th scope="col" className="num">
                  목표값
                </th>
                <th scope="col" className="num">
                  누적 최고
                </th>
              </tr>
            </thead>
            <tbody>
              {result.iterations.map((it) => (
                <tr key={it.idx} className={it.idx === result.best_iteration_idx ? "row-best" : undefined}>
                  <td className="num">{it.idx}</td>
                  <td className="num">{it.generation}</td>
                  <td className="mono-l">
                    {Object.entries(it.params)
                      .map(([k, v]) => `${k}=${Number(v).toFixed(4)}`)
                      .join(", ")}
                  </td>
                  <td className="num">
                    {it.objective_value === null ? EMPTY_CELL : it.objective_value.toFixed(4)}
                  </td>
                  <td className="num">
                    {it.best_so_far === null ? EMPTY_CELL : it.best_so_far.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
