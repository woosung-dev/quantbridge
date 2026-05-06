// 시계열 곡선의 첫 값을 0으로 정규화 (PnL 기준). 빈 배열은 그대로.
//
// Sprint 37 BL-184: TradingView 표준에 맞춰 equity / buy_and_hold_curve 의
// 시작점을 0 (PnL 기준) 으로 정렬해 두 시리즈가 동일 baseline 에서 비교되도록
// 한다. BE BH curve 는 absolute capital 형식 그대로 (metrics/MC/stress 입력),
// FE 표시 단계에서만 정규화 (codex GO_WITH_FIXES — FE-only).
//
// 순수 함수 / idempotent: 첫 값을 0 으로 빼면, 다시 호출해도 첫 값이 이미 0
// 이라 변화 없음. value 외 필드는 spread 로 보존.

export function normalizeToPnlCurve<T extends { value: number }>(
  curve: readonly T[],
): readonly T[] {
  if (curve.length === 0) return [];
  const baseline = curve[0]!.value;
  return curve.map((point) => ({ ...point, value: point.value - baseline }));
}
