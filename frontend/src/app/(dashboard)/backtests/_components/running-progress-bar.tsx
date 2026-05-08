// 백테스트 실행 상태 시각화 — prototype 09 의 .period-cell.running / .status-pill.running pulseDot 패턴.
//
// running: indeterminate progress bar (pulse animation, 종료 시점 미상)
// queued: pulse dot + "대기" 라벨 (Celery 큐에 진입 후 worker pickup 전)
// 그 외 status: null 반환 (호출 측에서 분기).

import type { BacktestStatus } from "@/features/backtest/schemas";

interface RunningProgressBarProps {
  status: BacktestStatus;
  /** 접근성: aria-label override (기본 status 별 라벨). */
  label?: string;
}

export function RunningProgressBar({ status, label }: RunningProgressBarProps) {
  if (status === "running" || status === "cancelling") {
    return (
      <div
        className="flex min-w-[120px] items-center gap-2"
        role="status"
        aria-live="polite"
        aria-label={label ?? (status === "cancelling" ? "취소 중" : "실행 중")}
        data-testid="running-progress-bar"
      >
        <span
          className="size-1.5 shrink-0 rounded-full bg-[color:var(--primary)]"
          style={{ animation: "qb-pulse-dot 1.6s infinite" }}
          aria-hidden="true"
        />
        <span className="relative h-1 flex-1 overflow-hidden rounded-full bg-[color:var(--bg-alt)]">
          <span
            className="absolute inset-y-0 left-0 w-1/3 rounded-full bg-[color:var(--primary)]"
            style={{ animation: "qb-progress-indeterminate 1.4s ease-in-out infinite" }}
            aria-hidden="true"
          />
        </span>
        <span className="font-mono text-[0.75rem] font-medium text-[color:var(--primary)]">
          {status === "cancelling" ? "취소 중…" : "실행 중…"}
        </span>
      </div>
    );
  }

  if (status === "queued") {
    return (
      <div
        className="flex items-center gap-2"
        role="status"
        aria-live="polite"
        aria-label={label ?? "대기 중"}
        data-testid="queued-pulse"
      >
        <span
          className="size-1.5 shrink-0 rounded-full bg-[color:var(--text-muted)]"
          style={{ animation: "qb-pulse-dot 2s infinite" }}
          aria-hidden="true"
        />
        <span className="font-mono text-[0.75rem] text-[color:var(--text-muted)]">대기 중…</span>
      </div>
    );
  }

  return null;
}
