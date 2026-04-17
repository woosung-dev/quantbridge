"use client";

// Sprint 7c T5 + Sprint 7b ISSUE-004: 파싱 결과 탭.
// 섹션 순서: (1) 에러 → (2) 경고 → (3) 감지 지표/전략 콜 → (4) 메타.
// 마운트 자동 파싱은 useQuery(usePreviewParse) — StrictMode-safe.
// 저장 시점 스냅샷(strategy.parse_errors)은 라이브 결과와 구분 표시.

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { usePreviewParse } from "@/features/strategy/hooks";
import type { ParseError, StrategyResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

function groupFunctions(fns: readonly string[]): {
  indicators: string[];
  strategies: string[];
  others: string[];
} {
  const indicators: string[] = [];
  const strategies: string[] = [];
  const others: string[] = [];
  for (const fn of fns) {
    if (fn.startsWith("ta.")) indicators.push(fn);
    else if (fn.startsWith("strategy.") || fn === "strategy") strategies.push(fn);
    else others.push(fn);
  }
  return { indicators, strategies, others };
}

function normalizeSnapshotError(raw: Record<string, unknown>): ParseError {
  const code = typeof raw.code === "string" ? raw.code : "";
  const message =
    typeof raw.message === "string" ? raw.message : JSON.stringify(raw);
  const line = typeof raw.line === "number" ? raw.line : null;
  return { code, message, line };
}

export function TabParse({ strategy }: { strategy: StrategyResponse }) {
  const preview = usePreviewParse(strategy.pine_source);
  const live = preview.data;

  const meta = PARSE_STATUS_META[live?.status ?? strategy.parse_status];
  const liveErrors = live?.errors ?? [];
  const snapshotErrors = (strategy.parse_errors ?? []).map(normalizeSnapshotError);

  const warnings = live?.warnings ?? [];
  const functions = live?.functions_used ?? [];
  const { indicators, strategies, others } = groupFunctions(functions);
  const hasFunctions =
    indicators.length > 0 || strategies.length > 0 || others.length > 0;

  return (
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
      <CardContent className="space-y-5">
        {/* (1) 에러 섹션 — 실시간 + 저장 시점 구분 */}
        {(liveErrors.length > 0 || snapshotErrors.length > 0) && (
          <section>
            <h3 className="text-sm font-bold text-[color:var(--destructive)]">
              에러
            </h3>
            {liveErrors.length > 0 && (
              <ErrorList label="현재 코드" errors={liveErrors} />
            )}
            {snapshotErrors.length > 0 && (
              <ErrorList label="저장 시점" errors={snapshotErrors} />
            )}
          </section>
        )}

        {/* (2) 경고 섹션 */}
        {warnings.length > 0 && (
          <section>
            <h3 className="text-sm font-bold text-[color:var(--text-secondary)]">
              경고 ({warnings.length})
            </h3>
            <ul className="mt-2 space-y-1 text-xs text-[color:var(--text-secondary)]">
              {warnings.map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
            </ul>
          </section>
        )}

        {/* (3) 감지 지표 / 전략 콜 / 기타 */}
        {hasFunctions && (
          <section>
            <h3 className="text-sm font-bold">
              감지된 함수 ({functions.length})
            </h3>
            <div className="mt-2 space-y-2">
              {indicators.length > 0 && (
                <DetectedGroup label="지표" items={indicators} />
              )}
              {strategies.length > 0 && (
                <DetectedGroup label="전략 콜" items={strategies} />
              )}
              {others.length > 0 && <DetectedGroup label="기타" items={others} />}
            </div>
          </section>
        )}

        {preview.isFetching && !live && (
          <p className="text-xs text-[color:var(--text-muted)]">
            저장된 코드를 파싱 중입니다...
          </p>
        )}

        {/* (4) 메타 */}
        <section>
          <dl className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2">
            <div>
              <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                버전
              </dt>
              <dd className="mt-1 font-mono">
                Pine {live?.pine_version ?? strategy.pine_version}
              </dd>
            </div>
            <div>
              <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                아카이브 상태
              </dt>
              <dd className="mt-1">{strategy.is_archived ? "보관됨" : "활성"}</dd>
            </div>
            {live && (
              <>
                <div>
                  <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                    진입 신호
                  </dt>
                  <dd className="mt-1 font-mono">{live.entry_count}</dd>
                </div>
                <div>
                  <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                    청산 신호
                  </dt>
                  <dd className="mt-1 font-mono">{live.exit_count}</dd>
                </div>
              </>
            )}
          </dl>
        </section>

        <p className="text-xs text-[color:var(--text-muted)]">
          ※ &apos;현재 코드&apos; 섹션은 마운트 시 자동 파싱 결과. &apos;저장 시점&apos;은 최근 저장에서 DB에 기록된 스냅샷입니다.
        </p>
      </CardContent>
    </Card>
  );
}

function ErrorList({
  label,
  errors,
}: {
  label: string;
  errors: readonly ParseError[];
}) {
  return (
    <div className="mt-2">
      <p className="text-[0.65rem] text-[color:var(--text-muted)]">{label}</p>
      <ul className="mt-1 space-y-1 text-xs">
        {errors.map((e, i) => (
          <li
            key={i}
            className="rounded border border-[color:var(--destructive-light)] bg-[color:var(--destructive-light)] p-2 font-mono"
          >
            {e.line !== null && <span className="mr-1">L{e.line}:</span>}
            {e.code && (
              <span className="mr-2 text-[color:var(--destructive)]">
                [{e.code}]
              </span>
            )}
            {e.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DetectedGroup({
  label,
  items,
}: {
  label: string;
  items: readonly string[];
}) {
  return (
    <div>
      <p className="text-[0.65rem] text-[color:var(--text-muted)]">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {items.map((fn) => (
          <Badge key={fn} variant="outline" className="font-mono text-[0.65rem]">
            {fn}
          </Badge>
        ))}
      </div>
    </div>
  );
}
