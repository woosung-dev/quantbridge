"use client";

// Sprint 7c T4 + Sprint 7b ISSUE-003/004: 실시간 파싱 결과 패널.
// - Sprint 7c: aria-live + status badges + entry/exit count + warnings/errors.
// - Sprint 7b: functions_used 섹션 (감지 지표 / 전략 콜 / 기타) + 빈 상태 copy 수정.

import { CheckIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
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
          ⌘+Enter로 첫 파싱을 실행하세요.
        </p>
      )}

      {result && <ResultBody result={result} />}
    </aside>
  );
}

function ResultBody({ result }: { result: ParsePreviewResponse }) {
  const { indicators, strategies, others } = groupFunctions(result.functions_used);
  const hasFunctions =
    indicators.length > 0 || strategies.length > 0 || others.length > 0;

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge variant="outline" data-tone={PARSE_STATUS_META[result.status].tone}>
          {PARSE_STATUS_META[result.status].label}
        </Badge>
        <Badge variant="secondary">Pine {result.pine_version}</Badge>
      </div>

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

      {result.status === "unsupported" && (
        <p className="mt-3 text-xs text-[color:var(--text-secondary)]">
          <strong>저장은 가능합니다.</strong> 백테스트 실행 시 해당 함수는 제외되거나 에러를 반환합니다.
        </p>
      )}

      {result.warnings.length > 0 && (
        <section className="mt-3">
          <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
            경고 ({result.warnings.length})
          </h4>
          <ul className="mt-1 space-y-1 text-xs text-[color:var(--text-secondary)]">
            {result.warnings.slice(0, 5).map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        </section>
      )}

      {result.errors.length > 0 && (
        <section className="mt-3">
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
        </section>
      )}

      {hasFunctions && (
        <section className="mt-3">
          <h4 className="text-[0.65rem] font-bold uppercase tracking-wide text-[color:var(--text-secondary)]">
            감지된 함수 ({result.functions_used.length})
          </h4>
          {indicators.length > 0 && (
            <FunctionSubsection label="지표" items={indicators} />
          )}
          {strategies.length > 0 && (
            <FunctionSubsection label="전략 콜" items={strategies} />
          )}
          {others.length > 0 && (
            <FunctionSubsection label="기타" items={others.slice(0, 5)} />
          )}
        </section>
      )}
    </>
  );
}

function FunctionSubsection({
  label,
  items,
}: {
  label: string;
  items: readonly string[];
}) {
  return (
    <div className="mt-2">
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
