"use client";

// Sprint 30-β (W2): EquityChartV2 — lightweight-charts 기반 equity curve.
// Sprint 32-B (BL-169 + BL-170): 2-pane split (Equity top + Drawdown bottom)
//   + ChartLegend + Worker C marker hook (extraMarkers prop).
// Sprint 32-C (BL-171 + BL-172): MarkerLayer (의미 있는 trade markers) +
//   AxisLabelBar (Y축/X축 라벨) — ui-ux-pro-max P0 #1 + #5 해소.
// 기존 equity-chart.tsx (recharts) 는 보존 (rollback path). 신규 차트만 lightweight-charts.
// ADR: git:0ddf2b53 docs/dev-log/2026-05-05-sprint30-chart-lib-decision.md
//
// ui-ux-pro-max 진단 (dogfood Day 4 = 5/10) 해소:
// - P0 #1 Y축 단위 모호 (-9855.71 USDT vs %) → AxisLabelBar 로 Y/X 축 단위 명시
//   + DrawdownPane mddExceedsCapital 시 leverage warning inline
// - P0 #2 3 series 시각 구분 불가 → Legend + LineStyle (solid/dashed/area) 명시
// - P0 #3 Drawdown -30000 vs KPI -343.15% 매핑 모호 → Drawdown pane Y축 % only
// - P0 #4 Legend 부재 → ChartLegend inline (top-right)
// - P0 #5 거래 마커 약자 의미 0 → MarkerLayer 가 "L $price" / "+1.23%" 등
//   의미 있는 text + shape (arrow=entry, circle=exit) + 색상 (PnL 부호) 표시
// - P0 #6 Y축 dual scale 부재 → 2-pane 으로 자연스러운 dual scale (각 pane 독립 priceScale)

import { useMemo, useState } from "react";

import {
  normalizeToPercentCurve,
  normalizeToPnlCurve,
} from "@/components/charts/normalize-to-pnl-curve";
import type {
  ChartMarker,
  ChartPoint,
} from "@/components/charts/trading-chart";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";

import { AxisLabelBar } from "@/features/backtest/components/charts/axis-label-bar";
import { ChartLegend } from "@/features/backtest/components/charts/chart-legend";
import { DrawdownPane } from "@/features/backtest/components/charts/drawdown-pane";
import { EquityPane } from "@/features/backtest/components/charts/equity-pane";
import { deriveTradeMarkers } from "@/features/backtest/components/charts/marker-layer";

// 2-pane 비율 (ui-ux-pro-max 권장 60/40).
const TOP_PANE_RATIO = 0.6;
const BOTTOM_PANE_RATIO = 0.4;

// Sprint 43 W10 — prototype 02 타임프레임 탭. ALL = 전체 기간 표시.
type Timeframe = "1M" | "3M" | "6M" | "ALL";

const TIMEFRAME_OPTIONS: ReadonlyArray<{ value: Timeframe; label: string }> = [
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "6M", label: "6M" },
  { value: "ALL", label: "전체" },
];

const TIMEFRAME_DAYS: Record<Exclude<Timeframe, "ALL">, number> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
};

/**
 * 선택된 timeframe 에 맞춰 curve 끝에서 N일 윈도우 슬라이싱.
 * ALL 또는 데이터 부족 시 원본 그대로 반환.
 */
function sliceByTimeframe(
  curve: readonly EquityPoint[],
  tf: Timeframe,
): readonly EquityPoint[] {
  if (tf === "ALL" || curve.length === 0) return curve;
  const days = TIMEFRAME_DAYS[tf];
  const lastTs = curve[curve.length - 1]?.timestamp;
  if (lastTs === undefined) return curve;
  const lastDate = Date.parse(lastTs);
  if (!Number.isFinite(lastDate)) return curve;
  const cutoff = lastDate - days * 24 * 60 * 60 * 1000;
  const filtered = curve.filter((p) => Date.parse(p.timestamp) >= cutoff);
  // 윈도우 내 포인트가 너무 적으면 fallback (시각화 의미 있을 정도까지).
  return filtered.length >= 2 ? filtered : curve;
}

interface EquityChartV2Props {
  equityCurve: readonly EquityPoint[];
  trades?: readonly TradeItem[];
  initialCapital: number;
  /** 전체 차트 영역 높이 (top + bottom 합계). default 360. */
  height?: number;
  /**
   * Worker C marker hook — 외부에서 추가 markers 주입.
   * 자동 계산된 trade markers 와 merge 됨.
   * 본 PR 은 hook point 만 정의 — Worker C (BL-171/172) 가 의미 있는 마커 추가.
   */
  extraMarkers?: readonly ChartMarker[];
  /**
   * Sprint 32-C BL-172: candle 단위 (예: "1h", "1d", "15m"). X축 라벨에 표시.
   * 미지정 시 X축 라벨에 단위 미표시 (그래도 X축 단위 = "시간" 만 안내).
   */
  timeframe?: string;
  /**
   * Sprint 32-C BL-172: BL-156 메타 (`metrics.mdd_exceeds_capital`) pass-through.
   * true 면 DrawdownPane Y축 라벨에 leverage warning inline.
   */
  mddExceedsCapital?: boolean | null;
  /**
   * Sprint 34 BL-175: Buy & Hold benchmark curve (backend OHLCV 첫/끝 close 기반 정확 계산).
   * `metrics.buy_and_hold_curve` 직접 pass-through. null 시 BH series 미렌더 +
   * ChartLegend BH 항목 자동 hide (Sprint 33 hotfix 동작 보존, Surface Trust ADR-019).
   *
   * frontend 자체 계산은 폐기 — `computeBuyAndHold` 는 legacy no-op.
   */
  buyAndHoldCurve?: readonly EquityPoint[] | null;
  /**
   * Compare 오버레이 — 다른 백테스트의 equity_curve. 존재 시 equity/BH/compare 를
   * 모두 % 수익률(시작=0%) 로 정규화해 자본금 상이한 두 백테스트를 동일 축에서 비교.
   * null/미지정 시 기존 PnL(USDT) 표시 유지.
   */
  compareCurve?: readonly EquityPoint[] | null;
  /** Compare 대상 라벨 (범례/a11y 표기). */
  compareLabel?: string;
}

interface DrawdownPoint {
  timestamp: string;
  value: number;
}

/**
 * equity_curve 만으로 drawdown 계산.
 * - peak = running max
 * - drawdown = (current - peak) / peak (음수, 0..-1)
 *
 * NOTE: backend 가 drawdown_curve 를 별도 응답하면 그것을 우선 사용해야 함.
 * 본 컴포넌트는 BE drawdown_curve 부재 시 자체 계산 fallback.
 * BL-156 (Worker D) MDD 수학 검증 시 본 fallback 도 보완 대상.
 */
function computeDrawdownArea(
  curve: readonly EquityPoint[],
): DrawdownPoint[] {
  if (curve.length === 0) return [];
  const out: DrawdownPoint[] = [];
  let peak = curve[0]!.value;
  for (const point of curve) {
    if (!Number.isFinite(point.value)) continue;
    if (point.value > peak) peak = point.value;
    const dd = peak > 0 ? (point.value - peak) / peak : 0; // 음수
    out.push({ timestamp: point.timestamp, value: dd });
  }
  return out;
}

export function EquityChartV2({
  equityCurve,
  trades,
  initialCapital: _initialCapital,
  height = 360,
  extraMarkers,
  timeframe,
  mddExceedsCapital,
  buyAndHoldCurve,
  compareCurve,
  compareLabel,
}: EquityChartV2Props) {
  // Compare 활성 시 % 기준, 아니면 PnL(USDT) 기준으로 모든 series 정규화.
  const comparing = (compareCurve?.length ?? 0) > 0;
  // Sprint 43 W10 — prototype 02 정합. 타임프레임 탭 (1M/3M/6M/전체) +
  // Buy&Hold checkbox + 드로다운 overlay checkbox. 기본값은 ALL + 둘 다 ON.
  const [activeTimeframe, setActiveTimeframe] = useState<Timeframe>("ALL");
  const [showBuyAndHold, setShowBuyAndHold] = useState(true);
  const [showDrawdownOverlay, setShowDrawdownOverlay] = useState(true);

  // 사용자 선택 timeframe 으로 curve 슬라이싱. equity / BH / drawdown 모두 동일 기간 적용.
  const slicedEquity = useMemo(
    () => sliceByTimeframe(equityCurve, activeTimeframe),
    [equityCurve, activeTimeframe],
  );
  const slicedBuyAndHold = useMemo<readonly EquityPoint[] | null>(() => {
    if (!buyAndHoldCurve || buyAndHoldCurve.length === 0) return null;
    return sliceByTimeframe(buyAndHoldCurve, activeTimeframe);
  }, [buyAndHoldCurve, activeTimeframe]);

  // Sprint 37 BL-184: equity / Buy&Hold curve 모두 PnL 기준 (시작=0) 으로 정규화.
  // BE 는 absolute capital (initial_capital 시작) 그대로 유지 — metrics/MC/stress
  // 입력 안전성 우선. FE 표시 단계에서만 첫 값을 baseline 0 으로 정렬해
  // TradingView 표준 + equity vs BH 동일 baseline 비교 가능 (Surface Trust).
  const equityData = useMemo<ChartPoint[]>(() => {
    const norm = comparing ? normalizeToPercentCurve : normalizeToPnlCurve;
    return norm(slicedEquity).map((p) => ({
      time: p.timestamp,
      value: p.value,
    }));
  }, [slicedEquity, comparing]);

  // Compare 대상 백테스트 곡선 — 동일 timeframe 슬라이싱 + % 정규화 후 오버레이.
  const compareData = useMemo<ChartPoint[]>(() => {
    if (!comparing || !compareCurve) return [];
    const sliced = sliceByTimeframe(compareCurve, activeTimeframe);
    return normalizeToPercentCurve(sliced).map((p) => ({
      time: p.timestamp,
      value: p.value,
    }));
  }, [comparing, compareCurve, activeTimeframe]);

  // Sprint 34 BL-175 + Sprint 37 BL-184: backend buy_and_hold_curve 직접 사용
  // (frontend 자체 계산 폐기) + PnL 정규화. null/undefined/빈 배열 시 benchmark
  // series 미추가 → ChartLegend 가 BH 항목 hide. Sprint 43 W10: showBuyAndHold=false 시도 동일하게 hide.
  const benchmarkData = useMemo<ChartPoint[]>(() => {
    if (!showBuyAndHold) return [];
    if (!slicedBuyAndHold || slicedBuyAndHold.length === 0) return [];
    const norm = comparing ? normalizeToPercentCurve : normalizeToPnlCurve;
    return norm(slicedBuyAndHold).map((p) => ({
      time: p.timestamp,
      value: p.value,
    }));
  }, [slicedBuyAndHold, showBuyAndHold, comparing]);

  const drawdownData = useMemo<ChartPoint[]>(() => {
    if (!showDrawdownOverlay) return [];
    return computeDrawdownArea(slicedEquity).map((p) => ({
      time: p.timestamp,
      value: p.value,
    }));
  }, [slicedEquity, showDrawdownOverlay]);

  // Sprint 32-C BL-171: deriveTradeMarkers 사용. 이전 inline 변환 코드 대체.
  // Sprint 34 BL-177: trades 가 30개 초과면 compact mode (entry "L"/"S" 만,
  // exit text "") 로 marker text 겹침 차단 (dogfood Day 6 BUG #3 해소).
  const tradeMarkers = useMemo<ChartMarker[]>(
    () =>
      deriveTradeMarkers(trades, {
        compact: (trades?.length ?? 0) > 30,
      }),
    [trades],
  );

  // Worker C hook — extraMarkers 가 있으면 자동 계산된 마커와 merge.
  const mergedMarkers = useMemo<ChartMarker[]>(() => {
    if (extraMarkers === undefined || extraMarkers.length === 0) {
      return tradeMarkers;
    }
    return [...tradeMarkers, ...extraMarkers];
  }, [tradeMarkers, extraMarkers]);

  if (equityCurve.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  // 2-pane 분리 (top: 60% / bottom: 40%). 각 pane 은 독립 chart 인스턴스
  // → Y축 priceScale 자연스럽게 분리. 단위 모호 문제 해소.
  const topHeight = Math.round(height * TOP_PANE_RATIO);
  const bottomHeight = Math.round(height * BOTTOM_PANE_RATIO);
  const showBenchmark = benchmarkData.length > 0;
  const showDrawdown = drawdownData.length > 0;

  // 사용자가 BH 를 toggle off 했어도 BH curve 가 존재하면 checkbox 는 표시.
  const hasBuyAndHoldData = (buyAndHoldCurve?.length ?? 0) > 0;

  return (
    <div
      className="space-y-2"
      data-testid="equity-chart-v2"
      role="group"
      aria-label="백테스트 자본 곡선 + Buy and Hold 비교 + Drawdown 차트"
    >
      {/* Sprint 43 W10 — prototype 02 정합. 타임프레임 탭 + checkbox 컨트롤 바. */}
      <div
        className="flex flex-wrap items-center justify-between gap-3"
        data-testid="equity-chart-controls"
      >
        <div
          role="tablist"
          aria-label="차트 기간 선택"
          className="inline-flex items-center gap-1 rounded-md bg-[color:var(--bg-alt)] p-1"
        >
          {TIMEFRAME_OPTIONS.map((opt) => {
            const isActive = activeTimeframe === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveTimeframe(opt.value)}
                className={
                  "min-h-[32px] rounded px-3 py-1 font-mono text-xs font-medium transition-colors " +
                  (isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-[color:var(--text-secondary)] hover:bg-foreground/5 hover:text-[color:var(--text-primary)]")
                }
              >
                {opt.label}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          {hasBuyAndHoldData && (
            <label className="inline-flex items-center gap-2 text-xs text-[color:var(--text-secondary)] select-none">
              <input
                type="checkbox"
                checked={showBuyAndHold}
                onChange={(e) => setShowBuyAndHold(e.target.checked)}
                className="h-4 w-4 cursor-pointer accent-[color:var(--primary)]"
                aria-label="Buy and Hold 비교 표시"
              />
              Buy &amp; Hold 비교
            </label>
          )}
          <label className="inline-flex items-center gap-2 text-xs text-[color:var(--text-secondary)] select-none">
            <input
              type="checkbox"
              checked={showDrawdownOverlay}
              onChange={(e) => setShowDrawdownOverlay(e.target.checked)}
              className="h-4 w-4 cursor-pointer accent-[color:var(--primary)]"
              aria-label="드로다운 영역 표시"
            />
            드로다운 영역 표시
          </label>
        </div>
      </div>

      <div className="sr-only" role="status" aria-live="polite">
        {`기간 ${activeTimeframe === "ALL" ? "전체" : activeTimeframe} · ` +
          `Buy & Hold ${showBuyAndHold && hasBuyAndHoldData ? "표시" : "숨김"} · ` +
          `드로다운 ${showDrawdownOverlay ? "표시" : "숨김"}`}
      </div>

      <ChartLegend
        showBenchmark={showBenchmark}
        showDrawdown={showDrawdown}
        showCompare={comparing}
        compareLabel={compareLabel}
      />

      <div data-testid="equity-pane-wrapper">
        <EquityPane
          equityData={equityData}
          benchmarkData={benchmarkData}
          compareData={compareData}
          markers={mergedMarkers}
          height={topHeight}
          ariaLabel={
            comparing
              ? `자본 곡선 (Equity) 및 비교 백테스트 ${compareLabel ?? ""} — % 수익률 (시작=0%)`
              : undefined
          }
        />
        <AxisLabelBar
          // Sprint 37 BL-184: equity/BH curve 가 PnL 기준 (시작=0) 으로 정규화.
          // Compare 활성 시에는 % 수익률 기준으로 전환 (자본금 상이 대응).
          yAxisLabel={comparing ? "% 수익률 (시작=0%)" : "PnL (USDT, 시작=0)"}
          xAxisLabel={
            timeframe !== undefined && timeframe !== ""
              ? `시간 · ${timeframe} 단위 캔들`
              : "시간"
          }
          variant="equity"
        />
      </div>

      {showDrawdown && (
        <div data-testid="drawdown-pane-wrapper">
          <DrawdownPane drawdownData={drawdownData} height={bottomHeight} />
          <AxisLabelBar
            yAxisLabel={
              // BL-466 — 종전 문구 "leverage 시 -100% 초과 가능" 은 원인을 레버리지로
              // 돌렸지만, 자본 초과 손실은 **L=1 에서도** 일어난다(마진 게이트 no-op +
              // 청산 없음). 원인 귀속을 빼고 사실만 적는다.
              mddExceedsCapital === true
                ? "% (자본 대비 손실 · -100% 초과 = 자본을 넘어선 손실)"
                : "% (자본 대비 손실 · 0 ~ -100%)"
            }
            xAxisLabel={
              timeframe !== undefined && timeframe !== ""
                ? `시간 · ${timeframe} 단위 캔들`
                : "시간"
            }
            variant="drawdown"
          />
        </div>
      )}
    </div>
  );
}
