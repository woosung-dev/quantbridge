"use client";

// Sprint 32-B (BL-169): ChartLegend — Equity / Buy & Hold / Drawdown 시리즈
// 색상·라인 스타일 inline 명시. ui-ux-pro-max 진단 P0 #4 (Legend 부재) 해소.
//
// 사용자 코멘트 (dogfood Day 4 = 5/10): "지표 표시가 뭘 의미하는지 도대체 모르겠어"
// → 차트 우측 상단 inline Legend 로 series 의미 즉시 식별 가능하게 함.
//
// 색상은 trading-chart.tsx 의 default 와 정합:
// - Equity: #22c55e (green-500), solid
// - Buy & Hold: #3b82f6 (blue-500), dashed (LineStyle.Dashed = 2)
// - Drawdown: #ef4444 (red-500), area
//
// 디자인: shadcn 스타일 (rounded-md border bg-card/80 backdrop-blur).
// 모바일 wrap 가능하도록 flex-wrap.

interface ChartLegendProps {
  /** Buy & Hold 시리즈가 차트에 표시되는지. false 면 항목 hide. */
  showBenchmark?: boolean;
  /** Drawdown 영역이 차트에 표시되는지. false 면 항목 hide. */
  showDrawdown?: boolean;
  /** 추가 클래스 (호출 측 위치/마진 조정용). */
  className?: string;
}

export function ChartLegend({
  showBenchmark = true,
  showDrawdown = true,
  className,
}: ChartLegendProps) {
  return (
    <div
      role="list"
      aria-label="차트 범례"
      className={[
        "flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border bg-card/80 px-3 py-2 text-xs text-muted-foreground backdrop-blur-sm",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <LegendItem
        ariaLabel="Equity (자본 곡선): 실선 녹색"
        marker={
          <span
            aria-hidden="true"
            className="inline-block h-[2px] w-5 rounded"
            style={{ backgroundColor: "#22c55e" }}
          />
        }
        label="Equity (자본 곡선)"
      />

      {showBenchmark && (
        <LegendItem
          ariaLabel="Buy & Hold 벤치마크: 점선 파란색"
          marker={
            <span
              aria-hidden="true"
              className="inline-flex w-5 items-center justify-between"
              style={{ height: "2px" }}
            >
              <span
                className="inline-block h-[2px] w-1"
                style={{ backgroundColor: "#3b82f6" }}
              />
              <span
                className="inline-block h-[2px] w-1"
                style={{ backgroundColor: "#3b82f6" }}
              />
              <span
                className="inline-block h-[2px] w-1"
                style={{ backgroundColor: "#3b82f6" }}
              />
            </span>
          }
          label="Buy & Hold (단순보유)"
        />
      )}

      {showDrawdown && (
        <LegendItem
          ariaLabel="Drawdown (손실 폭): 빨간 영역"
          marker={
            <span
              aria-hidden="true"
              className="inline-block h-3 w-5 rounded-sm"
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.35)",
                border: "1px solid rgba(239, 68, 68, 0.55)",
              }}
            />
          }
          label="Drawdown (손실 폭)"
        />
      )}
    </div>
  );
}

interface LegendItemProps {
  ariaLabel: string;
  marker: React.ReactNode;
  label: string;
}

function LegendItem({ ariaLabel, marker, label }: LegendItemProps) {
  return (
    <span
      role="listitem"
      aria-label={ariaLabel}
      className="inline-flex items-center gap-1.5"
    >
      {marker}
      <span className="text-foreground/80">{label}</span>
    </span>
  );
}
