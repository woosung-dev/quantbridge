"use client";

// Sprint 7c T5 + Sprint 7b ISSUE-003: 코드 탭 — Monaco Pine 에디터 + 실시간 파싱 + 저장.
// 마운트 자동 파싱은 useQuery(usePreviewParse) — StrictMode-safe idempotent.
// ⌘+Enter 수동 재파싱은 useParseStrategy mutation. 두 결과를 우측 패널에 병합 표시.

import { useState } from "react";
import { SaveIcon } from "lucide-react";
import { toast } from "sonner";

import { PineEditor } from "@/components/monaco/pine-editor";
import { Button } from "@/components/ui/button";
import {
  useParseStrategy,
  usePreviewParse,
  useUpdateStrategy,
} from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";

import { ParsePreviewPanel } from "../../../new/_components/parse-preview-panel";

export function TabCode({ strategy }: { strategy: StrategyResponse }) {
  const [source, setSource] = useState(strategy.pine_source);
  const dirty = source !== strategy.pine_source;
  // 마운트 자동 파싱(저장된 pine_source 기준) — useQuery 기반.
  const autoParse = usePreviewParse(strategy.pine_source);
  // 사용자 수정 후 ⌘+Enter 재파싱 — mutation 기반.
  const manualParse = useParseStrategy();
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  // manual이 있으면 우선, 없으면 auto 결과 노출.
  const result = manualParse.data ?? autoParse.data ?? null;
  const loading = manualParse.isPending || autoParse.isFetching;

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs text-[color:var(--text-muted)]">
            ⌘+S 저장 · ⌘+Enter 파싱 미리보기
          </p>
          <Button
            onClick={() => update.mutate({ pine_source: source })}
            disabled={!dirty || update.isPending}
          >
            <SaveIcon className="size-4" />
            {update.isPending ? "저장 중..." : "저장"}
          </Button>
        </div>
        <PineEditor
          value={source}
          onChange={setSource}
          onTriggerParse={() => source.trim() && manualParse.mutate(source)}
          height={520}
        />
      </div>
      <ParsePreviewPanel result={result} loading={loading} />
    </div>
  );
}
