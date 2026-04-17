"use client";

// Sprint 7c T5: 파싱 결과 탭 — 저장 시점에 스냅샷된 parse_status/errors 표시.
// 실시간 파싱은 코드 탭의 우측 ParsePreviewPanel이 담당.

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const meta = PARSE_STATUS_META[strategy.parse_status];
  const errors = strategy.parse_errors ?? [];
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Badge variant="outline" data-tone={meta.tone}>
            {meta.label}
          </Badge>
          <Badge variant="secondary">Pine {strategy.pine_version}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
          <div>
            <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
              버전
            </dt>
            <dd className="mt-1 font-mono">Pine {strategy.pine_version}</dd>
          </div>
          <div>
            <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
              아카이브 상태
            </dt>
            <dd className="mt-1">{strategy.is_archived ? "보관됨" : "활성"}</dd>
          </div>
        </dl>
        {errors.length > 0 && (
          <div>
            <h3 className="text-sm font-bold text-[color:var(--destructive)]">
              저장 당시 에러 ({errors.length})
            </h3>
            <ul className="mt-2 space-y-1 text-xs">
              {errors.map((e, i) => (
                <li
                  key={i}
                  className="rounded border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-2 font-mono"
                >
                  {JSON.stringify(e)}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="text-xs text-[color:var(--text-muted)]">
          ※ 실시간 파싱은 코드 탭의 우측 패널을 참조하세요. 이 탭은{" "}
          <strong>저장 시점에 스냅샷된</strong> 결과입니다.
        </p>
      </CardContent>
    </Card>
  );
}
