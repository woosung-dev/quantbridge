// 전략 파싱 결과 패널 — stagger entrance + 초록 점 pulse (Sprint 42-polish W3-fidelity)
// loading: skeleton / error: 빨강 / null: empty hint / present: kv-list 2-col + feature pills
// prefers-reduced-motion: stagger animation은 motion-safe class 로 자동 disable
// aria-live="polite": result 변경 시 screen reader 알림
// W3-fidelity 정합: padding 22/20, h4 0.72rem, kv text 0.82rem, animationDelay 100/200/300/400ms

import { CheckIcon, XIcon } from "lucide-react";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

interface ParseResultPanelProps {
  result: ParsePreviewResponse | null;
  loading: boolean;
  error?: string | null;
}

export function ParseResultPanel({ result, loading, error = null }: ParseResultPanelProps) {
  return (
    <aside
      aria-live="polite"
      aria-label="실시간 파싱 결과"
      // prototype 07: padding 20px 22px (vertical 20 / horizontal 22)
      className="rounded-[var(--radius-md,0.625rem)] border border-[color:var(--primary-100)] bg-[color:var(--primary-light)] px-[22px] py-5"
    >
      <header className="mb-4 flex items-center gap-2.5">
        <span
          aria-hidden
          className={
            "block size-2 rounded-full " +
            (loading
              ? "animate-pulse bg-[color:var(--primary)]"
              : result
                ? "bg-[#22C55E] motion-safe:animate-[pulseDot_1.6s_ease-out_infinite]"
                : "bg-[color:var(--text-muted)]")
          }
        />
        <h3 className="font-display text-[0.9rem] font-bold text-[color:var(--primary)]">
          {loading ? "파싱 중..." : "실시간 파싱 결과"}
        </h3>
      </header>

      {error && <ErrorBlock message={error} />}
      {!error && loading && <LoadingSkeleton />}
      {!error && !loading && !result && <EmptyHint />}
      {!error && !loading && result && <ResultBody result={result} />}
    </aside>
  );
}

function LoadingSkeleton() {
  return (
    <div role="status" aria-label="파싱 중" className="space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-3 rounded bg-[color:var(--primary-100)]/60 animate-pulse"
          style={{ width: `${100 - i * 12}%` }}
        />
      ))}
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-[var(--radius-sm,0.375rem)] border border-[color:var(--destructive)]/30 bg-[color:var(--destructive-light)] px-3 py-2 text-xs text-[color:var(--destructive)]"
    >
      {message}
    </p>
  );
}

function EmptyHint() {
  return (
    <p className="text-xs text-[color:var(--text-secondary)]">
      코드 입력 후 파싱 결과가 여기 표시됩니다.
    </p>
  );
}

function ResultBody({ result }: { result: ParsePreviewResponse }) {
  // Sprint 42-polish W3-fidelity: prototype 07 의 preview-grid 2-col 매칭
  // 좌: 감지된 전략 정보 (status, pine version, entry/exit count)
  // 우: 감지된 함수 (functions_used 상위 4개) — schema 에 parameters 미제공이라 functions_used 로 대체.
  const infoRows: Array<{ key: string; value: string; muted?: boolean }> = [
    { key: "상태", value: STATUS_LABEL[result.status] },
    { key: "버전", value: `Pine ${result.pine_version}` },
    { key: "진입 신호", value: String(result.entry_count) },
    { key: "청산 신호", value: String(result.exit_count) },
  ];

  const topFunctions = result.functions_used.slice(0, 4);

  return (
    <>
      {/* prototype 07: preview-grid `gap: 20px` ≈ gap-5 */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <h4 className="mb-2.5 text-[0.72rem] font-bold uppercase tracking-[0.05em] text-[color:var(--text-secondary)]">
            감지된 전략 정보
          </h4>
          <ul className="m-0 list-none space-y-2 p-0">
            {infoRows.map((row, idx) => (
              <li
                key={row.key}
                data-testid="parse-info-row"
                // prototype 07: 100/200/300/400ms 순차 stagger.
                className="motion-safe:animate-[staggerIn_400ms_cubic-bezier(0.4,0,0.2,1)_forwards] flex items-baseline justify-between gap-2.5 text-[0.82rem] opacity-0"
                style={{ animationDelay: `${(idx + 1) * 100}ms` }}
              >
                <span className="whitespace-nowrap text-[color:var(--text-secondary)]">
                  {row.key}
                </span>
                <span
                  className={
                    "text-right font-mono text-[0.8rem] font-semibold " +
                    (row.muted
                      ? "text-[color:var(--text-muted)]"
                      : "text-[color:var(--text-primary)]")
                  }
                >
                  {row.value}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="mb-2.5 text-[0.72rem] font-bold uppercase tracking-[0.05em] text-[color:var(--text-secondary)]">
            감지된 함수 ({result.functions_used.length}개)
          </h4>
          {topFunctions.length === 0 ? (
            <p className="text-[0.7rem] text-[color:var(--text-muted)]">없음</p>
          ) : (
            <ul className="m-0 list-none space-y-2 p-0">
              {topFunctions.map((fn, idx) => (
                <li
                  key={fn}
                  data-testid="parse-fn-row"
                  className="motion-safe:animate-[staggerIn_400ms_cubic-bezier(0.4,0,0.2,1)_forwards] flex items-baseline gap-2.5 text-[0.82rem] opacity-0"
                  style={{ animationDelay: `${(idx + 5) * 100}ms` }}
                >
                  <span className="truncate font-mono text-[0.8rem] font-semibold text-[color:var(--text-primary)]">
                    {fn}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* feature pills: 진입/청산/실행 가능 — prototype 07 의 dashed top border + pill 스타일 */}
      <div className="mt-4 flex flex-wrap gap-2 border-t border-dashed border-[color:var(--primary-100)] pt-3.5">
        <FeaturePill label="진입 시그널" present={result.entry_count > 0} />
        <FeaturePill label="청산 시그널" present={result.exit_count > 0} />
        <FeaturePill
          label="실행 가능"
          present={result.is_runnable && result.unsupported_builtins.length === 0}
        />
      </div>

      {result.unsupported_builtins.length > 0 && (
        <p className="mt-3 text-[0.7rem] text-[color:var(--text-secondary)]">
          미지원 함수 {result.unsupported_builtins.length}개 — 백테스트 실행 불가
        </p>
      )}
    </>
  );
}

function FeaturePill({ label, present }: { label: string; present: boolean }) {
  return (
    <span
      // prototype 07: padding 4px 10px, font-size 0.72rem, font-weight 600
      className={
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.72rem] font-semibold " +
        (present
          ? "border-[color:var(--primary-100)] bg-white text-[color:var(--primary)]"
          : "border-[color:var(--border)] bg-[color:var(--bg-alt)] text-[color:var(--text-muted)]")
      }
    >
      {present ? (
        <CheckIcon
          className="size-3 text-[color:var(--success)]"
          strokeWidth={3.5}
          aria-hidden
        />
      ) : (
        <XIcon
          className="size-3 text-[color:var(--text-muted)]"
          strokeWidth={3.5}
          aria-hidden
        />
      )}
      {label}
    </span>
  );
}

const STATUS_LABEL: Record<ParsePreviewResponse["status"], string> = {
  ok: "변환 완료",
  unsupported: "일부 미지원",
  error: "오류",
};
