"use client";

// Sprint 7c T4 Step 2 — Monaco Pine editor + 300ms debounce 실시간 파싱.
// Pass 6 Responsive: Monaco 높이 adaptive 300/400/520. Pass 3: empty state Lightbulb helper.
// Sprint 42-polish W3: prototype 07 매칭 — 2열 grid (md+) Monaco 좌 + ParseResultPanel 우.

import { useEffect, useRef } from "react";
import { LightbulbIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PineEditor } from "@/components/monaco/pine-editor";
import { useParseStrategy } from "@/features/strategy/hooks";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { useDebouncedValue } from "@/features/strategy/utils";
import { ParseResultPanel } from "./parse-result-panel";

export function StepCode(props: {
  pineSource: string;
  onPineSourceChange: (v: string) => void;
  onParsed: (r: ParsePreviewResponse | null) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const debounced = useDebouncedValue(props.pineSource, 300);
  const parse = useParseStrategy();
  const { mutate: parseMutate } = parse;

  // 부모가 매 렌더 새 onParsed를 내려주는 경우 effect deps 폭주 방지.
  // ADR-010 anti-pattern #5 (useEffect deps 안정화) 적용.
  const onParsedRef = useRef(props.onParsed);
  useEffect(() => {
    onParsedRef.current = props.onParsed;
  });

  // 자동 파싱: debounced 값이 비어있지 않을 때만.
  useEffect(() => {
    if (debounced.trim().length === 0) {
      onParsedRef.current(null);
      return;
    }
    parseMutate(debounced, {
      onSuccess: (data) => onParsedRef.current(data),
      onError: () => onParsedRef.current(null),
    });
  }, [debounced, parseMutate]);

  const canProceed =
    parse.data?.status === "ok" || parse.data?.status === "unsupported";

  return (
    <div>
      <h2 className="mb-2 font-display text-lg font-semibold">Pine Script 코드</h2>
      <p className="mb-4 text-xs text-[color:var(--text-muted)]">
        <kbd className="rounded border border-[color:var(--border)] bg-[color:var(--bg-alt)] px-1.5 py-0.5 font-mono text-[0.7rem]">
          ⌘+Enter
        </kbd>{" "}
        즉시 파싱
      </p>

      {/* Pass 3: 빈 코드 상태 Lightbulb helper */}
      {props.pineSource.length === 0 && (
        <p className="mb-2 flex items-center gap-1.5 text-xs text-[color:var(--text-muted)]">
          <LightbulbIcon className="size-3.5" />
          TradingView Pine Editor의 코드를 그대로 붙여넣으세요. 대부분 자동 변환됩니다.
        </p>
      )}

      {/* Sprint 42-polish W3: 2열 grid (md+) — 좌 Monaco / 우 파싱 결과 패널, mobile 에서 stack */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[2fr_1fr]">
        {/*
          Pass 6 Responsive: Monaco wrapper adaptive height.
          W3-fidelity: prototype 07 `.code-editor` 의 inset 1px ring(#334155) +
          rounded-md + overflow-hidden + dark editor-bg(#1E293B) 매칭.
        */}
        <div
          className="h-[300px] overflow-hidden rounded-[var(--radius-md,0.625rem)] bg-[#1E293B] shadow-[inset_0_0_0_1px_#334155] md:h-[400px] lg:h-[520px]"
        >
          <PineEditor
            value={props.pineSource}
            onChange={props.onPineSourceChange}
            onTriggerParse={() => {
              if (debounced.trim()) {
                parseMutate(debounced, {
                  onSuccess: (data) => onParsedRef.current(data),
                  onError: () => onParsedRef.current(null),
                });
              }
            }}
            height="100%"
          />
        </div>

        <ParseResultPanel result={parse.data ?? null} loading={parse.isPending} />
      </div>

      <div className="mt-8 flex items-center justify-between gap-3">
        <Button variant="ghost" onClick={props.onBack}>← 이전</Button>
        <div className="flex items-center gap-3">
          {!canProceed && props.pineSource.length > 0 && !parse.isPending && (
            <p className="text-[0.7rem] text-[color:var(--text-muted)] motion-safe:animate-[parseResultIn_200ms_ease-out_both]">
              파싱 완료 후 다음 단계로 진행할 수 있어요
            </p>
          )}
          <Button onClick={props.onNext} disabled={!canProceed}>
            다음 단계 →
          </Button>
        </div>
      </div>
    </div>
  );
}
