// LandingHowItWorks — 4 step 모두 렌더 + section id 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingHowItWorks } from "../landing-how-it-works";

describe("LandingHowItWorks", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + sub copy 노출", () => {
    render(<LandingHowItWorks />);
    expect(
      screen.getByRole("heading", { level: 2, name: /어떻게 작동하나요/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/4단계로 끝납니다/),
    ).toBeInTheDocument();
  });

  it("4 step 카드 — h3 + step number 모두 렌더", () => {
    const { container } = render(<LandingHowItWorks />);
    const titles = [
      "전략 업로드",
      "백테스트 실행",
      "파라미터 최적화",
      "자동 매매 시작",
    ] as const;
    for (const t of titles) {
      expect(
        screen.getByRole("heading", { level: 3, name: t }),
      ).toBeInTheDocument();
    }
    for (const n of ["01", "02", "03", "04"]) {
      expect(screen.getByText(n)).toBeInTheDocument();
    }
    expect(container.querySelector("#how-it-works")).not.toBeNull();
  });
});
