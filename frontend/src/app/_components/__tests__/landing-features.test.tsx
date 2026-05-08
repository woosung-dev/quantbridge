// LandingFeatures — 6개 카드 + section header 노출 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingFeatures } from "../landing-features";

describe("LandingFeatures", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + sub copy 노출", () => {
    render(<LandingFeatures />);
    expect(
      screen.getByRole("heading", { level: 2, name: /핵심 기능/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/트레이딩 전략의 전체 라이프사이클/),
    ).toBeInTheDocument();
  });

  it("6개 feature 카드 — h3 모두 렌더", () => {
    render(<LandingFeatures />);
    const titles = [
      "Pine Script 파싱",
      "벡터화 백테스트",
      "스트레스 테스트",
      "파라미터 최적화",
      "데모 트레이딩",
      "라이브 트레이딩",
    ] as const;
    for (const t of titles) {
      expect(
        screen.getByRole("heading", { level: 3, name: t }),
      ).toBeInTheDocument();
    }
  });
});
