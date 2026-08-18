// 옵티마이저 실행 목록 — C 디자인 언어 이식 (W3-C, screen-09 02 목록).
// 프로토타입 screen-09 의 시맨틱 CSS(table.trades.opt-table · run-id/run-main/run-sub/run-note ·
// col-status)를 소비하되, 열은 실데이터(OptimizationRunResponse)가 받치는 것만 그린다.
// §4.9 미렌더: 대상 백테스트의 "SOL/USDT · 1h" 부제는 목록 응답에 백테스트 조인이 없어(backtest_id
// 만 존재) 그리지 않는다. 실행 ID·대상 백테스트는 실 UUID 8자 단축형만 인쇄한다.
// 라벨·톤은 W1 용어 SSOT(OPTIMIZATION_*_LABEL) → CHIP_TONE_CLASS 로만 파생한다(원시 enum 렌더 금지).
"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangleIcon, InboxIcon, RefreshCwIcon } from "lucide-react";

import { useOptimizationRuns } from "@/features/optimizer/hooks";
import {
  OBJECTIVE_DIRECTION_LABEL,
  OBJECTIVE_METRIC_LABEL,
  OPTIMIZATION_KIND_LABEL,
  OPTIMIZATION_STATUS_LABEL,
  OPTIMIZER_EMPTY_REASON,
  OPTIMIZER_LIST_ERROR_STATE,
  OPTIMIZER_LIST_HEADER,
} from "@/features/optimizer/labels";
import { formatDateTime } from "@/features/backtest/utils";
import { formatObjectiveValue } from "@/features/optimizer/format";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL, statusLabelOf } from "@/lib/labels";
import type {
  OptimizationRunResponse,
  OptimizationStatus,
} from "@/features/optimizer/schemas";

// 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const LIST_ENDPOINT = "GET /api/v1/optimizer/runs";

// 페이지당 요청 개수 토글 값 (screen-09 02 목록 · role=group + aria-pressed).
const PAGE_SIZES = [10, 25, 50] as const;

// grid 는 cell objective, bayesian/genetic 은 best_iteration objective_value 로 최고 목표값 파생.
function bestObjectiveOf(r: OptimizationRunResponse): number | null {
  if (r.result?.kind === "grid_search" && r.result.best_cell_index !== null) {
    return r.result.cells[r.result.best_cell_index]?.objective_value ?? null;
  }
  if (r.result?.kind === "bayesian" && r.result.best_iteration_idx !== null) {
    return r.result.best_objective_value;
  }
  if (r.result?.kind === "genetic" && r.result.best_iteration_idx !== null) {
    return r.result.best_objective_value;
  }
  return null;
}

// 최고 목표값이 비었을 때의 사유 title — 상태별로 다르다 (§4.9 · W1 사유 SSOT).
function bestEmptyTitle(status: OptimizationStatus): string {
  switch (status) {
    case "queued":
      return OPTIMIZER_EMPTY_REASON.queuedNotStarted;
    case "running":
      return OPTIMIZER_EMPTY_REASON.runningNoIntermediate;
    case "failed":
      return OPTIMIZER_EMPTY_REASON.failedInvalidRange;
    default:
      return OPTIMIZER_EMPTY_REASON.degenerateNoSharpe;
  }
}

// 상태 셀 보조 문구 — 대기/실행 중만 인쇄한다(§4.9: 진행률·ETA·큐 순번 금지).
function statusNoteOf(status: OptimizationStatus): string | null {
  if (status === "queued") return OPTIMIZER_EMPTY_REASON.queuedNoQueuePosition;
  if (status === "running") return OPTIMIZER_EMPTY_REASON.runningNoIntermediate;
  return null;
}

export function OptimizerRunList({
  limit = 10,
  backtestId,
}: {
  limit?: number;
  backtestId?: string;
}) {
  // 페이지당 요청 개수는 토글로 바뀐다(초기값 = limit prop). 값 변경 시 queryKey 가 바뀌어 재조회.
  const [pageSize, setPageSize] = useState<number>(
    (PAGE_SIZES as readonly number[]).includes(limit) ? limit : 10,
  );
  const { data, isLoading, error, refetch } = useOptimizationRuns({
    limit: pageSize,
    offset: 0,
    backtest_id: backtestId,
  });

  const {
    runId: hRunId,
    kind: hKind,
    backtest: hBacktest,
    objective: hObjective,
    bestObjective: hBest,
    status: hStatus,
    createdAt: hCreated,
    action: hAction,
  } = OPTIMIZER_LIST_HEADER;

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const skipped = data?.skipped_count ?? 0;

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">최적화 실행</h3>
          <p className="card-sub">
            {items.length}건 표시{total > items.length ? ` · 전체 ${total}건 중` : ""}
          </p>
        </div>
        {/* 페이지당 요청 개수 토글 — 패널을 바꾸지 않는 상호배타 버튼이라 role=group + aria-pressed (§3-6). */}
        <div className="chart-head-actions">
          <div className="tabs" role="group" aria-label="페이지당 요청 개수">
            {PAGE_SIZES.map((size) => (
              <button
                key={size}
                type="button"
                className={"tab" + (size === pageSize ? " active" : "")}
                aria-pressed={size === pageSize}
                data-testid={`optimizer-pagesize-${size}`}
                onClick={() => setPageSize(size)}
              >
                {size}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Sprint 62 T-1 (BL-350/354): skipped_count > 0 시 graceful warn 인라인 고지. */}
      {skipped > 0 ? (
        <p
          className="notice-inline"
          style={{ margin: "16px 22px 0" }}
          role="status"
          data-testid="optimizer-skipped-warn"
        >
          <AlertTriangleIcon aria-hidden="true" />
          <span>
            이전 데이터 형식 불일치로 <span className="mono">{skipped}</span>개 항목이 표시되지
            않습니다.
          </span>
        </p>
      ) : null}

      {isLoading ? (
        <ListSkeleton />
      ) : error ? (
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="optimizer-error"
            icon={<AlertTriangleIcon />}
            title={OPTIMIZER_LIST_ERROR_STATE.headline}
            body={OPTIMIZER_LIST_ERROR_STATE.description}
            code={`${LIST_ENDPOINT} · 500`}
          >
            <button className="btn btn-ghost btn-xs" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        </div>
      ) : items.length === 0 ? (
        <div className="card-body">
          <StateBox
            testId="optimizer-empty"
            icon={<InboxIcon />}
            title="최적화 실행 이력이 없습니다."
            body="완료된 백테스트를 대상으로 첫 최적화를 제출하면 이곳에 실행 이력이 쌓입니다."
          />
        </div>
      ) : (
        <div className="table-wrap">
          <table className="trades opt-table" aria-label={`최적화 실행 목록 ${items.length}건`}>
            <thead>
              <tr>
                <th scope="col">{hRunId}</th>
                <th scope="col">{hKind}</th>
                <th scope="col">{hBacktest}</th>
                <th scope="col">{hObjective}</th>
                <th scope="col" className="num">
                  {hBest}
                </th>
                <th scope="col" className="col-status">
                  {hStatus}
                </th>
                <th scope="col">{hCreated}</th>
                <th scope="col">{hAction}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => {
                // 라벨·톤은 W1 용어 SSOT 에서만 온다 (원시 enum 렌더 금지 — no-raw-enum-labels 가드).
                const { label: statusLabel, tone: statusTone } = statusLabelOf(
                  OPTIMIZATION_STATUS_LABEL,
                  r.status,
                );
                const best = bestObjectiveOf(r);
                const note = statusNoteOf(r.status);
                return (
                  <tr key={r.id} data-testid={`optimizer-row-${r.id}`} data-status={r.status}>
                    <td className="mono-l run-id">
                      <Link href={`/optimizer/${r.id}`}>{r.id.slice(0, 8)}</Link>
                    </td>
                    <td>
                      <span className="run-main">{OPTIMIZATION_KIND_LABEL[r.kind]}</span>
                      <span className="run-sub">
                        최대 평가 {r.param_space.max_evaluations}회
                      </span>
                    </td>
                    {/* §4.9: 백테스트 조인(심볼·주기)이 목록 응답에 없어 backtest_id 8자만 인쇄한다. */}
                    <td className="mono-l">{r.backtest_id.slice(0, 8)}</td>
                    <td>
                      <span className="run-main">
                        {OBJECTIVE_METRIC_LABEL[r.param_space.objective_metric]}
                      </span>
                      <span className="run-sub">
                        {OBJECTIVE_DIRECTION_LABEL[r.param_space.direction]} 기준
                      </span>
                    </td>
                    <td className="num">
                      {/* 목표값 단위 SSOT — ratio 지표(총 수익률·최대 낙폭)는 %, sharpe 는 소수. */}
                      {best === null ? (
                        <span className="dim" title={bestEmptyTitle(r.status)}>
                          {EMPTY_CELL}
                        </span>
                      ) : (
                        formatObjectiveValue(r.param_space.objective_metric, best)
                      )}
                    </td>
                    <td className="col-status">
                      <span className={CHIP_TONE_CLASS[statusTone]}>{statusLabel}</span>
                      {note ? <span className="run-note">{note}</span> : null}
                    </td>
                    <td className="mono-l dim">{formatDateTime(r.created_at)}</td>
                    <td>
                      <Link className="btn btn-ghost btn-xs" href={`/optimizer/${r.id}`}>
                        상세
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 표 아래 ETA 미표시 안내 — 이 화면의 가장 중요한 문장 (§4.9 인쇄 금지 근거). */}
      {!isLoading && !error && items.length > 0 ? (
        <p className="chart-note no-eta">
          <RefreshCwIcon aria-hidden="true" />
          <span>
            <strong>{OPTIMIZER_EMPTY_REASON.noEtaByDesign}</strong> 실행 중 작업은 새로
            고쳐야 상태가 갱신됩니다. 최적화는 서버가 진행률을 보고하지 않아 미터를 그리지
            않습니다.
          </span>
        </p>
      ) : null}
    </div>
  );
}

// 목록을 불러오는 동안의 스켈레톤 — 프로토타입 aria-busy tbody 관례 (.sk .sk-cell).
function ListSkeleton() {
  return (
    <div className="table-wrap" data-testid="optimizer-skeleton" aria-busy="true" aria-hidden="true">
      <table className="trades opt-table">
        <tbody>
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 8 }).map((__, j) => (
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
