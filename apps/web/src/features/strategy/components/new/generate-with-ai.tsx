"use client";

// [ADR-041] 자연어 → 전략 생성.
//
// ★★**Pine 이 정본이고 Python 은 사람이 읽는 뷰다.** 둘이 어긋나는 것을 **막을 수단이 없고**,
//   이 화면은 그 위험을 제거하는 대신 **가시화**한다([ADR-041] §트레이드오프).
//   그래서 문구가 「다릅니다」가 아니라 「**다를 수 있습니다**」다 — 탐지기는 식별자 집합 비교라
//   「의미가 같은데 표현이 다름」과 「표현이 같은데 의미가 다름」을 완전히 못 가른다.
// ★판정(실행 가능/미지원)은 LLM 이 아니라 서버의 `analyze_coverage` 가 낸다.
// ★생성은 **저장하지 않는다** — 사용자가 검토하고 「이 코드 쓰기」를 눌러야 소스에 들어간다.

import { useState } from "react";

import { StateBox } from "@/components/state-box";
import { useGenerateStrategy } from "@/features/strategy/hooks";
import { hasDrift } from "@/features/strategy/schemas";
import { CHIP_TONE_CLASS } from "@/lib/labels";

export function GenerateWithAI({
  symbol,
  timeframe,
  onUsePine,
}: {
  symbol: string;
  timeframe: string;
  /** 검토를 마친 Pine 을 편집기로 넣는다. ★정본은 언제나 Pine 이다. */
  onUsePine: (pine: string) => void;
}) {
  const [prompt, setPrompt] = useState("");
  const generate = useGenerateStrategy();
  const result = generate.data ?? null;

  return (
    <div className="brief-section" data-testid="generate-with-ai">
      <label className="field-label" htmlFor="generate-prompt">
        어떤 전략을 원하시나요?
      </label>
      <textarea
        id="generate-prompt"
        className="input"
        rows={3}
        placeholder="예: RSI 가 30 아래로 내려갔다 올라오면 롱, 70 위에서 청산"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <button
        type="button"
        className="btn btn-ghost btn-xs"
        disabled={prompt.trim().length < 10 || generate.isPending}
        onClick={() => generate.mutate({ prompt: prompt.trim(), symbol, timeframe })}
      >
        {generate.isPending ? "만드는 중..." : "AI 로 만들기"}
      </button>
      <p className="strip-note">
        만든 결과는 <strong>바로 저장되지 않습니다.</strong> 검토한 뒤 직접 넣으세요. 실행 가능
        여부는 AI 가 아니라 코드 분석기가 판정합니다.
      </p>

      {generate.isError ? (
        <StateBox
          testId="generate-error"
          tone="failed"
          title="전략을 만들지 못했습니다."
          body="잠시 후 다시 시도해 주세요."
        />
      ) : null}

      {result ? (
        <div className="brief-section" data-testid="generate-result">
          <div className="brief-verdict">
            <span
              className={result.is_runnable ? CHIP_TONE_CLASS.done : CHIP_TONE_CLASS.warn}
              data-testid="generate-verdict"
            >
              {result.is_runnable ? "실행 가능" : "실행 불가"}
            </span>
          </div>

          {result.is_runnable ? null : (
            <div data-testid="generate-blocked">
              <p className="metric-group-title">지원하지 않는 함수가 있습니다</p>
              <ul className="brief-list">
                {result.unsupported.map((name) => (
                  <li className="mono" key={name}>
                    {name}
                  </li>
                ))}
              </ul>
              <p className="strip-note">
                미지원 함수가 하나라도 있으면 <strong>부분 실행하지 않습니다</strong>. 요청을 바꿔
                다시 만들어 보세요.
              </p>
            </div>
          )}

          {hasDrift(result.drift) && result.drift ? (
            <StateBox
              testId="generate-drift"
              tone="failed"
              title="AI 가 쓴 파이썬과 실제 실행되는 코드가 다를 수 있습니다."
              body="아래 Pine 이 실제로 도는 코드입니다. 파이썬 설명과 어긋나 보이면 Pine 을 기준으로 읽으세요."
            />
          ) : null}

          {result.notes.length > 0 ? (
            <ul className="brief-list" data-testid="generate-notes">
              {result.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : null}

          <div className="table-wrap">
            <pre className="python-view">
              <code>{result.pine_source}</code>
            </pre>
          </div>

          <button
            type="button"
            className="btn btn-primary btn-xs"
            disabled={!result.is_runnable}
            onClick={() => onUsePine(result.pine_source)}
          >
            이 Pine 코드 쓰기
          </button>
        </div>
      ) : null}
    </div>
  );
}
