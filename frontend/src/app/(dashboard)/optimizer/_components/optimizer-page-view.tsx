// Optimizer 진입 페이지 (실행 list + Grid Search / Bayesian / Genetic 선택).
"use client";

// Optimizer 진입 화면 본문 (client) — 실행 list + Grid/Bayesian/Genetic 폼 선택. page.tsx(server) 가 렌더.

import { useMemo, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBacktests } from "@/features/backtest/hooks";

import { BayesianSearchForm } from "./bayesian-search-form";
import { GeneticSearchForm } from "./genetic-search-form";
import { GridSearchForm } from "./grid-search-form";
import { OptimizerRunList } from "./optimizer-run-list";

type Algorithm = "grid_search" | "bayesian" | "genetic";

const ALGORITHM_LABEL: Record<Algorithm, string> = {
  grid_search: "그리드 탐색 새 실행",
  bayesian: "베이지안 탐색 새 실행",
  genetic: "유전 알고리즘 새 실행",
};

const PICKER_LIMIT = 100;

export function OptimizerPageView() {
  const [backtestId, setBacktestId] = useState("");
  const [algorithm, setAlgorithm] = useState<Algorithm>("grid_search");
  const [showForm, setShowForm] = useState(false);

  // P1-8 (S7-B): raw UUID paste 대신 useBacktests Select picker.
  // BacktestListQuery 는 status filter 미지원 → 클라 측에서 completed 만 필터.
  // useEffect dep 폭주 회피 위해 useMemo 로 stable 변환.
  const backtestsQuery = useBacktests({ limit: PICKER_LIMIT, offset: 0 });
  const completedOptions = useMemo(
    () =>
      (backtestsQuery.data?.items ?? [])
        .filter((b) => b.status === "completed")
        .map((b) => ({
          id: b.id,
          label: `${b.symbol} · ${b.timeframe} · ${b.id.slice(0, 8)}`,
        })),
    [backtestsQuery.data?.items],
  );

  return (
    <main className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold text-foreground">파라미터 최적화</h1>
        <p className="text-sm text-muted-foreground">
          그리드 탐색·베이지안 탐색·유전 알고리즘으로 전략의 입력 변수 조합을
          평가합니다. 방식별로 평가 횟수 상한이 적용됩니다.
        </p>
      </header>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-[240px]">
            <Select
              value={backtestId || undefined}
              onValueChange={(v) => {
                setBacktestId(v ?? "");
                setShowForm(false);
              }}
            >
              <SelectTrigger aria-label="백테스트 선택">
                <SelectValue
                  placeholder={
                    backtestsQuery.isLoading
                      ? "백테스트 로딩 중…"
                      : completedOptions.length === 0
                        ? "완료된 백테스트 없음"
                        : "백테스트 선택 (완료됨)"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {completedOptions.map((opt) => (
                  <SelectItem key={opt.id} value={opt.id}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <select
            value={algorithm}
            onChange={(e) => {
              setAlgorithm(e.target.value as Algorithm);
              setShowForm(false);
            }}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            aria-label="최적화 알고리즘"
          >
            <option value="grid_search">그리드 탐색 (최대 9개 조합)</option>
            <option value="bayesian">베이지안 탐색 (≤ 50회 평가)</option>
            <option value="genetic">유전 알고리즘 (≤ 50회 평가)</option>
          </select>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            disabled={backtestId.length === 0}
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-btn-primary transition-all hover:bg-primary-hover disabled:opacity-50"
          >
            {showForm ? "폼 닫기" : ALGORITHM_LABEL[algorithm]}
          </button>
        </div>
        {showForm && backtestId && algorithm === "grid_search" && (
          <GridSearchForm
            backtestId={backtestId}
            onSuccess={() => setShowForm(false)}
          />
        )}
        {showForm && backtestId && algorithm === "bayesian" && (
          <BayesianSearchForm
            backtestId={backtestId}
            onSuccess={() => setShowForm(false)}
          />
        )}
        {showForm && backtestId && algorithm === "genetic" && (
          <GeneticSearchForm
            backtestId={backtestId}
            onSuccess={() => setShowForm(false)}
          />
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">최근 실행</h2>
        <OptimizerRunList limit={20} />
      </section>
    </main>
  );
}
