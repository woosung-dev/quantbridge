"use client";

// Sprint 7c T5 / 7b ISSUE-003 / FE-03:
// 코드 탭 — Monaco Pine 에디터. Sprint FE-03 에서 편집 버퍼를 Zustand edit-store 로 lift-up.
// onChange → useEditStore.setPineSource 직접 연결 (debounce 없음, 상태는 즉시 동기화).
// TabParse 와 한 source of truth 를 공유 → 편집 즉시 파싱 재계산 (TabParse 쪽에서 debounce).
// 수동 ⌘+Enter 재파싱은 store 의 최신 pineSource 를 mutation 으로 다시 요청.

import { useParseStrategy, usePreviewParse } from "@/features/strategy/hooks";
import {
  selectPineSource,
  useEditStore,
} from "@/features/strategy/edit-store";
import { PineEditor } from "@/components/monaco/pine-editor";
import type { StrategyResponse } from "@/features/strategy/schemas";

import { ParsePreviewPanel } from "../../../new/_components/parse-preview-panel";

export function TabCode({ strategy: _strategy }: { strategy: StrategyResponse }) {
  const pineSource = useEditStore(selectPineSource);
  const setPineSource = useEditStore((s) => s.setPineSource);

  const autoParse = usePreviewParse(pineSource);
  const manualParse = useParseStrategy();

  const result = manualParse.data ?? autoParse.data ?? null;
  const loading = manualParse.isPending || autoParse.isFetching;

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs text-[color:var(--text-muted)]">
            ⌘+Enter 수동 재파싱 · 저장은 상단 헤더의 저장 버튼
          </p>
        </div>
        <PineEditor
          value={pineSource}
          onChange={setPineSource}
          onTriggerParse={() =>
            pineSource.trim() && manualParse.mutate(pineSource)
          }
          height={520}
        />
      </div>
      <ParsePreviewPanel result={result} loading={loading} />
    </div>
  );
}
