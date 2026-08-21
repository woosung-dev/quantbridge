// 테이프 진행률 바 — P&L Tape 모티프의 진행률 변형 (채워진 틱 = 코퍼, 미채움 = 보더색)
"use client";

import { cn } from "@/lib/utils";

interface TapeProgressProps {
  /** 0~100. null/undefined 는 indeterminate (전 틱 페이드 애니메이션). */
  value?: number | null;
  /** 틱 개수. default 24. */
  segments?: number;
  /** 스크린리더 레이블. */
  ariaLabel?: string;
  className?: string;
}

export function TapeProgress({
  value,
  segments = 24,
  ariaLabel = "진행률",
  className,
}: TapeProgressProps) {
  const clamped = value == null ? null : Math.max(0, Math.min(100, Math.round(value)));
  const filled = clamped == null ? 0 : Math.round((clamped / 100) * segments);

  return (
    <div
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped ?? undefined}
      className={cn("flex h-3 items-stretch gap-[2px]", className)}
    >
      {Array.from({ length: segments }, (_, segment) => segment).map((segment) => (
        <span
          key={segment}
          className={cn(
            "min-w-[2px] flex-1 rounded-[1px] transition-colors duration-200",
            clamped == null
              ? "animate-pulse bg-muted-foreground/25"
              : segment < filled
                ? "bg-primary"
                : "bg-border-dark",
          )}
        />
      ))}
    </div>
  );
}
