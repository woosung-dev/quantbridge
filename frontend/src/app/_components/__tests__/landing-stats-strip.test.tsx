// LandingStatsStrip — 4 KPI 노출 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingStatsStrip } from "../landing-stats-strip";

describe("LandingStatsStrip", () => {
  afterEach(() => {
    cleanup();
  });

  it("4 KPI 모두 (Beta 정직 표시 + 라벨, Sprint 60 S2 BL-270)", () => {
    render(<LandingStatsStrip />);
    const pairs = [
      ["Beta", "현재 단계"],
      ["Open", "feedback 환영"],
      ["Dogfood", "초기 사용자"],
      ["v2.0", "최신 버전"],
    ] as const;
    for (const [value, label] of pairs) {
      expect(screen.getByText(value)).toBeInTheDocument();
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
