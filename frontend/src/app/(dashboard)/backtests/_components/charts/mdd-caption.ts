// MDD leverage/자본초과 캡션 정책 (Sprint 32-D) — metrics-cards 에서 이관 (TV parity F5)
// 사용자 신뢰 quality bar: 자본 초과 손실은 leverage 가정과 함께 의무 표시.

export interface MddCaptionInput {
  readonly leverage: number;
  /** 클라이언트 계산: max_drawdown < -1 (= -100%). */
  readonly mddBelowCapital: boolean;
  /** BE 메타: 우선 신뢰 (Sprint 32-D 이후 응답). null 이면 클라이언트 fallback. */
  readonly mddExceedsCapital: boolean | null;
}

export function buildMddCaption({
  leverage,
  mddBelowCapital,
  mddExceedsCapital,
}: MddCaptionInput): string | null {
  const exceedsCapital = mddExceedsCapital ?? mddBelowCapital;
  const leverageLabel =
    leverage === 1 ? "leverage 1x · 현물" : `leverage ${leverage.toFixed(1)}x`;

  if (exceedsCapital) {
    // 자본 초과 손실 — 사용자 신뢰 quality bar 의무 표시.
    return `${leverageLabel} · 자본 초과 손실`;
  }
  if (leverage !== 1) {
    return `${leverageLabel} 가정`;
  }
  return null;
}
