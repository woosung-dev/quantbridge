"use client";

// Sprint FE-01 / FE-03:
// 요약 카드 + ParseDialog 런처. Sprint FE-03 에서 편집 버퍼를 Zustand edit-store 로 구독,
// 500ms debounce 후 preview 재파싱 — TabCode 가 편집해도 TabParse 가 최신 상태 반영.
//
// debounce 패턴은 LESSON-006 엄수 (ref.current = render body 대입 금지):
//  1) sync useEffect (deps 없음) 에서 ref.current <- 최신 값 commit
//  2) 별도 useEffect 의 scalar dep (pineSource) 로 debounce timer 트리거
//
// 저장 액션은 dialog 내부 "이 전략 저장" 버튼이 Zustand store 의 최신 pineSource 를
// 그대로 사용해 useUpdateStrategy → markSaved 호출 (header 저장 버튼과 동일 로직).

import { useEffect, useRef, useState } from "react";
import { SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  selectPineSource,
  useEditStore,
} from "@/features/strategy/edit-store";
import { usePreviewParse, useUpdateStrategy } from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

import { ParseDialog } from "./parse-dialog";

const PREVIEW_DEBOUNCE_MS = 500;

/**
 * pineSource 값이 변경된 뒤 `delay` ms 동안 추가 변경이 없을 때 반환값이 갱신된다.
 *
 * ref.current 를 render body 에서 직접 대입하면 React Compiler 의 "refs during render"
 * 규칙 위반이라, `draft.ts` 의 useAutoSaveDraft 패턴 그대로
 *  - sync useEffect (deps 없음) 에서 ref 최신값 commit
 *  - 별도 useEffect 에서 primitive dep 기반 timeout schedule
 * 로 분리한다.
 */
function useDebouncedValue(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value);
  const valueRef = useRef(value);

  useEffect(() => {
    valueRef.current = value;
  });

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(valueRef.current);
    }, delay);
    return () => clearTimeout(t);
  }, [value, delay]);

  return debounced;
}

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const pineSource = useEditStore(selectPineSource);
  const debouncedSource = useDebouncedValue(pineSource, PREVIEW_DEBOUNCE_MS);
  const preview = usePreviewParse(debouncedSource);
  const live = preview.data;
  const [dialogOpen, setDialogOpen] = useState(false);

  const markSaved = useEditStore((s) => s.markSaved);
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => {
      markSaved(new Date());
      toast.success("전략을 저장했습니다");
    },
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  const meta = PARSE_STATUS_META[live?.status ?? strategy.parse_status];
  const canWalkthrough = Boolean(live);
  const previewError = preview.isError ? (preview.error as Error).message : null;

  const handleSaveFromDialog = () => {
    update.mutate({ pine_source: pineSource });
  };
  const handleRetry = () => {
    preview.refetch();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Badge variant="outline" data-tone={meta.tone}>
              {meta.label}
            </Badge>
            <Badge variant="secondary">
              Pine {live?.pine_version ?? strategy.pine_version}
            </Badge>
            {preview.isFetching && (
              <span className="text-xs text-[color:var(--text-muted)]">
                파싱 중...
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <Summary
              label="에러"
              value={live?.errors.length ?? 0}
              tone="destructive"
            />
            <Summary
              label="경고"
              value={live?.warnings.length ?? 0}
              tone="warn"
            />
            <Summary
              label="감지 함수"
              value={live?.functions_used.length ?? 0}
              tone="info"
            />
          </dl>
          {previewError ? (
            <div className="rounded border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-2 text-xs">
              <p className="font-bold text-[color:var(--destructive)]">
                파싱 요청 실패
              </p>
              <p className="mt-1 font-mono">{previewError}</p>
              <Button variant="outline" onClick={handleRetry} className="mt-2">
                다시 시도
              </Button>
            </div>
          ) : (
            <Button
              onClick={() => setDialogOpen(true)}
              disabled={!canWalkthrough || update.isPending}
              className="w-full"
            >
              <SparklesIcon className="mr-1 size-4" />
              {canWalkthrough ? "파싱 결과 해설 시작" : "파싱 준비 중..."}
            </Button>
          )}
          <p className="text-xs text-[color:var(--text-muted)]">
            ※ 자연어 해설로 각 함수·에러·경고를 단계별 확인할 수 있습니다.
          </p>
        </CardContent>
      </Card>
      {live && (
        <ParseDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          result={live}
          onSave={handleSaveFromDialog}
        />
      )}
    </>
  );
}

function Summary({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "destructive" | "warn" | "info";
}) {
  const colorClass =
    tone === "destructive"
      ? "text-[color:var(--destructive)]"
      : tone === "warn"
        ? "text-amber-600"
        : "text-[color:var(--text-primary)]";
  return (
    <div>
      <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
        {label}
      </dt>
      <dd className={`mt-1 font-mono text-lg ${colorClass}`}>{value}</dd>
    </div>
  );
}
