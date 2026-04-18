"use client";

// Sprint FE-01: 요약 카드 + ParseDialog 런처로 전환. 상세 워크스루는 모달에서.
// BE 변경 없음. ParsePreviewResponse 그대로 사용.
// NOTE: TabCode가 pine_source 편집 버퍼를 소유하므로 여기 "저장" 액션은
// 저장된 strategy.pine_source에 대한 re-save (토스트 피드백용). 편집 버퍼 기반
// 저장을 원하면 EditorView로 source state를 리프트업 (TODO).

import { useState } from "react";
import { SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { usePreviewParse, useUpdateStrategy } from "@/features/strategy/hooks";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

import { ParseDialog } from "./parse-dialog";

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const preview = usePreviewParse(strategy.pine_source);
  const live = preview.data;
  const [dialogOpen, setDialogOpen] = useState(false);
  const update = useUpdateStrategy(strategy.id, {
    onSuccess: () => toast.success("전략을 저장했습니다"),
    onError: (e) => toast.error(`저장 실패: ${e.message}`),
  });

  const meta = PARSE_STATUS_META[live?.status ?? strategy.parse_status];
  const canWalkthrough = Boolean(live);
  const previewError = preview.isError ? (preview.error as Error).message : null;

  const handleSave = () => {
    update.mutate({ pine_source: strategy.pine_source });
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
              <span className="text-xs text-[color:var(--text-muted)]">파싱 중...</span>
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
              <Button
                variant="outline"
                onClick={handleRetry}
                className="mt-2"
              >
                다시 시도
              </Button>
            </div>
          ) : (
            <Button
              onClick={() => setDialogOpen(true)}
              disabled={!canWalkthrough}
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
          onSave={handleSave}
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
