// LandingPerformance (C 이식) — 성능 3값 + 각 조건 문구 + 측정 조건 고지.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingPerformance } from "../landing-performance";

describe("LandingPerformance", () => {
  afterEach(() => {
    cleanup();
  });

  it("성능 3셀(.perf-cell) + 3값", () => {
    const { container } = render(<LandingPerformance />);
    expect(container.querySelectorAll(".perf-cell").length).toBe(3);
    expect(screen.getByText("20,064")).toBeInTheDocument();
    expect(screen.getByText("3.24초")).toBeInTheDocument();
    expect(screen.getByText("6,193")).toBeInTheDocument();
  });

  it("조건 없는 속도 형용사 금지 — 측정 조건 고지 노출", () => {
    render(<LandingPerformance />);
    expect(screen.getByText(/로컬 개발 환경에서 한 번 측정한 결과입니다/)).toBeInTheDocument();
  });
});
