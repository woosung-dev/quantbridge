"use client";

// Sprint 7c T4: 실시간 파싱 결과 패널 — aria-live + status badges + entry/exit count + warnings/errors.
// Pass 3 microcelebration: status=ok일 때 scale-in 체크마크 애니메이션 + actionable microcopy.

import { CheckIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { PARSE_STATUS_META } from "@/features/strategy/utils";

export function ParsePreviewPanel({
  result,
  loading,
}: {
  result: ParsePreviewResponse | null;
  loading: boolean;
}) {
  return (
    <aside
      aria-live="polite"
      aria-label="실시간 파싱 결과"
      className="rounded-[var(--radius-md)] border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] p-5"
    >
      <header className="mb-3 flex items-center gap-2">
        <span
          aria-hidden
          className={
            "block size-2 rounded-full " +
            (loading ? "animate-pulse bg-[color:var(--primary)]" : "bg-[color:var(--success)]")
          }
        />
        <h3 className="font-display text-sm font-bold text-[color:var(--primary)]">
          {loading ? "파싱 중..." : "실시간 파싱 결과"}
        </h3>
      </header>

      {!result && !loading && (
        <p className="text-xs text-[color:var(--text-secondary)]">
          코드를 입력하면 자동으로 파싱 결과가 표시됩니다.
        </p>
      )}

      {result && (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge variant="outline" data-tone={PARSE_STATUS_META[result.status].tone}>
              {PARSE_STATUS_META[result.status].label}
            </Badge>
            <Badge variant="secondary">Pine {result.pine_version}</Badge>
          </div>

          {/* Pass 3 microcelebration: ok 상태 체크마크 + microcopy */}
          {result.status === "ok" && (
            <div className="mb-3 flex items-center gap-2">
              <span
                className="inline-grid size-5 place-items-center rounded-full bg-[color:var(--success)] text-white motion-safe:animate-[scale-in_200ms_ease-out]"
                aria-hidden
              >
                <CheckIcon className="size-3" strokeWidth={3} />
              </span>
              <span className="text-xs text-[color:var(--success)]">
                변환 완료. 바로 저장할 수 있어요.
              </span>
            </div>
          )}

          <dl className="grid grid-cols-2 gap-y-2 text-xs">
            <dt className="text-[color:var(--text-secondary)]">진입 신호</dt>
            <dd className="text-right font-mono font-semibold">{result.entry_count}</dd>
            <dt className="text-[color:var(--text-secondary)]">청산 신호</dt>
            <dd className="text-right font-mono font-semibold">{result.exit_count}</dd>
          </dl>

          {/* Pass 3 actionable microcopy: unsupported일 때 저장 가능 안내 */}
          {result.status === "unsupported" && (
            <p className="mt-3 text-xs text-[color:var(--text-secondary)]">
              <strong>저장은 가능합니다.</strong> 백테스트 실행 시 해당 함수는 제외되거나 에러를 반환합니다.
            </p>
          )}

          {result.warnings.length > 0 && (
            <div className="mt-3">
              <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
                경고 ({result.warnings.length})
              </h4>
              <ul className="mt-1 space-y-1 text-xs text-[color:var(--text-secondary)]">
                {result.warnings.slice(0, 5).map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}
          {result.errors.length > 0 && (
            <div className="mt-3">
              <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--destructive)]">
                에러 ({result.errors.length})
              </h4>
              <ul className="mt-1 space-y-1 text-xs text-[color:var(--destructive)]">
                {result.errors.slice(0, 5).map((e, i) => (
                  <li key={i}>
                    {e.line !== null && <span className="font-mono">L{e.line}: </span>}
                    {e.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
