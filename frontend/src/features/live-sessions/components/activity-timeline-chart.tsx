"use client";

// Sprint 33-A (BL-150 partial): Activity Timeline 차트 — recharts → lightweight-charts.
//
// 컨테이너:
// - Top pane: entries (녹색 solid) + closes (파란 solid). 같은 스케일 (정수 카운트).
// - Bottom pane (optional): equity (cumulative_pnl, USDT). equity_curve 가 있을 때만.
//
// 패턴 정합:
// - Sprint 32-B EquityChartV2 의 2-pane 구조 (`EquityPane` + `DrawdownPane`) 재사용.
// - TradingChart wrapper (`@/components/charts/trading-chart`) 만 사용.
//   → LESSON-004 (useEffect dep) + Sprint 30 BL-157 (`currentColor` fallback) 안전.
//
// 참고: lightweight-charts 4.x 에서 동일 chart 안 dual-axis (left + right priceScale)
//   는 가능하나, EquityChartV2 와의 일관성 + 단위 모호 회피를 위해 2-pane 분리 채택.

import { useMemo } from "react";

import {
  TradingChart,
  type ChartPoint,
} from "@/components/charts/trading-chart";

import type {
  ActivityTimelinePoint,
  ActivityTimelineWithEquityPoint,
} from "../utils";

// 2-pane 비율 (EquityChartV2 와 동일).
const TOP_PANE_RATIO = 0.6;
const BOTTOM_PANE_RATIO = 0.4;

interface ActivityTimelineChartProps {
  /** buildActivityTimeline / buildActivityTimelineWithEquity 결과. ascending 정렬됨. */
  data:
    | readonly ActivityTimelinePoint[]
    | readonly ActivityTimelineWithEquityPoint[];
  /** equity (cumulative_pnl) 표시 여부. true 면 bottom pane 노출. */
  showEquity: boolean;
  /** 전체 차트 높이 (top + bottom 합계). default 192 (recharts 시절 h-48). */
  height?: number;
}

// ── helpers ─────────────────────────────────────────────────────────────

/**
 * ActivityTimelinePoint.label 은 `new Date(bar_time).toLocaleString()` 형식.
 * lightweight-charts 의 Time 으로 직접 사용 불가 → Date.parse 로 epoch ms 시도,
 * 실패 시 index 기반 fallback (장시간 세션에서 label 충돌 방어 + locale 차이).
 *
 * codex G.2 P2 #3 — `toLocaleString()` 은 timezone 의존 → 직접 ISO 문자열 보존이
 * 더 견고하나, utils.ts 변경은 Sprint 33 범위 외 (다른 테스트 파급). 본 컴포넌트
 * 내부에서만 fallback 처리.
 */
function pointToTime(label: string, fallbackIndex: number): string | number {
  const ms = Date.parse(label);
  if (Number.isFinite(ms)) {
    return Math.floor(ms / 1000);
  }
  // 파싱 실패 시 fallback — 시작 시각 0 + index*60 (1분 간격 가짜 시각).
  // 실제 데이터 의미보다 chart 가 throw 되지 않게 하는 게 우선.
  return fallbackIndex * 60;
}

// ── component ───────────────────────────────────────────────────────────

export function ActivityTimelineChart({
  data,
  showEquity,
  height = 192,
}: ActivityTimelineChartProps) {
  // entries series — 녹색 solid.
  const entriesData = useMemo<ChartPoint[]>(
    () =>
      data.map((p, i) => ({
        time: pointToTime(p.label, i),
        value: p.entries_in_window,
      })),
    [data],
  );

  // closes series — 파란 점선 (benchmark 슬롯에 매핑, EquityChartV2 와 동일 패턴).
  const closesData = useMemo<ChartPoint[]>(
    () =>
      data.map((p, i) => ({
        time: pointToTime(p.label, i),
        value: p.closes_in_window,
      })),
    [data],
  );

  // equity series — bottom pane 전용. showEquity=true 일 때만 사용.
  const equityData = useMemo<ChartPoint[]>(() => {
    if (!showEquity) return [];
    return data.map((p, i) => {
      const eq = (p as ActivityTimelineWithEquityPoint).cumulative_pnl;
      return {
        time: pointToTime(p.label, i),
        value: typeof eq === "number" ? eq : 0,
      };
    });
  }, [data, showEquity]);

  // 데이터 없음 — 호출 측에서 이미 빈 상태 처리하지만 방어 코드.
  if (data.length === 0) {
    return null;
  }

  // 2-pane 또는 단일 pane.
  const topHeight = showEquity
    ? Math.round(height * TOP_PANE_RATIO)
    : height;
  const bottomHeight = showEquity
    ? Math.round(height * BOTTOM_PANE_RATIO)
    : 0;

  return (
    <div
      className="space-y-1"
      data-testid="activity-timeline-chart"
      role="group"
      aria-label="Live session activity timeline — entries / closes 누적 + (optional) cumulative PnL"
    >
      <div data-testid="activity-timeline-counts-pane">
        <TradingChart
          data={[...entriesData]}
          benchmark={
            closesData.length > 0
              ? {
                  data: [...closesData],
                  options: {
                    color: "#3b82f6",
                    lineWidth: 2,
                    lineStyle: 0, // solid (entries 도 solid 라 구분 위해 색상만 차이)
                    priceLineVisible: false,
                    lastValueVisible: true,
                  },
                }
              : undefined
          }
          options={{
            color: "#22c55e",
            lineWidth: 2,
            priceFormat: {
              type: "price",
              precision: 0,
              minMove: 1,
            },
            priceLineVisible: false,
            lastValueVisible: true,
          }}
          height={topHeight}
          ariaLabel="Activity counts — entries (녹색 실선) / closes (파란 실선) 누적 카운트"
        />
        {/* 컴팩트 legend (recharts Legend 대체) */}
        <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <span
              aria-hidden="true"
              className="inline-block h-0.5 w-3"
              style={{ backgroundColor: "#22c55e" }}
            />
            Entries (window)
          </span>
          <span className="inline-flex items-center gap-1">
            <span
              aria-hidden="true"
              className="inline-block h-0.5 w-3"
              style={{ backgroundColor: "#3b82f6" }}
            />
            Closes (window)
          </span>
          {showEquity && (
            <span className="inline-flex items-center gap-1">
              <span
                aria-hidden="true"
                className="inline-block h-0.5 w-3"
                style={{ backgroundColor: "#f59e0b" }}
              />
              Equity (PnL, USDT)
            </span>
          )}
        </div>
      </div>

      {showEquity && (
        <div data-testid="activity-timeline-equity-pane">
          <TradingChart
            data={[...equityData]}
            options={{
              color: "#f59e0b",
              lineWidth: 2,
              priceFormat: {
                type: "price",
                precision: 2,
                minMove: 0.01,
              },
              priceLineVisible: false,
              lastValueVisible: true,
            }}
            height={bottomHeight}
            ariaLabel="Cumulative PnL (USDT) — equity curve from BE state.equity_curve"
          />
        </div>
      )}
    </div>
  );
}
