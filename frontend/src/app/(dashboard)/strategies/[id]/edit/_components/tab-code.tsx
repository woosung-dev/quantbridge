"use client";

// Sprint 7c T5: 코드 탭 — Monaco Pine 에디터 + 실시간 파싱 미리보기 + 저장 mutation.
// ParsePreviewPanel은 T4 /strategies/new 에서 재사용 (동일 UX 유지).

import { useState } from "react";
import { SaveIcon } from "lucide-react";
import { toast } from "sonner";

import { PineEditor } from "@/components/monaco/pine-editor";
import { Button } from "@/components/ui/button";
import { useParseStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";

import { ParsePreviewPanel } from "../../../new/_components/parse-preview-panel";

export function TabCode({ strategy }: { strategy: StrategyResponse }) {
  const [source, setSource] = useState(strategy.pine_source);
  const dirty = source !== strategy.pine_source;
  const parse = useParseStrategy();
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("저장되었습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

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
          onTriggerParse={() => source.trim() && parse.mutate(source)}
          height={520}
        />
      </div>
      <ParsePreviewPanel result={parse.data ?? null} loading={parse.isPending} />
    </div>
  );
}
