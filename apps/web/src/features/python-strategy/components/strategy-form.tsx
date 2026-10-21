"use client";

import { Controller, useForm } from "react-hook-form";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";
import { describeApiError } from "@/lib/api-client";
import { strategyDraft } from "../defaults";
import {
  PythonStrategyDraftSchema,
  type PythonStrategy,
  type PythonStrategyDraft,
} from "../schemas";
import { PythonEditor } from "./python-editor";

export function StrategyForm({
  strategy,
  isSaving,
  error,
  onSave,
  children,
}: {
  strategy: PythonStrategy | null;
  isSaving: boolean;
  error: Error | null;
  onSave: (draft: PythonStrategyDraft) => void;
  children: (isDirty: boolean) => React.ReactNode;
}) {
  const form = useForm<PythonStrategyDraft>({
    resolver: zodV4Resolver(PythonStrategyDraftSchema),
    defaultValues: strategyDraft(strategy),
  });
  const errors = form.formState.errors;
  return (
    <>
      <section className="card" aria-label="Python 전략 편집">
        <div className="card-head">
          <div>
            <h2 className="card-title">전략 코드</h2>
            <p className="card-sub">
              저장할 때마다 새 버전을 만듭니다. 실행 기록은 당시 버전을 유지합니다.
            </p>
          </div>
          {strategy ? (
            <span className="chip mono" title={strategy.version_id}>
              버전 {strategy.version_id.slice(0, 8)}
            </span>
          ) : (
            <span className="chip">저장 전</span>
          )}
        </div>
        <form onSubmit={form.handleSubmit(onSave)} className="card-body space-y-4">
          <div className="field">
            <label className="field-label" htmlFor="python-name">
              전략 이름
            </label>
            <input
              className="input"
              id="python-name"
              {...form.register("name")}
              aria-invalid={Boolean(errors.name)}
            />
            {errors.name ? (
              <p className="field-error" role="alert">
                {errors.name.message}
              </p>
            ) : null}
          </div>
          <div className="field">
            <p className="field-label" id="python-code-label">
              Python 코드
            </p>
            <section
              className="min-w-0 overflow-hidden rounded-md border"
              aria-labelledby="python-code-label"
            >
              <Controller
                control={form.control}
                name="source"
                render={({ field }) => (
                  <PythonEditor value={field.value} onChange={field.onChange} />
                )}
              />
            </section>
            {errors.source ? (
              <p className="field-error" role="alert">
                {errors.source.message}
              </p>
            ) : null}
          </div>
          <details className="text-sm text-muted-foreground">
            <summary className="cursor-pointer">전략 작성 규칙</summary>
            <p className="mt-2 leading-relaxed">
              <code>on_bar(ctx, state)</code>에서 <code>action</code>을 반환합니다:{" "}
              <code>hold</code>, <code>long</code>, <code>short</code>, <code>close</code>.{" "}
              <code>ctx["history"]</code>에는 현재까지 확정된 봉만 들어옵니다. 가격·거래량은
              문자열입니다. <code>stop_loss</code>와 <code>take_profit</code>은 절대 가격 문자열로
              지정합니다. 선택 함수 <code>init(params)</code>는 상태 객체를 반환합니다.
            </p>
            <p className="mt-2 leading-relaxed">
              예제는 실행 방법을 보여주는 단순 이동평균 전략입니다. 연구에서 선별된 전략이 아닙니다.
              네트워크·파일 접근과 실행 중 패키지 설치는 지원하지 않습니다.
            </p>
          </details>
          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            <div className="field">
              <label className="field-label" htmlFor="python-params">
                파라미터 JSON
              </label>
              <textarea
                className="textarea min-h-24 font-mono"
                id="python-params"
                {...form.register("params_json")}
                aria-invalid={Boolean(errors.params_json)}
              />
              {errors.params_json ? (
                <p className="field-error" role="alert">
                  {errors.params_json.message}
                </p>
              ) : null}
            </div>
            <div className="field">
              <label className="field-label" htmlFor="python-warmup">
                워밍업 봉 수
              </label>
              <input
                className="input"
                id="python-warmup"
                type="number"
                min={0}
                max={10_000}
                {...form.register("warmup_bars")}
                aria-invalid={Boolean(errors.warmup_bars)}
              />
              <p className="text-sm text-muted-foreground">
                지표 준비에 사용하며 성과 측정 기간에서 제외합니다.
              </p>
              {errors.warmup_bars ? (
                <p className="field-error" role="alert">
                  {errors.warmup_bars.message}
                </p>
              ) : null}
            </div>
          </div>
          {error ? (
            <p role="alert" className="field-error">
              {describeApiError(error, "전략 저장에 실패했습니다")}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn btn-primary" disabled={isSaving}>
              {isSaving ? "버전 저장 중…" : strategy ? "새 버전 저장" : "첫 버전 저장"}
            </button>
            {strategy ? (
              <p role="status" className="text-sm text-muted-foreground">
                저장된 코드 {strategy.source_hash.slice(0, 12)}
              </p>
            ) : null}
          </div>
        </form>
      </section>
      {children(form.formState.isDirty)}
    </>
  );
}
