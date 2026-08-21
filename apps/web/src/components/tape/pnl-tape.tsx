// "P&L Tape" 시그니처 — 구간별 손익 델타를 얇은 상승(bullish)/하락(bearish) 마이크로바로 표시
// Precision Instrument 브랜드 모티프: dashboard 전용에서 공용 승격 (테이블 인라인 micro 사이즈 추가)
"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";

interface PnlTapeProps {
  /** 누적이 아닌 "구간 델타" 값 배열 (양수=이익, 음수=손실). */
  deltas: readonly number[];
  /** 표시할 최대 바 개수 (끝에서 slice). default 48. */
  maxBars?: number;
  /** micro = 테이블 셀 인라인용 (h-4, 1px gap). default = 기존 h-6. */
  size?: "default" | "micro";
  className?: string;
}

export function PnlTape({ deltas, maxBars = 48, size = "default", className }: PnlTapeProps) {
  const bars = useMemo(() => {
    const sliced = deltas.slice(-maxBars);
    const peak = sliced.reduce((m, d) => Math.max(m, Math.abs(d)), 0) || 1;
    const occurrences = new Map<number, number>();
    return sliced.map((d) => {
      const occurrence = occurrences.get(d) ?? 0;
      occurrences.set(d, occurrence + 1);
      return {
        // 동일 델타도 출현 순서를 더해 list 안에서 유일하게 식별한다.
        key: `${d}-${occurrence}`,
        // 최소 6% 높이 보장 → 0 근처도 가시화.
        height: Math.max(6, (Math.abs(d) / peak) * 100),
        up: d >= 0,
      };
    });
  }, [deltas, maxBars]);

  const frameClass = cn(
    "flex items-center",
    size === "micro" ? "h-4 gap-px" : "h-6 gap-[2px]",
    className,
  );
  const barClass = cn("flex-1 rounded-[1px]", size === "micro" ? "min-w-px" : "min-w-[2px]");

  if (bars.length === 0) {
    // 데이터 없음 — faint baseline 틱으로 시그니처 자리 유지.
    return (
      <div className={frameClass} aria-hidden="true">
        {Array.from({ length: 40 }, (_, slot) => `baseline-${slot}`).map((barKey) => (
          <span
            key={barKey}
            className={cn(barClass, "bg-muted-foreground/25")}
            style={{ height: "18%" }}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={frameClass} role="img" aria-label="구간별 손익 추이 마이크로바">
      {bars.map((b) => (
        <span
          key={b.key}
          className={barClass}
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
