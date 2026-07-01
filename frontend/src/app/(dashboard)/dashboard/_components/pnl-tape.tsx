// "P&L Tape" 시그니처 — 구간별 손익 델타를 얇은 상승(bullish)/하락(bearish) 마이크로바로 표시
"use client";

import { useMemo } from "react";

interface PnlTapeProps {
  /** 누적이 아닌 "구간 델타" 값 배열 (양수=이익, 음수=손실). */
  deltas: readonly number[];
  /** 표시할 최대 바 개수 (끝에서 slice). default 48. */
  maxBars?: number;
  className?: string;
}

export function PnlTape({ deltas, maxBars = 48, className }: PnlTapeProps) {
  const bars = useMemo(() => {
    const sliced = deltas.slice(-maxBars);
    const peak = sliced.reduce((m, d) => Math.max(m, Math.abs(d)), 0) || 1;
    return sliced.map((d) => ({
      // 최소 6% 높이 보장 → 0 근처도 가시화.
      height: Math.max(6, (Math.abs(d) / peak) * 100),
      up: d >= 0,
    }));
  }, [deltas, maxBars]);

  if (bars.length === 0) {
    // 데이터 없음 — faint baseline 틱으로 시그니처 자리 유지.
    return (
      <div
        className={`flex h-6 items-center gap-[2px] ${className ?? ""}`}
        aria-hidden="true"
      >
        {Array.from({ length: 40 }).map((_, i) => (
          <span
            key={i}
            className="min-w-[2px] flex-1 rounded-[1px] bg-muted-foreground/25"
            style={{ height: "18%" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`flex h-6 items-center gap-[2px] ${className ?? ""}`}
      role="img"
      aria-label="구간별 손익 추이 마이크로바"
    >
      {bars.map((b, i) => (
        <span
          key={i}
          className="min-w-[2px] flex-1 rounded-[1px]"
          style={{
            height: `${b.height}%`,
            backgroundColor: b.up ? "var(--bullish)" : "var(--bearish)",
            opacity: 0.85,
          }}
        />
      ))}
    </div>
  );
}
