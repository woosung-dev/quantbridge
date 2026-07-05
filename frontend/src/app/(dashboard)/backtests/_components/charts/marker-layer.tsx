"use client";

// Sprint 32-C (BL-171): MarkerLayer — trade → ChartMarker 변환 유틸 + hover tooltip.
// Sprint 34 (BL-177): dense text shorten — trades 가 많을 때 marker text 겹침 차단.
//
// 목적 (ui-ux-pro-max 진단 P0 #5 해소):
// - 사용자 코멘트: "L/S/X 약자가 도대체 뭐냐"
// - 거래 마커가 차트 위에 점으로만 떠 있고 의미가 안 보였음
// - 본 컴포넌트는 (1) marker shape/color/text 를 의미 있게 디자인 +
//   (2) hover tooltip 으로 가격·수량·시간·PnL 등 상세 정보 제공
//
// 설계 결정:
// 1. **shape**: lightweight-charts 4.x 가 native 로 지원하는 4종류 사용
//    - Long entry  → arrowUp   (filled green) — "위로 진입"
//    - Long exit   → circle    (green / red, PnL 부호로 색상)
//    - Short entry → arrowDown (filled red) — "아래로 진입"
//    - Short exit  → circle    (green / red, PnL 부호로 색상)
//    NOTE: lightweight-charts 4.x 는 "filled vs outline" 이중 shape 미지원.
//    사용자 권장 (filled entry / outline exit) 은 라이브러리 제약상 불가능 →
//    shape 종류 (arrow vs circle) 로 entry/exit 구분 + 색상으로 long/short
//    구분 + PnL 부호로 exit 색상 분기 (수익=녹색 / 손실=빨강).
//
// 2. **text**: 기존 "L"/"S"/"X" 약자 → 가격·PnL 노출
//    - Long entry  → "L $12345.67"
//    - Short entry → "S $12345.67"
//    - exit (수익) → "+1.23%"
//    - exit (손실) → "-1.23%"
//    text 길이가 길어지면 lightweight-charts 가 캔버스 공간 좁을 시 자동 truncate.
//
//    **compact mode (Sprint 34 BL-177)**: trades 가 30개 초과인 경우 dense
//    text 가 서로 겹쳐 읽을 수 없는 문제 (dogfood Day 6 BUG #3) 해소.
//    - entry text → "L" / "S" 만
//    - exit text  → "" (빈 문자열, 색상으로 win/loss 구분만 유지)
//    호출자가 `{ compact: true }` 명시 시 활성화. 기본값 false (backward compat).
//
// 3. **hover tooltip**: lightweight-charts native tooltip 미지원 →
//    `subscribeCrosshairMove` + 가장 가까운 marker 검색 + custom div overlay.
//    구현은 `MarkerTooltipOverlay` 별도 컴포넌트. 단, 본 PR 1차 scope 는
//    marker text 의미화만 우선. tooltip overlay 는 hook 만 노출 (deferred — 차후
//    별도 BL 로 분리. 현재는 marker.text 가 시각적으로 충분).
//
// Sprint 35+ 분리:
// - BL-177-A: visible-range zoom-aware count limit (chart instance subscription)
// - BL-177-B: hover tooltip overlay (subscribeCrosshairMove)
// - BL-177-C: cluster (인접 marker 통합)

import type { ChartMarker } from "@/components/charts/trading-chart";
import type { TradeItem } from "@/features/backtest/schemas";

// 차트 마커 cap — TRADE_LIMIT 정합. equity-chart-v2 의 200 과 동일 값.
export const MARKER_LIMIT = 200;

// 색상 token — entry 강조 / exit 흐림 (Tailwind green-500/red-500/green-400/red-400 정합).
const COLORS = {
  longEntry: "#22c55e", // green-500
  longExitWin: "#22c55e", // green-500
  longExitLoss: "#ef4444", // red-500
  shortEntry: "#ef4444", // red-500
  shortExitWin: "#22c55e", // green-500
  shortExitLoss: "#ef4444", // red-500
} as const;

// 가격 포맷 — 짧은 marker text 를 위해 소수점 자리 적응형.
function formatPriceShort(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  // BTC 처럼 큰 가격은 정수 부분만 (e.g. 67890), alt 코인 처럼 작으면 소수 4자리.
  if (abs >= 1000) return `$${Math.round(value).toLocaleString("en-US")}`;
  if (abs >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function formatReturnPctShort(returnPct: number): string {
  // BE return_pct 는 비율 (0.0123 = 1.23%) 가정. metrics-cards 와 동일 컨벤션.
  if (!Number.isFinite(returnPct)) return "—";
  const pct = returnPct * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

/**
 * `deriveTradeMarkers` 옵션.
 *
 * Sprint 34 BL-177: dense text shorten — trades 가 많을 때 marker text 겹침 차단.
 */
export interface DeriveTradeMarkersOptions {
  /**
   * compact mode — trades 가 많을 때 marker text 를 짧게 유지.
   * - true:  entry text = "L" / "S" 만, exit text = "" (빈 문자열)
   * - false: entry text = "L $price" / "S $price", exit text = "+1.23%" / "-1.23%"
   *
   * 기본값 = false (Sprint 32-C 기존 동작 보존, backward compat).
   */
  compact?: boolean;
}

/**
 * 거래 목록을 차트 마커 배열로 변환.
 *
 * - entry: arrow (long=arrowUp green / short=arrowDown red), text="L $price" / "S $price"
 * - exit: circle, color = PnL 부호 (win=green / loss=red), text="+1.23%" / "-1.23%"
 * - 미체결 거래 (status==="open"): exit marker 미생성
 * - MARKER_LIMIT 초과 시 앞에서부터 cap (trade_index ascending 가정)
 *
 * Sprint 34 BL-177: `options.compact === true` 시 text 를 단축
 * (entry "L"/"S" / exit ""). dense trades (>30) 환경에서 marker text 겹침 차단.
 *
 * 빈 배열 / null / undefined 안전.
 */
export function deriveTradeMarkers(
  trades: readonly TradeItem[] | undefined,
  options?: DeriveTradeMarkersOptions,
): ChartMarker[] {
  if (trades === undefined || trades.length === 0) return [];

  const compact = options?.compact === true;
  const capped = trades.slice(0, MARKER_LIMIT);
  const out: ChartMarker[] = [];

  for (const trade of capped) {
    // --- entry marker -------------------------------------------------------
    const entryColor =
      trade.direction === "long" ? COLORS.longEntry : COLORS.shortEntry;
    const directionLabel = trade.direction === "long" ? "L" : "S";
    const entryText = compact
      ? directionLabel
      : `${directionLabel} ${formatPriceShort(trade.entry_price)}`;
    out.push({
      time: trade.entry_time,
      position: trade.direction === "long" ? "belowBar" : "aboveBar",
      color: entryColor,
      shape: trade.direction === "long" ? "arrowUp" : "arrowDown",
      text: entryText,
    });

    // --- exit marker (closed only) -----------------------------------------
    if (trade.status === "closed" && trade.exit_time !== null) {
      const isWin = Number.isFinite(trade.pnl) && trade.pnl > 0;
      const exitColor =
        trade.direction === "long"
          ? isWin
            ? COLORS.longExitWin
            : COLORS.longExitLoss
          : isWin
            ? COLORS.shortExitWin
            : COLORS.shortExitLoss;
      out.push({
        time: trade.exit_time,
        position: "inBar",
        color: exitColor,
        shape: "circle",
        // compact mode: 빈 문자열 → 색상으로 win/loss 만 구분.
        text: compact ? "" : formatReturnPctShort(trade.return_pct),
      });
    }
  }
  return out;
}

// --- export helper for tests --------------------------------------------------
//
// formatPriceShort / formatReturnPctShort 도 test 에서 직접 검증하기 위해 export.
// production 코드 (equity-chart-v2) 에서는 deriveTradeMarkers 만 사용.
export const __test_only__ = {
  formatPriceShort,
  formatReturnPctShort,
  COLORS,
};
