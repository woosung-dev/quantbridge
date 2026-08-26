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
import { NARRATIVE_STYLE_LABEL, type NarrativeNote } from "@/features/strategy/schemas";
import { CHIP_TONE_CLASS } from "@/lib/labels";

export function NarrativePanel({ strategyId }: { strategyId: string }) {
  const [asked, setAsked] = useState(false);
  const query = useStrategyNarrative(strategyId, asked);

  if (!asked) {
    return (
      <div className="brief-section" data-testid="narrative-idle">
        <button type="button" className="btn btn-ghost btn-xs" onClick={() => setAsked(true)}>
          AI 해설 보기
        </button>
        <p className="strip-note">
          전략을 자연어로 설명합니다. <strong>판정이 아니라 보조 설명</strong>이며, 위의 판정·미지원
          목록은 AI 와 무관하게 코드 분석으로 나온 값입니다.
        </p>
      </div>
    );
  }

  if (query.isPending) {
    return (
      <div className="brief-section" aria-busy="true" data-testid="narrative-loading">
        <div className="sk sk-line" style={{ width: "70%" }} aria-hidden="true" />
        <div className="sk sk-line" style={{ width: "48%" }} aria-hidden="true" />
        <p className="state-note">해설을 만들고 있습니다.</p>
      </div>
    );
  }

  if (query.isError || !query.data) {
    // ★실패해도 화면은 이미 완결돼 있다 — 이 박스가 브리핑을 대체하지 않는다.
    return (
      <div className="brief-section">
        <StateBox
          testId="narrative-error"
          tone="failed"
          title="AI 해설을 만들지 못했습니다."
          body="위의 판정과 구조 정보는 그대로 유효합니다. 해설만 실패한 것입니다."
        />
      </div>
    );
  }

  const { summary, style, assumptions, risks, dropped_ungrounded } = query.data;

  return (
    <div className="brief-section narrative" data-testid="narrative">
      <div className="brief-verdict">
        <span className={CHIP_TONE_CLASS.accent} data-testid="narrative-label">
          AI 해설 · 판정이 아닙니다
        </span>
        <span className={CHIP_TONE_CLASS.neutral}>{NARRATIVE_STYLE_LABEL[style] ?? style}</span>
      </div>

      {summary ? <p data-testid="narrative-summary">{summary}</p> : null}

      <NoteList title="이 전략이 가정하는 것" notes={assumptions} testId="narrative-assumptions" />
      <NoteList title="언제 깨지나" notes={risks} testId="narrative-risks" />

      {dropped_ungrounded > 0 ? (
        <p className="strip-note" data-testid="narrative-dropped">
          {`근거를 대지 못한 문장 ${dropped_ungrounded}개는 표시하지 않았습니다.`}
        </p>
      ) : null}
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
