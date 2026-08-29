// 옵티마이저 진입 화면 — C 디자인 언어 이식 (W3-C, screen-09).
// 셸(.page/.report/.section/.card) + 01 최적화 제출 폼(.toolbar.opt-form) + 02 실행 목록(OptimizerRunList).
// 페이지명은 "옵티마이저"(OPTIMIZER_DOMAIN_LABEL.page, terminology B8), 실행 유형은 "최적화"(action).
"use client";

import { useMemo, useState } from "react";
import { PlusIcon } from "lucide-react";

import { SelectWithDisplayName } from "@/components/ui/select-with-display-name";
import { InfoIcon } from "@/components/info-icon";
import { useBacktests } from "@/features/backtest/hooks";
import {
  OPTIMIZATION_KIND_LABEL,
  OPTIMIZER_BACKTEST_PICKER_NOTE,
  OPTIMIZER_DOMAIN_LABEL,
  OPTIMIZER_LIMIT_NOTE,
} from "@/features/optimizer/labels";
import { useStrategyInputs } from "@/features/optimizer/use-strategy-inputs";

import { BayesianSearchForm } from "./bayesian-search-form";
import { GeneticSearchForm } from "./genetic-search-form";
import { GridSearchForm } from "./grid-search-form";
import { OptimizerRunList } from "./optimizer-run-list";

type Algorithm = "grid_search" | "bayesian" | "genetic";

const PICKER_LIMIT = 100;

// 방식별 평가 상한 힌트 — 셀렉트 옵션 라벨에 붙인다 (screen-09 셀렉트 관례).
const KIND_LIMIT_HINT: Record<Algorithm, string> = {
  grid_search: "최대 9조합",
  bayesian: "최대 100회 평가",
  genetic: "최대 100회 평가",
};

export function OptimizerPageView() {
  const [backtestId, setBacktestId] = useState("");
  const [algorithm, setAlgorithm] = useState<Algorithm>("grid_search");
  const [showForm, setShowForm] = useState(false);

  // P1-8 (S7-B): raw UUID paste 대신 useBacktests Select picker.
  // BacktestListQuery 는 status filter 미지원 → 클라 측에서 completed 만 필터.
  // useMemo 로 stable 변환 (H-1: RQ data 를 effect dep 로 직접 쓰지 않는다).
  const backtestsQuery = useBacktests({ limit: PICKER_LIMIT, offset: 0 });
  const completedOptions = useMemo(
    () =>
      (backtestsQuery.data?.items ?? [])
        .filter((b) => b.status === "completed")
        .map((b) => ({
          value: b.id,
          label: `${b.symbol} · ${b.timeframe} · ${b.id.slice(0, 8)}`,
        })),
    [backtestsQuery.data?.items],
  );
  const strategyId = (backtestsQuery.data?.items ?? []).find(
    (item) => item.id === backtestId,
  )?.strategy_id;
  const { inputs } = useStrategyInputs(strategyId);

  return (
    <main className="page">
      {/* ===== 헤더 ===== */}
      <section className="card" aria-label="옵티마이저 개요">
        <div className="report">
          <div>
            <h1 className="report-title">{OPTIMIZER_DOMAIN_LABEL.page}</h1>
            <p className="report-desc">
              그리드 탐색 · 베이지안 탐색 · 유전 알고리즘으로 전략 입력 변수 조합을 평가합니다.
              방식별로 평가 횟수 상한이 적용됩니다.
            </p>
            <div className="report-meta">
              <span className="chip">완료된 백테스트에서만 시작</span>
              <span className="chip">그리드 최대 9조합</span>
              <span className="chip">베이지안 · 유전 최대 100회 평가</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
        </div>
      </section>

      {/* ===== 01 최적화 제출 ===== */}
      <section className="section" aria-label="새 최적화 실행 시작">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 새 실행
          </p>
          <h2 className="section-title">{OPTIMIZER_DOMAIN_LABEL.action} 제출</h2>
          <p className="section-desc">
            이미 끝난 백테스트 하나를 고르고, 그 실행 조건을 그대로 둔 채 입력 변수만 바꿔 가며
            평가합니다.
          </p>
        </header>

        <div className="card">
          <div className="card-body">
            <div className="toolbar opt-form">
              <span className="field">
                <span className="field-label" id="lbl-target">
                  대상 백테스트
                </span>
                <SelectWithDisplayName
                  options={completedOptions}
                  value={backtestId}
                  onValueChange={(v) => {
                    setBacktestId(v);
                    setShowForm(false);
                  }}
                  placeholder={
                    backtestsQuery.isLoading
                      ? "백테스트 로딩 중"
                      : completedOptions.length === 0
                        ? "완료된 백테스트 없음"
                        : "백테스트 선택 (완료됨)"
                  }
                  ariaLabel="백테스트 선택"
                />
              </span>

              <span className="field">
                <span className="field-label" id="lbl-kind">
                  방식
                </span>
                <select
                  className="select"
                  value={algorithm}
                  onChange={(e) => {
                    setAlgorithm(e.target.value as Algorithm);
                    setShowForm(false);
                  }}
                  aria-label="최적화 알고리즘"
                >
                  <option value="grid_search">
                    {OPTIMIZATION_KIND_LABEL.grid_search} ({KIND_LIMIT_HINT.grid_search})
                  </option>
                  <option value="bayesian">
                    {OPTIMIZATION_KIND_LABEL.bayesian} ({KIND_LIMIT_HINT.bayesian})
                  </option>
                  <option value="genetic">
                    {OPTIMIZATION_KIND_LABEL.genetic} ({KIND_LIMIT_HINT.genetic})
                  </option>
                </select>
              </span>

              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setShowForm((v) => !v)}
                disabled={backtestId.length === 0}
              >
                <PlusIcon aria-hidden="true" />
                {showForm ? "폼 닫기" : `${OPTIMIZATION_KIND_LABEL[algorithm]} 새 실행`}
              </button>
            </div>

            {showForm && backtestId && algorithm === "grid_search" && (
              <GridSearchForm
                backtestId={backtestId}
                inputs={inputs}
                onSuccess={() => setShowForm(false)}
              />
            )}
            {showForm && backtestId && algorithm === "bayesian" && (
              <BayesianSearchForm
                backtestId={backtestId}
                inputs={inputs}
                onSuccess={() => setShowForm(false)}
              />
            )}
            {showForm && backtestId && algorithm === "genetic" && (
              <GeneticSearchForm
                backtestId={backtestId}
                inputs={inputs}
                onSuccess={() => setShowForm(false)}
              />
            )}

            <p className="chart-note">
              <InfoIcon />
              {OPTIMIZER_LIMIT_NOTE}
            </p>
            <p className="chart-note" style={{ paddingTop: 0 }}>
              <InfoIcon />
              {OPTIMIZER_BACKTEST_PICKER_NOTE}
            </p>
          </div>
        </div>
      </section>

      {/* ===== 02 실행 목록 ===== */}
      <section className="section" aria-label="최적화 실행 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 목록
          </p>
          <h2 className="section-title">최근 실행</h2>
          <p className="section-desc">
            최근 생성순입니다. 아직 끝나지 않은 실행은 결과 열이 비어 있습니다.
          </p>
        </header>
        <OptimizerRunList limit={10} />
      </section>
    </main>
  );
}
