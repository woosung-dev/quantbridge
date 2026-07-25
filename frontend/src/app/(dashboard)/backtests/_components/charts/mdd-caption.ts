// MDD leverage/자본초과 캡션 정책 (Sprint 32-D) — metrics-cards 에서 이관 (TV parity F5)
// 사용자 신뢰 quality bar: 자본 초과 손실은 leverage 가정과 함께 의무 표시.

export interface MddCaptionInput {
  readonly leverage: number;
  /** 클라이언트 계산: max_drawdown < -1 (= -100%). */
  readonly mddBelowCapital: boolean;
  /** BE 메타: 우선 신뢰 (Sprint 32-D 이후 응답). null 이면 클라이언트 fallback. */
  readonly mddExceedsCapital: boolean | null;
  /** 레버리지 마진 모델의 강제청산 발생 여부. 구 실행은 null. */
  readonly liquidationOccurred: boolean | null;
}

export function buildMddCaption({
  leverage,
  mddBelowCapital,
  mddExceedsCapital,
  liquidationOccurred,
}: MddCaptionInput): string | null {
  const exceedsCapital = mddExceedsCapital ?? mddBelowCapital;
  const leverageLabel =
    leverage === 1 ? "leverage 1x · 현물" : `leverage ${leverage.toFixed(1)}x`;

  if (leverage > 1 && liquidationOccurred) {
    return `${leverageLabel} · 강제청산 발생${exceedsCapital ? " · 갭 체결로 증거금 초과" : ""}`;
  }
  if (leverage > 1 && exceedsCapital && liquidationOccurred === false) {
    return `${leverageLabel} · 레버리지 가정과 손실이 맞지 않습니다`;
  }
  if (exceedsCapital) {
    // 자본 초과 손실 — 사용자 신뢰 quality bar 의무 표시.
    return `${leverageLabel} · 자본 초과 손실`;
  }
  if (leverage !== 1) {
    return `${leverageLabel} 가정`;
  }
  return null;
}
