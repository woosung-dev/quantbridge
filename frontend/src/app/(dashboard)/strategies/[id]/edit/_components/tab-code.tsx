"use client";

// Sprint 7c T5 + Sprint 7b ISSUE-003: 코드 탭 — Monaco Pine 에디터 + 실시간 파싱 + 저장.
// 마운트 시 저장된 pine_source 자동 파싱으로 우측 패널 빈 상태 오표시 제거.

import { useEffect, useRef, useState } from "react";
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

  // 마운트 자동 파싱 — strategy.id 기준 1회만 실행.
  // StrictMode double-invoke 방어를 위해 id별 ref로 가드.
  const mountedForId = useRef<string | null>(null);
  useEffect(() => {
    if (mountedForId.current === strategy.id) return;
    mountedForId.current = strategy.id;
    if (strategy.pine_source.trim().length > 0) {
      parse.mutate(strategy.pine_source);
    }
    // mutate는 react-query 안정 참조 — deps에서 제외.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy.id, strategy.pine_source]);

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
