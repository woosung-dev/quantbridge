"use client";

// [ADR-040] 해설 층 — **판정이 아니다.**
//
// ★★이 컴포넌트가 지켜야 할 것은 하나다: **판정처럼 보이지 않게 하는 것.**
//   실행 가능/미지원/degraded/Track 은 위쪽 결정론 층이 이미 냈고, 여기 있는 것은 산문이다.
//   [ADR-020] §3 F 가 「Trust Layer 에 LLM 노이즈가 섞이면 신뢰도 역행」이라고 기각한 바로 그
//   위험이라, 배경·라벨을 분리하고 「AI 해설 — 판정이 아닙니다」를 **본문 위에** 붙인다.
// ★근거 줄이 없는 문장은 그리지 않는다(서버가 이미 버렸고 여기서 한 겹 더).
// ★사용자가 **열 때만** 부른다 — LLM 왕복은 느리고 돈이 든다.

import { useState } from "react";

import { StateBox } from "@/components/state-box";
import { useStrategyNarrative } from "@/features/strategy/hooks";
import {
  LLM_PROVIDER_LABEL,
  NARRATIVE_STYLE_LABEL,
  type NarrativeNote,
} from "@/features/strategy/schemas";
import { CHIP_TONE_CLASS } from "@/lib/labels";
import { describeApiError } from "@/lib/api-client";
import { errorIdOf } from "@/features/strategy/error-id";

export function NarrativePanel({ strategyId }: { strategyId: string }) {
  const [asked, setAsked] = useState(false);
  const query = useStrategyNarrative(strategyId, asked);
  const data = query.data ?? null;

  // ★버튼을 **모든 상태에서 계속 마운트**한다. 조기 반환으로 블록을 갈아치우면 누른 순간
  //   버튼이 사라져 포커스가 <body> 로 유실된다(키보드 사용자가 문서 처음으로 튕긴다).
  //   접었다 펴도 React Query 캐시가 있어 LLM 을 다시 부르지 않는다.
  return (
    <div className="brief-section" data-testid={asked ? "narrative" : "narrative-idle"}>
      <button
        type="button"
        className="btn btn-ghost btn-xs"
        aria-expanded={asked}
        aria-controls="narrative-body"
        onClick={() => setAsked((v) => !v)}
      >
        {asked ? "AI 해설 접기" : "AI 해설 보기"}
      </button>

      {/* ★도착·실패를 스크린리더에 알린다. `aria-busy` 는 라이브 리전이 아니라 억제 속성이다. */}
      <p className="sr-only" role="status">
        {asked && query.isPending
          ? "AI 해설을 만들고 있습니다."
          : asked && query.isError
            ? "AI 해설을 만들지 못했습니다. 위의 판정과 구조 정보는 그대로 유효합니다."
            : asked && data
              ? "AI 해설이 준비됐습니다. 판정이 아니라 보조 설명입니다."
              : ""}
      </p>

      <div id="narrative-body" hidden={!asked}>
        {query.isPending ? (
          <div aria-busy="true" data-testid="narrative-loading">
            <div className="sk sk-line" style={{ width: "70%" }} aria-hidden="true" />
            <div className="sk sk-line" style={{ width: "48%" }} aria-hidden="true" />
            <p className="state-note">해설을 만들고 있습니다.</p>
          </div>
        ) : query.isError || !data ? (
          // ★실패해도 화면은 이미 완결돼 있다. 이 박스가 브리핑을 대체하지 않는다.
          //   ★재시도가 없으면 유일한 탈출구가 새로고침인데, 백테스트 폼 안에서는 그것이
          //     사용자가 채운 폼 값을 전부 날린다.
          <StateBox
            testId="narrative-error"
            tone="failed"
            title="AI 해설을 만들지 못했습니다."
            body={describeApiError(query.error, "위의 판정과 구조 정보는 그대로 유효합니다.")}
            code={errorIdOf(query.error)}
          >
            <button type="button" className="btn btn-ghost btn-xs" onClick={() => query.refetch()}>
              다시 시도
            </button>
          </StateBox>
        ) : (
          <div className="narrative">
            <div className="brief-verdict">
              {/* ★`chip accent`(코퍼)를 쓰지 않는다 — 이 레포에서 그것은 「바 단위 이벤트 루프」
                  같은 **결정론 사실 배지**로 이미 8곳이 쓰고 있어 「시스템이 보증함」으로 읽힌다.
                  AI 층은 보증이 아니므로 전용 토큰을 쓴다. */}
              <span className="chip ai" data-testid="narrative-label">
                AI 해설 · 판정이 아닙니다
              </span>
              <span className={CHIP_TONE_CLASS.neutral}>
                {NARRATIVE_STYLE_LABEL[data.style] ?? data.style}
              </span>
              {/* ★색과 테두리만으로 AI 층을 구분하면 색을 못 보는 사용자에게 전달되지 않는다
                  (ui-ux-pro-max §1 color-not-only). 누가 썼는지 글자로도 밝힌다. */}
              <span className="dim mono" data-testid="narrative-provider">
                {LLM_PROVIDER_LABEL[data.provider] ?? data.provider}
              </span>
            </div>

            {data.summary ? <p data-testid="narrative-summary">{data.summary}</p> : null}

            <NoteList
              title="이 전략이 가정하는 것"
              notes={data.assumptions}
              testId="narrative-assumptions"
            />
            <NoteList title="언제 깨지나" notes={data.risks} testId="narrative-risks" />

            {data.dropped_ungrounded > 0 ? (
              <p className="strip-note" data-testid="narrative-dropped">
                {`근거를 대지 못한 문장 ${data.dropped_ungrounded}개는 표시하지 않았습니다.`}
              </p>
            ) : null}
          </div>
        )}
      </div>

      <p className="strip-note">
        전략을 자연어로 설명합니다. <strong>판정이 아니라 보조 설명</strong>이며, 위의 판정·미지원
        목록은 AI 와 무관하게 코드 분석으로 나온 값입니다.
      </p>
    </div>
  );
}

function NoteList({
  title,
  notes,
  testId,
}: {
  title: string;
  notes: readonly NarrativeNote[];
  testId: string;
}) {
  // ★근거 줄이 없는 문장은 그리지 않는다. 남는 것이 없으면 절 자체를 그리지 않는다.
  const grounded = notes.filter((n) => n.pine_lines.length > 0 && n.text.trim().length > 0);
  if (grounded.length === 0) {
    return null;
  }
  return (
    <div>
      <p className="metric-group-title">{title}</p>
      <ul className="brief-list" data-testid={testId}>
        {grounded.map((n) => (
          <li key={n.text}>
            {n.text} <span className="dim mono">{n.pine_lines.map((l) => `L${l}`).join(" ")}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
