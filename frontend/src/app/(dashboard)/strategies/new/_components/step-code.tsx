"use client";

// Sprint 7c T4 Step 2 — Monaco Pine editor + 300ms debounce 실시간 파싱.
// Pass 6 Responsive: Monaco 높이 adaptive 300/400/520. Pass 3: empty state Lightbulb helper.

import { useEffect, useRef } from "react";
import { LightbulbIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PineEditor } from "@/components/monaco/pine-editor";
import { useParseStrategy } from "@/features/strategy/hooks";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { useDebouncedValue } from "@/features/strategy/utils";
import { ParsePreviewPanel } from "./parse-preview-panel";

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

      {/* Pass 6 Responsive: Monaco wrapper adaptive height */}
      <div className="h-[300px] md:h-[400px] lg:h-[520px]">
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

      <div className="mt-5">
        <ParsePreviewPanel result={parse.data ?? null} loading={parse.isPending} />
      </div>

      <div className="mt-8 flex items-center justify-between">
        <Button variant="ghost" onClick={props.onBack}>← 이전</Button>
        <Button onClick={props.onNext} disabled={!canProceed}>
          다음 단계 →
        </Button>
      </div>
    </div>
  );
}
