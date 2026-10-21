"use client";

import Link from "next/link";
import { describeApiError } from "@/lib/api-client";
import { formatDateTime } from "@/features/backtest/utils";
import { usePythonLab } from "../hooks";
import { BacktestForm } from "./backtest-form";
import { RunResult, PYTHON_RUN_LABEL } from "./run-result";
import { StrategyForm } from "./strategy-form";

export function PythonLab() {
  const lab = usePythonLab();
  const available = lab.capabilities.data?.available === true;
  const isActive = lab.run.data?.status === "pending" || lab.run.data?.status === "running";
  return (
    <main className="page space-y-6">
      <section className="card" aria-label="Python 전략 실험실 개요">
        <div className="report">
          <div>
            <h1 className="report-title">Python 전략 실험실</h1>
            <p className="report-meta">코드를 저장하고 같은 버전으로 과거 시세를 검증합니다.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="chip accent">백테스트 전용</span>
              <span className="chip">Bybit USDT 무기한</span>
            </div>
          </div>
          <div className="report-actions">
            <Link className="btn" href="/strategies">
              Pine 전략 목록
            </Link>
            <button type="button" className="btn" onClick={() => lab.selectStrategy(null)}>
              새 Python 전략
            </button>
          </div>
        </div>
      </section>
      {lab.capabilities.isPending ? (
        <p role="status" className="strip-note">
          Python 실행 환경을 확인하고 있습니다.
        </p>
      ) : null}
      {lab.capabilities.isError ? (
        <div role="alert" className="strip-note">
          <p>{describeApiError(lab.capabilities.error, "실행 가능 여부를 확인하지 못했습니다")}</p>
          <button
            className="btn btn-xs mt-2"
            type="button"
            onClick={() => lab.capabilities.refetch()}
          >
            실행 환경 다시 확인
          </button>
        </div>
      ) : null}
      {lab.capabilities.data && !available ? (
        <p role="status" className="strip-note">
          <span>
            <strong>지금은 Python 백테스트를 실행할 수 없습니다.</strong>{" "}
            {lab.capabilities.data.reason ?? "격리 실행 환경이 준비되지 않았습니다."} 코드는 저장할
            수 있습니다.
          </span>
        </p>
      ) : null}
      <section className="card" aria-label="저장된 Python 전략">
        <div className="card-head">
          <h2 className="card-title">저장된 전략</h2>
          <button type="button" className="btn btn-xs" onClick={() => lab.strategies.refetch()}>
            새로고침
          </button>
        </div>
        <div className="card-body">
          {lab.strategies.isPending ? <p role="status">전략을 불러오는 중…</p> : null}
          {lab.strategies.isError ? (
            <p className="field-error" role="alert">
              {describeApiError(lab.strategies.error, "전략을 불러오지 못했습니다")}
            </p>
          ) : null}
          {lab.strategies.data?.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              첫 버전을 저장하면 이곳에서 다시 열 수 있습니다.
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {lab.strategies.data?.items.map((strategy) => (
              <button
                type="button"
                className={`btn${lab.strategy?.id === strategy.id ? " btn-primary" : ""} max-w-full break-all`}
                aria-pressed={lab.strategy?.id === strategy.id}
                key={strategy.id}
                onClick={() => lab.selectStrategy(strategy)}
              >
                {strategy.name}
              </button>
            ))}
          </div>
        </div>
      </section>
      <StrategyForm
        key={lab.strategy?.version_id ?? "new"}
        strategy={lab.strategy}
        isSaving={lab.save.isPending}
        error={lab.save.error}
        onSave={lab.saveDraft}
      >
        {(isDirty) => (
          <BacktestForm
            canRun={available && lab.strategy !== null && !isDirty && !isActive}
            disabledReason={
              !lab.strategy
                ? "먼저 첫 버전을 저장하세요."
                : isDirty
                  ? "코드와 설정을 새 버전으로 저장한 뒤 실행하세요."
                  : isActive
                    ? "진행 중인 실행이 끝나거나 취소된 뒤 실행하세요."
                    : !available
                      ? "Python 실행 환경이 준비되어야 실행할 수 있습니다."
                      : null
            }
            isStarting={lab.start.isPending}
            error={lab.start.error}
            onRun={lab.startRun}
          />
        )}
      </StrategyForm>
      {lab.strategy ? (
        <section className="card" aria-label="Python 실행 이력">
          <div className="card-head">
            <h2 className="card-title">실행 이력</h2>
          </div>
          <div className="card-body">
            {lab.history.isPending ? <p role="status">실행 이력을 불러오는 중…</p> : null}
            {lab.history.isError ? (
              <p role="alert" className="field-error">
                {describeApiError(lab.history.error, "실행 이력을 불러오지 못했습니다")}
              </p>
            ) : null}
            {lab.history.data?.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">아직 실행한 백테스트가 없습니다.</p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              {lab.history.data?.items.map((run) => (
                <button
                  type="button"
                  className="btn max-w-full whitespace-normal"
                  key={run.id}
                  aria-pressed={run.id === lab.run.data?.id}
                  onClick={() => lab.selectRun(run.id)}
                >
                  {formatDateTime(run.created_at)} UTC · {run.request.symbol} ·{" "}
                  {run.request.timeframe} · {PYTHON_RUN_LABEL[run.status]}
                </button>
              ))}
            </div>
          </div>
        </section>
      ) : null}
      {lab.run.isFetching && !lab.run.data ? (
        <p role="status" className="strip-note">
          실행 결과를 불러오는 중…
        </p>
      ) : null}
      {lab.run.isError ? (
        <div role="alert" className="strip-note">
          <p>{describeApiError(lab.run.error, "실행 상태를 불러오지 못했습니다")}</p>
          <button type="button" className="btn btn-xs mt-2" onClick={() => lab.run.refetch()}>
            상태 다시 확인
          </button>
        </div>
      ) : null}
      {lab.run.data ? (
        <RunResult
          run={lab.run.data}
          isCancelling={lab.cancel.isPending}
          cancelError={lab.cancel.error ? describeApiError(lab.cancel.error) : null}
          onCancel={() => {
            if (lab.run.data) lab.cancel.mutate(lab.run.data.id);
          }}
        />
      ) : null}
    </main>
  );
}
