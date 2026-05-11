// Sprint 55 — Optimizer 진입 페이지 (실행 list + Grid Search / Bayesian 알고리즘 선택).
"use client";

import { useState } from "react";

import { BayesianSearchForm } from "./_components/bayesian-search-form";
import { GridSearchForm } from "./_components/grid-search-form";
import { OptimizerRunList } from "./_components/optimizer-run-list";

type Algorithm = "grid_search" | "bayesian";

export default function OptimizerPage() {
  const [backtestId, setBacktestId] = useState("");
  const [algorithm, setAlgorithm] = useState<Algorithm>("grid_search");
  const [showForm, setShowForm] = useState(false);

  return (
    <main className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold">Optimizer (Sprint 55)</h1>
        <p className="text-sm text-muted-foreground">
          Grid Search (서버 9 cell) 또는 Bayesian (≤ 50 evaluation, ADR-013 §6) 으로
          strategy 의 pine input 변수 조합을 평가. Genetic 은 Sprint 56+ 이연 (BL-233).
        </p>
      </header>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <input
            placeholder="backtest_id (COMPLETED)"
            className="rounded border border-input bg-background px-3 py-2 text-sm font-mono"
            value={backtestId}
            onChange={(e) => setBacktestId(e.target.value.trim())}
            aria-label="backtest_id"
          />
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
          </select>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            disabled={backtestId.length === 0}
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {showForm
              ? "폼 닫기"
              : algorithm === "grid_search"
                ? "Grid Search 신규 제출"
                : "Bayesian 신규 제출"}
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
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-semibold">최근 실행</h2>
        <OptimizerRunList limit={20} />
      </section>
    </main>
  );
}
