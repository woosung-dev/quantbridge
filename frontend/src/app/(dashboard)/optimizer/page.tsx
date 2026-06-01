// Optimizer 진입 페이지 (실행 list + Grid Search / Bayesian / Genetic 선택).
"use client";

import { useMemo, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBacktests } from "@/features/backtest/hooks";

import { BayesianSearchForm } from "./_components/bayesian-search-form";
import { GeneticSearchForm } from "./_components/genetic-search-form";
import { GridSearchForm } from "./_components/grid-search-form";
import { OptimizerRunList } from "./_components/optimizer-run-list";

type Algorithm = "grid_search" | "bayesian" | "genetic";

const ALGORITHM_LABEL: Record<Algorithm, string> = {
  grid_search: "Grid Search 신규 제출",
  bayesian: "Bayesian 신규 제출",
  genetic: "Genetic 신규 제출",
};

const PICKER_LIMIT = 100;

export default function OptimizerPage() {
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
        <h1 className="text-xl font-semibold">최적화</h1>
        <p className="text-sm text-muted-foreground">
          Grid Search (서버 9 cell) / Bayesian (≤ 50 evaluation) / Genetic
          (≤ 50 evaluation) 으로 strategy 의 pine input 변수 조합을 평가합니다.
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
              <SelectTrigger aria-label="backtest_id">
                <SelectValue
                  placeholder={
                    backtestsQuery.isLoading
                      ? "백테스트 로딩 중..."
                      : completedOptions.length === 0
                        ? "완료된 백테스트 없음"
                        : "백테스트 선택 (COMPLETED)"
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
            className="rounded border border-input bg-background px-3 py-2 text-sm"
            aria-label="optimizer algorithm"
          >
            <option value="grid_search">Grid Search (≤ 9 cell)</option>
            <option value="bayesian">Bayesian (skopt, ≤ 50 eval)</option>
            <option value="genetic">Genetic (self-impl GA, ≤ 50 eval)</option>
          </select>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            disabled={backtestId.length === 0}
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
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
