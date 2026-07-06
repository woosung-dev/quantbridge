"use client";

// Sprint 32-B (BL-169): ChartLegend — Equity / Buy & Hold / Drawdown 시리즈
// 색상·라인 스타일 inline 명시. ui-ux-pro-max 진단 P0 #4 (Legend 부재) 해소.
//
// 사용자 코멘트 (dogfood Day 4 = 5/10): "지표 표시가 뭘 의미하는지 도대체 모르겠어"
// → 차트 우측 상단 inline Legend 로 series 의미 즉시 식별 가능하게 함.
//
// 색상은 trading-chart.tsx 의 default(chart-tokens SSOT) 와 정합 — CSS 변수 경유:
// - Equity: var(--chart-equity), solid
// - Buy & Hold: var(--chart-benchmark), dashed (LineStyle.Dashed = 2)
// - Compare: var(--chart-compare), solid
// - Drawdown: var(--chart-dd-top/-line), area
// DOM 마커라 var() 직접 사용 가능 — 테마 토글 시 자동 flip (DESIGN.md §2.3).
//
// 디자인: shadcn 스타일 (rounded-md border bg-card/80 backdrop-blur).
// 모바일 wrap 가능하도록 flex-wrap.

interface ChartLegendProps {
  /** Buy & Hold 시리즈가 차트에 표시되는지. false 면 항목 hide. */
  showBenchmark?: boolean;
  /** Drawdown 영역이 차트에 표시되는지. false 면 항목 hide. */
  showDrawdown?: boolean;
  /** Compare 오버레이(다른 백테스트)가 표시되는지. false 면 항목 hide. */
  showCompare?: boolean;
  /** Compare 대상 라벨 (예: "ETH · 1h"). */
  compareLabel?: string;
  /** 추가 클래스 (호출 측 위치/마진 조정용). */
  className?: string;
}

export function ChartLegend({
  showBenchmark = true,
  showDrawdown = true,
  showCompare = false,
  compareLabel,
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
            style={{ backgroundColor: "var(--chart-equity)" }}
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
                style={{ backgroundColor: "var(--chart-benchmark)" }}
              />
              <span
                className="inline-block h-[2px] w-1"
                style={{ backgroundColor: "var(--chart-benchmark)" }}
              />
              <span
                className="inline-block h-[2px] w-1"
                style={{ backgroundColor: "var(--chart-benchmark)" }}
              />
            </span>
          }
          label="Buy & Hold (단순보유)"
        />
      )}

      {showCompare && (
        <LegendItem
          ariaLabel={`비교 백테스트${compareLabel ? ` ${compareLabel}` : ""}: 실선 보라색`}
          marker={
            <span
              aria-hidden="true"
              className="inline-block h-[2px] w-5 rounded"
              style={{ backgroundColor: "var(--chart-compare)" }}
            />
          }
          label={`비교${compareLabel ? ` · ${compareLabel}` : ""}`}
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
                backgroundColor: "var(--chart-dd-top)",
                border: "1px solid var(--chart-dd-line)",
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
