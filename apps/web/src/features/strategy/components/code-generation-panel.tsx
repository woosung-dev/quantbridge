"use client";

import { useState } from "react";

import { TableScrollRegion } from "@/components/table-scroll-region";
import type { GenerateCodeStrategyResponse } from "@/features/strategy/code-schemas";
import { describeApiError } from "@/lib/api-client";

export function CodeGenerationPanel({
  preview,
  hasAppliedPreview,
  isPending,
  error,
  disabled,
  onGenerate,
  onApply,
}: {
  preview: GenerateCodeStrategyResponse | null;
  hasAppliedPreview: boolean;
  isPending: boolean;
  error: Error | null;
  disabled: boolean;
  onGenerate: (prompt: string) => void;
  onApply: () => void;
}) {
  const [prompt, setPrompt] = useState("");
  const length = prompt.trim().length;
  return (
    <section className="section" aria-labelledby="code-generation-title">
      <header className="section-head">
        <h2 id="code-generation-title">자연어로 Python 초안 만들기</h2>
      </header>
      <div className="card p-5 grid gap-4">
        <label className="field-label" htmlFor="code-generation-prompt">
          진입·청산 조건
        </label>
        <textarea
          id="code-generation-prompt"
          className="textarea"
          rows={3}
          maxLength={2000}
          value={prompt}
          disabled={disabled || isPending}
          aria-describedby="code-generation-hint"
          placeholder="예: 빠른 이동평균이 느린 이동평균을 상향 돌파하면 롱, 하향 돌파하면 숏"
          onChange={(event) => setPrompt(event.target.value)}
        />
        <p className="field-hint" id="code-generation-hint">
          {length > 0 && length < 10 ? "조건을 10자 이상 적으세요. " : ""}
          {prompt.length} / 2000자. 아래 준비 봉 수와 파라미터를 사용합니다.
        </p>
        <div className="report-actions">
          <button
            type="button"
            className="btn"
            disabled={disabled || isPending || length < 10}
            onClick={() => onGenerate(prompt.trim())}
          >
            {isPending ? "Python 초안 만드는 중…" : "Python 초안 생성"}
          </button>
        </div>
        <p className="strip-note">
          초안은 자동으로 적용·저장되지 않습니다. 원문을 검토하고 적용한 뒤, 직접 저장하고
          백테스트하세요. 데모 자동매매는 별도 시작이 필요합니다.
        </p>
        <p role="status" className="field-hint">
          {isPending
            ? "Python 초안을 만들고 있습니다."
            : preview
              ? "Python 초안이 준비되었습니다. 실행·의미 일치는 아직 검증하지 않았습니다."
              : hasAppliedPreview
                ? "Python 초안을 편집기에 적용했습니다. 원문을 검토한 뒤 저장하세요."
                : ""}
        </p>
        {error ? <p role="alert">{describeApiError(error)}</p> : null}
        {preview ? (
          <div className="grid gap-4" data-testid="code-generation-preview">
            <p className="field-hint">
              Gemini 요청 모델: <span className="mono">{preview.requested_model}</span>
              <br />
              응답 모델:{" "}
              <span className="mono">{preview.actual_model ?? "미보고 · 확인 안 됨"}</span>
              <br />
              {preview.usage
                ? `토큰 사용량: 입력 ${preview.usage.input_tokens ?? "미보고"} · 출력 ${preview.usage.output_tokens ?? "미보고"} · 사고 ${preview.usage.thinking_tokens ?? "미보고"} · 전체 ${preview.usage.total_tokens ?? "미보고"}`
                : "토큰 사용량: 미보고"}
            </p>
            <TableScrollRegion label="생성된 Python 초안">
              <pre className="python-view">
                <code>{preview.code.source_code}</code>
              </pre>
            </TableScrollRegion>
            <p className="field-hint">준비 봉 수: {preview.code.warmup_bars}</p>
            <TableScrollRegion label="생성된 Python 파라미터">
              <pre className="python-view">
                <code>{JSON.stringify(preview.code.params, null, 2)}</code>
              </pre>
            </TableScrollRegion>
            {preview.assumptions.length > 0 ? (
              <div className="narrative">
                <p className="field-label">AI가 해석한 조건 · 검증 결과가 아닙니다</p>
                <ul className="brief-list">
                  {Array.from(new Set(preview.assumptions)).map((assumption) => (
                    <li key={assumption}>{assumption}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="report-actions">
              <button
                type="button"
                className="btn btn-primary"
                disabled={disabled || isPending}
                onClick={onApply}
              >
                이 Python 초안 적용
              </button>
            </div>
            <p className="field-hint">
              적용하면 아래 편집기의 원문·언어·준비 봉·파라미터를 바꿉니다.
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
