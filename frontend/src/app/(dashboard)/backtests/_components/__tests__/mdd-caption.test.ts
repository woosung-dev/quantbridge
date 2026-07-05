// buildMddCaption — leverage/자본초과 캡션 정책 (metrics-cards-mdd-leverage 에서 이관)
import { describe, expect, it } from "vitest";

import { buildMddCaption } from "../mdd-caption";

describe("buildMddCaption — leverage 가정 표시 정책 (Sprint 32-D)", () => {
  it("leverage=1 + 정상 MDD → null (caption 표시 없음)", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: false,
        mddExceedsCapital: false,
      }),
    ).toBeNull();
  });

  it("leverage=2 + 정상 MDD → 'leverage 2.0x 가정'", () => {
    expect(
      buildMddCaption({
        leverage: 2,
        mddBelowCapital: false,
        mddExceedsCapital: false,
      }),
    ).toMatch(/leverage 2\.0x.*가정/);
  });

  it("자본 초과 손실 + leverage=1 → '자본 초과 손실' 강조", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: true,
        mddExceedsCapital: true,
      }),
    ).toMatch(/자본 초과 손실/);
  });

  it("BE 메타 우선 — mddExceedsCapital=null 이면 mddBelowCapital fallback", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: true,
        mddExceedsCapital: null,
      }),
    ).toMatch(/자본 초과 손실/);
  });

  it("BE 메타 mddExceedsCapital=false 우선 — 클라이언트 mddBelowCapital 무시", () => {
    expect(
      buildMddCaption({
        leverage: 1,
        mddBelowCapital: false,
        mddExceedsCapital: false,
      }),
    ).toBeNull();
  });
});
