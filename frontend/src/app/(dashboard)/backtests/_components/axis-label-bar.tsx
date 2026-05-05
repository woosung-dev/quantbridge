"use client";

// Sprint 32-C (BL-172): AxisLabelBar — Y축/X축 단위 inline 라벨.
//
// 목적 (ui-ux-pro-max 진단 P0 #1 해소):
// - 사용자 코멘트 (dogfood Day 4): "-9855.71 USDT 인지 % 인지 도대체 모르겠어"
// - lightweight-charts 는 priceFormat=price/percent 로 tick label 만 표시 — 단위
//   자체는 별도 안내 필요
//
// 설계:
// - 차트 pane 바로 아래 한 줄 axis label bar (Y축 단위 + X축 단위 + variant 색상)
// - shadcn 스타일 (text-xs text-muted-foreground)
// - variant=equity/drawdown 으로 좌측 dot 색상 구분 (legend 와 정합)
// - 모바일 wrap: flex-wrap + space-x

interface AxisLabelBarProps {
  /** Y축 단위 라벨 (예: "USDT (자본금)" / "% (자본 대비 손실)"). */
  yAxisLabel: string;
  /** X축 단위 라벨 (예: "시간 · 1h 단위 캔들"). */
  xAxisLabel: string;
  /** 시각 구분용 — equity (green) / drawdown (red). */
  variant: "equity" | "drawdown";
}

export function AxisLabelBar({
  yAxisLabel,
  xAxisLabel,
  variant,
}: AxisLabelBarProps) {
  const dotColor = variant === "equity" ? "#22c55e" : "#ef4444";
  const ariaLabel =
    variant === "equity"
      ? "자본 곡선 차트 축 단위 안내"
      : "Drawdown 차트 축 단위 안내";

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      data-testid={`axis-label-bar-${variant}`}
      className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 px-1 text-[11px] text-muted-foreground"
    >
      <span
        aria-hidden="true"
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: dotColor }}
      />
      <span data-testid="y-axis-label">
        <span className="font-medium text-foreground/70">Y축:</span> {yAxisLabel}
      </span>
      <span aria-hidden="true" className="text-muted-foreground/40">
        ·
      </span>
      <span data-testid="x-axis-label">
        <span className="font-medium text-foreground/70">X축:</span> {xAxisLabel}
      </span>
    </div>
  );
}
