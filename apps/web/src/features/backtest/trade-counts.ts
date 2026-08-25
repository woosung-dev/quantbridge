// BL-822 — 「거래 수」와 「완료 거래」를 한 곳에서만 파생시킨다.
//
// BE detail 응답은 두 셈을 함께 싣는다.
//   · num_trades       = 미청산 포함 전체 (Sprint 31-E/BL-155 override — 거래 목록 길이와 같다)
//   · completed_trades = 청산 완료분     (승률·평균손익 등 모든 성과 지표의 분모)
// 이 둘이 한 이름을 쓰던 동안 화면은 「총 거래 수 13 · 승률 16.67%」처럼 곱해서 정수가
// 안 나오는 조합을 인쇄했다(2026-08-25 qa-sweep, backtest 20128227).

import type { BacktestMetricsOut } from "./schemas";

export interface TradeCounts {
  /** 원장에 기록된 전체 거래 수 — 미청산 포함. 거래 행이 그만큼 나열되는 곳에서만 쓴다. */
  total: number;
  /** 청산이 끝난 거래 수 — 승률을 비롯한 모든 성과 지표의 분모. */
  completed: number;
  /** 아직 청산되지 않은 거래 수. */
  open: number;
}

/**
 * ★`open` 은 `total_open_trades`(engine 값)가 아니라 **표시되는 두 수의 차이**다.
 *   화면에 인쇄되는 셋이 언제나 total = completed + open 으로 닫히게 하려는 것이다.
 * ★`completed_trades` 가 없는 응답(구 BE·구 캐시)에서는 total 로 접어 무너지지 않게 한다.
 */
export function deriveTradeCounts(
  m: Pick<BacktestMetricsOut, "num_trades" | "completed_trades">,
): TradeCounts {
  const total = m.num_trades;
  const completed = m.completed_trades ?? m.num_trades;
  return { total, completed, open: Math.max(0, total - completed) };
}
