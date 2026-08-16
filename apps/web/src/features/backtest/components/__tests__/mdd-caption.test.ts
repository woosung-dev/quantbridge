// buildMddCaption — leverage/자본초과 캡션 정책 (metrics-cards-mdd-leverage 에서 이관)
import { describe, expect, it } from "vitest";

import { buildMddCaption } from "@/features/backtest/components/charts/mdd-caption";

describe("buildMddCaption — leverage 가정 표시 정책 (Sprint 32-D)", () => {
  it("leverage=1 + 정상 MDD → null (caption 표시 없음)", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: false,
        mddExceedsCapital: false,
        liquidationOccurred: null,
      }),
    ).toBeNull();
  });

  it("레버리지 실행에서 강제청산 발생 → 강제청산과 갭 체결 증거금 초과를 표시한다", () => {
    expect(
      buildMddCaption({
        leverage: 2,
        mddBelowCapital: true,
        mddExceedsCapital: true,
        liquidationOccurred: true,
      }),
    ).toBe("leverage 2.0x · 강제청산 발생 · 갭 체결로 증거금 초과");
  });

  it("레버리지 실행에서 자본초과인데 청산이 없으면 모델 이상 신호를 표시한다", () => {
    expect(
      buildMddCaption({
        leverage: 2,
        mddBelowCapital: true,
        mddExceedsCapital: true,
        liquidationOccurred: false,
      }),
    ).toBe("leverage 2.0x · 레버리지 가정과 손실이 맞지 않습니다");
  });

  it("그 외 기존 문구는 유지한다", () => {
    expect(
      buildMddCaption({
        leverage: 2,
        mddBelowCapital: false,
        mddExceedsCapital: false,
        liquidationOccurred: false,
      }),
    ).toBe("leverage 2.0x 가정");
  });

  it("BE 메타 우선 — 구 실행은 기존 자본 초과 손실 문구를 유지한다", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: true,
        mddExceedsCapital: null,
        liquidationOccurred: null,
      }),
    ).toMatch(/자본 초과 손실/);
  });

  // [BL-466] 승인안 (c) — L=1 도 자본을 초과해 손실할 수 있다. 캡션이 그것을
  // 레버리지 탓으로 돌리지 않고, 막아줄 장치가 없었다는 사실까지 말해야 한다.
  it("leverage=1 자본초과 → 강제청산 부재까지 고지한다", () => {
    const caption = buildMddCaption({
      leverage: 1,
      mddBelowCapital: true,
      mddExceedsCapital: true,
      liquidationOccurred: null,
    });

    expect(caption).toBe(
      "leverage 1x · 현물 · 자본 초과 손실 · 강제청산이 없어 실제로는 불가능한 결과",
    );
  });

  it("레버리지 실행의 자본초과 문구는 1x 전용 문구를 쓰지 않는다", () => {
    const caption = buildMddCaption({
      leverage: 3,
      mddBelowCapital: true,
      mddExceedsCapital: true,
      liquidationOccurred: null,
    });

    expect(caption).toBe("leverage 3.0x · 자본 초과 손실");
    expect(caption).not.toMatch(/강제청산이 없어/);
  });
});
