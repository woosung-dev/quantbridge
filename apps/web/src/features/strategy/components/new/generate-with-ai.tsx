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
import { toast } from "sonner";

import { StateBox } from "@/components/state-box";
import { useGenerateStrategy } from "@/features/strategy/hooks";
import { hasDrift } from "@/features/strategy/schemas";
import { CHIP_TONE_CLASS } from "@/lib/labels";

// 서버 계약(`GenerateStrategyRequest`)과 **같은 수**여야 한다. 어긋나면 화면이 통과시킨 입력이 422 가 된다.
const PROMPT_MIN = 10;
const PROMPT_MAX = 2000;

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
  const tooShort = prompt.trim().length > 0 && prompt.trim().length < PROMPT_MIN;
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
        // ★서버 계약이 `Field(min_length=10, max_length=2000)` 이다. 상한을 화면이 막지 않으면
        //   사용자는 422 를 받고 「잠시 후 다시 시도」라는, 절대 통하지 않는 조언을 듣는다.
        maxLength={PROMPT_MAX}
        aria-describedby="generate-prompt-hint"
        placeholder="예: RSI 가 30 아래로 내려갔다 올라오면 롱, 70 위에서 청산"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <p className="field-hint" id="generate-prompt-hint">
        {tooShort
          ? `조금 더 자세히 적어주세요. ${PROMPT_MIN}자 이상 필요합니다. (현재 ${prompt.trim().length}자)`
          : `${prompt.length} / ${PROMPT_MAX}자`}
      </p>
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

      <p className="sr-only" role="status">
        {generate.isPending
          ? "전략을 만들고 있습니다."
          : result
            ? `전략을 만들었습니다. ${result.is_runnable ? "실행 가능합니다." : "실행 불가입니다."}`
            : ""}
      </p>

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
              body="아래 Pine 이 실제로 도는 코드입니다. 대조기는 식별자 집합만 비교하므로 확정하지 못합니다."
            >
              {/* ★어긋난 식별자를 보여주지 않으면 「다를 수 있다」가 확인 불가능한 주장이 된다. */}
              <p className="dim mono">
                {[
                  result.drift.only_in_llm.length > 0
                    ? `파이썬에만: ${result.drift.only_in_llm.slice(0, 8).join(", ")}`
                    : null,
                  result.drift.only_in_rendered.length > 0
                    ? `Pine 에만: ${result.drift.only_in_rendered.slice(0, 8).join(", ")}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" / ")}
              </p>
            </StateBox>
          ) : null}

          {/* ★AI 층 격리 — 위의 판정 칩·미지원 목록은 코드 분석기 산출이고 여기는 LLM 산문이다.
              같은 서체·같은 좌측 바로 나란히 두면 사용자가 어느 줄이 검증된 사실인지 못 가른다. */}
          {result.notes.length > 0 ? (
            <div className="narrative" data-testid="generate-notes">
              <div className="brief-verdict">
                <span className="chip ai">AI 가 덧붙인 말 · 판정이 아닙니다</span>
              </div>
              <ul className="brief-list">
                {result.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
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
            onClick={() => {
              onUsePine(result.pine_source);
              // ★편집기는 이 패널보다 위 카드라 화면 밖일 수 있다. 피드백이 없으면 사용자는
              //   반영됐는지 몰라 같은 버튼을 반복해 누르고, 그 사이 직접 붙여넣은 Pine 은
              //   이미 덮어써져 있다. 위저드의 다른 두 주입 경로도 toast 를 띄운다.
              toast.success("생성한 Pine 을 편집기에 넣었습니다. 기존 소스는 덮어썼습니다.");
            }}
          >
            이 Pine 코드 쓰기
          </button>
        </div>
      ) : null}
    </div>
  );
}
