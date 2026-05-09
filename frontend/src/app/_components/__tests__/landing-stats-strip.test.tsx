// LandingStatsStrip — 4 KPI 노출 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingStatsStrip } from "../landing-stats-strip";

describe("LandingStatsStrip", () => {
  afterEach(() => {
    cleanup();
  });

  it("4 KPI 모두 (값 + 라벨)", () => {
    render(<LandingStatsStrip />);
    const pairs = [
      ["10,000+", "활성 전략"],
      ["99.97%", "시스템 가동률"],
      ["$2.4B+", "총 거래량"],
      ["4.8", "사용자 평점"],
    ] as const;
    for (const [value, label] of pairs) {
      expect(screen.getByText(value)).toBeInTheDocument();
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
