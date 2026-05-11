// Sprint 54 — Optimizer 진입 페이지 (실행 list + 새 Grid Search 폼).
"use client";

import { useState } from "react";

import { GridSearchForm } from "./_components/grid-search-form";
import { OptimizerRunList } from "./_components/optimizer-run-list";

export default function OptimizerPage() {
  const [backtestId, setBacktestId] = useState("");
  const [showForm, setShowForm] = useState(false);

  return (
    <main className="container mx-auto space-y-6 px-4 py-6">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold">Optimizer (Sprint 54 MVP)</h1>
        <p className="text-sm text-muted-foreground">
          Grid Search 로 strategy 의 pine input 변수 조합을 평가 (서버 9 cell 제한).
          Bayesian / Genetic 알고리즘은 Sprint 55+ 이연 (ADR-013).
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
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            disabled={backtestId.length === 0}
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {showForm ? "폼 닫기" : "Grid Search 신규 제출"}
          </button>
        </div>
        {showForm && backtestId && (
          <GridSearchForm
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
